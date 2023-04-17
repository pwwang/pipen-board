"""Provides the running data and functions to mutate it"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import importlib
import importlib.util
from copy import deepcopy
from multiprocessing import Process, Pipe
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING, Any, Mapping, Type
from urllib.parse import urlparse

import cmdy
from simpleconf import Config
from liquid import Liquid
from pipen import Pipen, Proc, ProcGroup
from pipen.utils import get_marked
from pipen_annotate import annotate

from .defaults import (
    PIPEN_BOARD_DIR,
    SECTION_PIPELINE_OPTIONS,
    SECTION_PROCESSES,
    SECTION_PROCGROUPS,
    SECTION_DIAGRAM,
    SECTION_REPORTS,
    SECTION_LOG,
    PIPELINE_OPTIONS,
    logger,
)

if TYPE_CHECKING:
    from argparse import Namespace

DEFAULT_RUN_DATA = {
    # "log": None
    SECTION_LOG: None,
    # "diagram": "<svg>...</svg>"
    SECTION_DIAGRAM: None,
    # "reports": <reportdir>
    SECTION_REPORTS: None,
    # "PROCESSES": { proc: { status, jobs: [status] } }
    SECTION_PROCESSES: {},
    # "PROCGROUPS": {
    #     procgroup: { proc: { status, jobs: [status] } }
    # }
    SECTION_PROCGROUPS: {},
}

# proc status: init, running, succeeded, failed
# job status: init, queued, submitted, running, killed, succeeded, failed


def parse_pipeline(pipeline: str) -> Pipen:
    """Parse the pipeline"""
    modpath, sep, name = pipeline.rpartition(":")
    if sep != ":":
        raise ValueError(
            f"Invalid pipeline: {pipeline}.\n"
            "It must be in the format '<module[.submodule]>:pipeline' or \n"
            "'/path/to/pipeline.py:pipeline'"
        )

    path = Path(modpath)
    if path.is_file():
        spec = importlib.util.spec_from_file_location(path.stem, modpath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(modpath)

    try:
        pipeline = getattr(module, name)
    except AttributeError:
        raise ValueError(f"Invalid pipeline: {pipeline}") from None

    if isinstance(pipeline, type) and issubclass(pipeline, Proc):
        pipeline = Pipen(name=f"{pipeline.name}Pipeline").set_starts(pipeline)

    if isinstance(pipeline, type) and issubclass(pipeline, Pipen):
        pipeline = pipeline()

    if isinstance(pipeline, type) and issubclass(pipeline, ProcGroup):
        pipeline = pipeline().as_pipen()

    if not isinstance(pipeline, Pipen):
        raise ValueError(
            f"Invalid pipeline: {pipeline}\n"
            "It must be a `pipen.Pipen` instance"
        )

    return pipeline


def _anno_to_argspec(anno: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Convert the annotation to the argument spec"""
    if anno is None:
        return {}

    argspec = {}
    # arginfo: attrs, help, terms
    for arg, arginfo in anno.items():
        argspec[arg] = arginfo.attrs.copy()
        # type - bool/text/choice/mchoice(s)/json/auto/list(array)/ns(namespace)
        # required
        # choices
        # itype
        if "ctype" not in argspec[arg]:
            if (argspec[arg].get("action") in ("store_true", "store_false")):
                argspec[arg]["type"] = "bool"
            elif (
                argspec[arg].get("action") in ("ns", "namespace")
                or argspec[arg].get("ns")
                or argspec[arg].get("namespace")
            ):
                argspec[arg]["type"] = "ns"
            elif (
                argspec[arg].get("action") in (
                    "append", "extend", "clear_append", "clear_extend"
                )
                or argspec[arg].get("array")
                or argspec[arg].get("list")
            ):
                argspec[arg]["type"] = "list"
            elif argspec[arg].get("choices") or argspec[arg].get("choice"):
                argspec[arg]["type"] = "choice"
            elif argspec[arg].get("mchoice") or argspec[arg].get("mchoices"):
                argspec[arg]["type"] = "mchoice"
        else:
            argspec[arg]["type"] = argspec[arg].pop("ctype")

        t = argspec[arg].get("type")
        if t == "ns":
            argspec[arg]["value"] = _anno_to_argspec(arginfo.terms)
        elif t in ("choice", "mchoice"):
            argspec[arg]["value"] = argspec[arg].pop("default", [])
            argspec[arg]["choices"] = list(arginfo.terms)
            argspec[arg]["choices_desc"] = [
                term.help for term in arginfo.terms.values()
            ]
        else:
            argspec[arg]["value"] = argspec[arg].pop("default", None)

        # determine the itype for list elements
        if t == 'list':
            if (
                argspec[arg]["value"] is not None
                and not isinstance(argspec[arg]["value"], list)
            ):
                argspec[arg]["value"] = [argspec[arg]["value"]]
            if (
                argspec[arg]["value"] is not None
                and argspec[arg]["value"]
                and "itype" not in argspec[arg]
                and not isinstance(argspec[arg]["value"][0], str)
            ):
                argspec[arg]["itype"] = type(argspec[arg]["value"][0]).__name__

        argspec[arg]["desc"] = arginfo.help

    return argspec


def _proc_to_argspec(
    proc: Proc | Type[Proc],
    is_start: bool,
    hidden: bool = False,
) -> Mapping[str, Any]:
    """Convert the proc to the argument spec"""
    if isinstance(proc, Proc):
        anno = annotate(proc.__class__)
    else:
        anno = annotate(proc)

    summary = anno.get("Summary", {"short": "", "long": ""})
    argspec = {
        "is_start": is_start,
        "desc": f'# {summary["short"]}\n\n{summary["long"]}',
        "value": {},
    }
    if hidden:
        argspec["hidden"] = True
        return argspec

    if is_start and not get_marked(proc, "board_config_no_input"):
        argspec["value"]["in"] = {
            "desc": "The input data for the process",
            "type": "ns",
            "required": True,
            "value": _anno_to_argspec(anno.get("Input", {})),
        }
    argspec["value"]["envs"] = {
        "desc": "Environment variables for the process, used across jobs",
        "value": _anno_to_argspec(anno.get("Envs", {})),
    }
    argspec["value"]["plugin_opts"] = PIPELINE_OPTIONS["plugin_opts"]
    argspec["value"]["scheduler_opts"] = PIPELINE_OPTIONS["scheduler_opts"]
    argspec["value"]["forks"] = PIPELINE_OPTIONS["forks"]
    argspec["value"]["cache"] = PIPELINE_OPTIONS["cache"]
    argspec["value"]["scheduler"] = PIPELINE_OPTIONS["scheduler"]
    argspec["value"]["dirsig"] = PIPELINE_OPTIONS["dirsig"]
    argspec["value"]["error_strategy"] = PIPELINE_OPTIONS["error_strategy"]
    argspec["value"]["num_retries"] = PIPELINE_OPTIONS["num_retries"]
    argspec["value"]["lang"] = {
        "desc": "The interpreter to run the script",
        "hidden": True,
        "placeholder": proc.lang,
        # Don't include it in the config file if not specified
        "value": None,
    }

    return argspec


def _load_additional(additional: str, **kwargs) -> Mapping[str, Any]:
    """Load additional config files"""
    if not additional:
        return {}

    parsed = urlparse(additional)
    cache_dir = Path(gettempdir()) / 'pipen-cli-config-additional-configs'
    cache_dir.mkdir(parents=True, exist_ok=True)
    if parsed.scheme in ('http', 'https', 'ftp', 'ftps', 'gh'):
        from hashlib import sha256
        from urllib.error import URLError
        from urllib.request import urlretrieve

        if parsed.scheme == 'gh':
            try:
                user, repo, file_path = parsed.path.split('/', 2)
            except ValueError:
                raise ValueError(f"Invalid gh:// URL: {additional}")
            branch = 'master'
            if '@' in file_path:
                file_path, branch = file_path.split('@')
            parsed = urlparse(
                "https://raw.githubusercontent.com/"
                f"{user}/{repo}/{branch}/{file_path}"
            )

        url = parsed.geturl()
        cache_key = sha256(url.encode('utf-8')).hexdigest()
        additional = cache_dir / f"{cache_key}-{parsed.path.split('/')[-1]}"
        if not additional.exists():
            try:
                urlretrieve(url, additional)
            except URLError:
                raise ValueError(
                    f"Could not retrieve remote path: {additional}"
                ) from None

    if not kwargs:
        return Config.load(additional)

    # kwargs passed, treat the file as a template
    additional = Path(additional)
    tpl = Liquid(additional, mode="wild", from_file=True)
    configfile = cache_dir / f"{additional.stem}.rendered{additional.suffix}"
    configfile.write_text(tpl.render(**kwargs))
    return Config.load(configfile)


async def _get_config_data(args: Namespace) -> Mapping[str, Any]:
    """Get the pipeline data"""
    old_argv = sys.argv
    sys.argv = ["from-pipen-cli-config"] + args.pipeline_args
    logger.debug("DBG Fetching pipeline data ...")
    try:
        pipeline = parse_pipeline(args.pipeline)
        # Initialize the pipeline so that the arguments definied by
        # other plugins (i.e. pipen-args) to take in place.
        await pipeline._init()
        pipeline.build_proc_relationships()
    finally:
        sys.argv = old_argv

    if args.additional:
        logger.debug("DBG Loading additional configuration items ...")
        data = _load_additional(
            args.additional,
            pipeline=args.pipeline,
            pipeline_args=args.pipeline_args,
        )
    else:
        data = {}

    data[SECTION_PIPELINE_OPTIONS] = PIPELINE_OPTIONS
    data[SECTION_PIPELINE_OPTIONS]["name"] = {
        "type": "str",
        "value": args.name or pipeline.name,
        "placeholder": args.name or pipeline.name,
        "readonly": True,
        "desc": (
            "The name of the pipeline. "
            "It will affect the names of working directory and "
            "the result directory"
        ),
    }
    data[SECTION_PIPELINE_OPTIONS]["desc"] = {
        "type": "str",
        "value": pipeline.desc,
        "desc": (
            "The description of the pipeline, "
            "shows in the log and report."
        ),
    }
    data[SECTION_PIPELINE_OPTIONS]["outdir"] = {
        "desc": "The output directory of your pipeline",
        "placeholder": "./<name>_results",
        "type": "str",
        "value": None,
    }
    data[SECTION_PROCESSES] = {}
    pg_sec = {}
    for proc in pipeline.procs:
        logger.debug("DBG Parsing process %s ...", proc.name)

        pg = proc.__meta__["procgroup"]
        if pg:
            if pg.name not in pg_sec:
                pg_sec[pg.name] = {"PROCESSES": {}}
                pg_args = _anno_to_argspec(
                    annotate(pg.__class__).get("Args")
                )
                if pg_args:
                    for arg, arginfo in pg_args.items():
                        arginfo["value"] = pg.DEFAULTS.get(arg)
                    pg_sec[pg.name]["ARGUMENTS"] = pg_args

            pg_sec[pg.name][SECTION_PROCESSES][proc.name] = _proc_to_argspec(
                proc,
                proc in pipeline.starts,
                get_marked(proc, "board_config_hidden", False),
            )
        else:
            data[SECTION_PROCESSES][proc.name] = _proc_to_argspec(
                proc,
                proc in pipeline.starts,
                get_marked(proc, "board_config_hidden", False),
            )

    data[SECTION_PROCGROUPS] = pg_sec
    return data


class DataManager:
    """Gather and manager the pipeline data"""

    # Send data every 3 seconds to the client, via websocket
    INTERVAL = 3

    def __init__(self) -> None:
        self.running = False
        self._config_data = None
        self._run_data = None
        self._timer = None

    def _get_config_data(
        self,
        args: Namespace,
        configfile: str | None = None,
        use_cached: bool | str = "auto",
    ):
        """Get the config data of the pipeline

        Args:
            args: The arguments from the CLI
            configfile: The name to the config file
            use_cached: Whether to use the cached data
                - auto: use the cached data if args.dev is True, otherwise don't
                - True: use the cached data regardless of args.dev
                - False: don't use the cached data anyway regardless of args.dev
        """
        if configfile:
            with PIPEN_BOARD_DIR.joinpath(configfile).open() as f:
                self._config_data = json.load(f)
                return

        if (
            (use_cached is True or (use_cached == "auto" and args.dev))
            and self._config_data
        ):
            return

        # Use multiprocessing to get a clean environment
        # to load the pipeline to avoid conflicts
        def target(conn):
            conn.send(
                json.dumps(asyncio.run(_get_config_data(args))).encode()
            )
            conn.close()

        parent_conn, child_conn = Pipe()
        p = Process(target=target, args=(child_conn,))
        p.start()
        data = parent_conn.recv()
        p.join()

        self._config_data = json.loads(data)

    def _get_prev_run(self, args: Namespace, configfile: str | None = None):
        """Get data for the previous run

        Args:
            args: The parsed arguments from cli
            configfile: The config file to use, if not specified, use a
                fresh one loaded from the pipeline object
        """
        out = self._run_data = {SECTION_LOG: None}
        pipeline_dir = Path(args.root).joinpath(".pipen", args.name)
        self._get_config_data(args, configfile=configfile)
        if not pipeline_dir.is_dir():
            # no previous run, return defaults
            self._run_data = DEFAULT_RUN_DATA
            return

        # Get the log
        logfile = pipeline_dir.joinpath("run-latest.log")
        if logfile.is_file():
            out[SECTION_LOG] = logfile.read_text()

        config_data = self._config_data
        outdir = config_data[SECTION_PIPELINE_OPTIONS].get(
            "outdir",
            {"value": None},
        )["value"]
        outdir = outdir or Path(args.root).joinpath(f"{args.name}_results")
        reports_dir = outdir.joinpath("REPORTS")
        if reports_dir.joinpath("index.html").is_file():
            out[SECTION_REPORTS] = str(reports_dir)

        diagram = outdir.joinpath("diagram.svg")
        if diagram.is_file():
            out[SECTION_DIAGRAM] = diagram.read_text()

        out[SECTION_PROCESSES] = {}
        out[SECTION_PROCGROUPS] = {}

        def process_proc(proc: str, container: dict):
            procdir = pipeline_dir.joinpath(proc)
            container[proc] = {"jobs": []}
            if not procdir.is_dir():
                container[proc]["status"] = "init"
                return

            for jobdir in sorted(
                [j for j in procdir.glob("*") if j.name.isdigit()],
                key=lambda x: int(x.name),
            ):
                rcfile = jobdir / "job.rc"
                try:
                    rc = int(rcfile.read_text().strip())
                except Exception:
                    container[proc]["jobs"].append("failed")
                else:
                    container[proc]["jobs"].append(
                        "succeeded" if rc == 0 else "failed"
                    )
            if not container[proc]["jobs"]:
                container[proc]["status"] = "init"
            elif "failed" in container[proc]["jobs"]:
                container[proc]["status"] = "failed"
            else:
                container[proc]["status"] = "succeeded"

        for proc in config_data[SECTION_PROCESSES]:
            process_proc(proc, out[SECTION_PROCESSES])

        for pg in config_data[SECTION_PROCGROUPS]:
            out[SECTION_PROCGROUPS][pg] = {}
            for proc in config_data[SECTION_PROCGROUPS][pg][SECTION_PROCESSES]:
                process_proc(proc, out[SECTION_PROCGROUPS][pg])

    def clear_run_data(self, keep_log: bool = False):
        """Clear the data"""
        if not keep_log:
            self._run_data = deepcopy(DEFAULT_RUN_DATA)
        else:
            log = self._run_data[SECTION_LOG]
            self._run_data = deepcopy(DEFAULT_RUN_DATA)
            self._run_data[SECTION_LOG] = log

    def get_data(self, args: Namespace, configfile: str | None = None):
        """Get the data"""
        if not self.running:
            self._get_prev_run(args, configfile=configfile)
            return {
                "isRunning": False,
                "config": self._config_data,
                "run": self._run_data,
            }

        self._get_config_data(args, configfile=configfile)
        return {
            "isRunning": True,
            "config": self._config_data,
            "run": self._run_data,
        }

    async def send_run_data(self, ws, force: bool = False):
        if ws is None:
            return
        if not force and time.time() - self._timer < self.INTERVAL:
            return

        # Send data
        logger.debug("DBG Sending run data to the frontend")
        try:
            await ws.send(json.dumps(self._run_data))
        except BrokenPipeError:
            pass

        # Reset timer
        self._timer = time.time()

    async def on_start(self, data, ws):
        # { SECTION_PROCESSES: [p1, p2], SECTION_PROCGROUPS: {pg1: [p3, p4]} }
        if isinstance(data, str):
            data = json.loads(data)

        if SECTION_DIAGRAM in data:
            self._run_data[SECTION_DIAGRAM] = data[SECTION_DIAGRAM]

        if SECTION_PROCESSES in data:
            for proc in data[SECTION_PROCESSES]:
                self._run_data[SECTION_PROCESSES][proc] = {
                    "status": "init", "jobs": []
                }

        if SECTION_PROCGROUPS in data:
            for pg in data[SECTION_PROCGROUPS]:
                self._run_data[SECTION_PROCGROUPS][pg] = {}
                for proc in data[SECTION_PROCGROUPS][pg]:
                    self._run_data[SECTION_PROCGROUPS][pg][proc] = {
                        "status": "init", "jobs": []
                    }

        self.timer = time.time()
        await self.send_run_data(ws, force=True)

    async def on_complete(self, data, ws):
        if isinstance(data, str):
            data = json.loads(data)

        if SECTION_REPORTS in data:
            self._run_data[SECTION_REPORTS] = data[SECTION_REPORTS]

        self.running = False
        await self.send_run_data(ws, force=True)

    async def on_proc_start(self, data, ws):
        if isinstance(data, str):
            data = json.loads(data)

        proc, group, njobs = data["proc"], data["procgroup"], data["njobs"]

        if not group:
            self._run_data[SECTION_PROCESSES][proc]["status"] = "running"
            self._run_data[SECTION_PROCESSES][proc]["jobs"] = ["init"] * njobs
        else:
            self._run_data[SECTION_PROCGROUPS][group][proc]["status"] = "running"
            self._run_data[SECTION_PROCGROUPS][group][proc]["jobs"] = [
                "init"
            ] * njobs

        await self.send_run_data(ws, force=True)

    async def on_proc_done(self, data, ws):
        if isinstance(data, str):
            data = json.loads(data)

        proc, group, succeeded = (
            data["proc"],
            data["procgroup"],
            data["succeeded"],
        )
        procdata = (
            self._run_data[SECTION_PROCESSES][proc]
            if not group
            else self._run_data[SECTION_PROCGROUPS][group][proc]
        )
        # succeeded could be True, False, or "cached"
        procdata["status"] = "succeeded" if succeeded else "failed"

        await self.send_run_data(ws, force=True)

    async def _on_job(self, data, status, ws):
        if isinstance(data, str):
            data = json.loads(data)

        proc, group, job = data["proc"], data["procgroup"], data["job"]

        if not group:
            self._run_data[SECTION_PROCESSES][proc]["jobs"][job] = status
        else:
            self._run_data[
                SECTION_PROCGROUPS
            ][group][proc]["jobs"][job] = status
        await self.send_run_data(ws)

    async def on_job_queued(self, data, ws):
        await self._on_job(data, "queued", ws)

    async def on_job_submitted(self, data, ws):
        await self._on_job(data, "submitted", ws)

    async def on_job_killed(self, data, ws):
        await self._on_job(data, "killed", ws)

    async def on_job_failed(self, data, ws):
        await self._on_job(data, "failed", ws)

    async def on_job_succeeded(self, data, ws):
        await self._on_job(data, "succeeded", ws)

    async def on_job_cached(self, data, ws):
        await self._on_job(data, "succeeded", ws)

    def run_pipeline(self, command, ws):
        """Run a command and send the output to the websocket"""
        self.clear_run_data()
        self.running = True
        # TODO: Redirect stderr to stdout
        for line in cmdy.bash(c=command).iter():
            self._run_data[SECTION_LOG] += line


data_manager = DataManager()