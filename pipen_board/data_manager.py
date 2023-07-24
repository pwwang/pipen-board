"""Provides the running data and functions to mutate it"""
from __future__ import annotations

import asyncio
import json
import os
import re
import signal
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

from simpleconf import Config
from slugify import slugify
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
    "FINISHED": False,
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
        # Avoid "pipeline" to be used as pipeline name
        [pipeline] = [pipeline()]

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
        argspec[arg]["desc"] = re.sub(
            r"([\.\?!:])\s*\n",
            "\\1<br />\n",
            arginfo.help,
        )
        if arg.startswith("<") and arg.endswith(">"):
            argspec[arg].setdefault("order", 999)
        if "btype" not in argspec[arg]:
            if (
                argspec[arg].get("text")
                or argspec[arg].get("mline")
                or argspec[arg].get("mlines")
            ):
                argspec[arg]["type"] = "text"
            elif argspec[arg].get("action") in (
                "store_true",
                "store_false",
            ) or argspec[arg].get("flag"):
                argspec[arg]["type"] = "bool"
            elif (
                argspec[arg].get("action") in ("ns", "namespace")
                or argspec[arg].get("ns")
                or argspec[arg].get("namespace")
            ):
                argspec[arg]["type"] = "ns"
            elif (
                argspec[arg].get("action")
                in ("append", "extend", "clear_append", "clear_extend")
                or argspec[arg].get("array")
                or argspec[arg].get("list")
            ):
                argspec[arg]["type"] = "list"
            elif argspec[arg].get("choices") or argspec[arg].get("choice"):
                argspec[arg]["type"] = "choice"
            elif argspec[arg].get("mchoice") or argspec[arg].get("mchoices"):
                argspec[arg]["type"] = "mchoice"
        else:
            argspec[arg]["type"] = argspec[arg].pop("btype")

        t = argspec[arg].get("type")
        if t == "ns":
            argspec[arg]["value"] = _anno_to_argspec(arginfo.terms)
        elif t in ("choice", "mchoice"):
            argspec[arg]["value"] = argspec[arg].get("default", [])
            argspec[arg]["choices"] = list(arginfo.terms)
            argspec[arg]["choices_desc"] = [
                term.help if not term.help else term.help.splitlines()[0]
                for term in arginfo.terms.values()
            ]
            argspec[arg]["desc"] += "\n"
            # Add the choices to the description
            for termname, term in arginfo.terms.items():
                h = re.sub(r"([\.\?!:])\s*\n", "\\1<br />\n", term.help)
                argspec[arg]["desc"] += f"- `{termname}`: {h}\n"
        else:
            argspec[arg]["value"] = argspec[arg].get("default", None)

        # determine the itype for list elements
        if t == "list":
            if argspec[arg]["value"] is not None and not isinstance(
                argspec[arg]["value"], list
            ):
                argspec[arg]["value"] = [argspec[arg]["value"]]
            if (
                argspec[arg]["value"] is not None
                and argspec[arg]["value"]
                and "bitype" not in argspec[arg]
                and "itype" not in argspec[arg]
                and not isinstance(argspec[arg]["value"][0], str)
            ):
                argspec[arg]["itype"] = type(argspec[arg]["value"][0]).__name__

            if "bitype" in argspec[arg]:
                argspec[arg]["itype"] = argspec[arg].pop("bitype")

    # argspec.setdefault("default", argspec.get("value", None))
    return argspec


def _get_default(argspec: Mapping[str, Any], force_ns: bool = False) -> Any:
    """Set the default using the value for the argspec

    This can be used to omit the argument in final config in frontend
    in case the value is the same as the default
    """
    value = argspec.get("value", None)
    if not force_ns and argspec.get("type") not in ("ns", "namespace"):
        argspec.setdefault("default", value)
        return argspec["default"]

    # flatten the namespace
    if value is None:
        argspec.setdefault("default", {})
        return argspec["default"]

    default = {}
    for arg, arginfo in value.items():
        # placeholder
        if arg.startswith("<") and arg.endswith(">"):
            continue

        # Set the default for sub-item
        dlt = _get_default(arginfo)
        default[arg] = dlt

    argspec.setdefault("default", default)
    return default


def _proc_to_argspec(
    proc: Proc | Type[Proc],
    is_start: bool,
    hidden: bool = False,
    order: int = 0,
) -> Mapping[str, Any]:
    """Convert the proc to the argument spec"""
    if isinstance(proc, Proc):
        anno = annotate(proc.__class__)
    else:
        anno = annotate(proc)

    summary = anno.get("Summary", {"short": "", "long": ""})
    argspec = {
        "is_start": is_start,
        "order": order,
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
    _get_default(argspec["value"]["envs"], force_ns=True)

    argspec["value"]["plugin_opts"] = PIPELINE_OPTIONS["plugin_opts"]
    _get_default(argspec["value"]["plugin_opts"], force_ns=True)

    argspec["value"]["scheduler_opts"] = PIPELINE_OPTIONS["scheduler_opts"]
    _get_default(argspec["value"]["scheduler_opts"], force_ns=True)

    argspec["value"]["forks"] = PIPELINE_OPTIONS["forks"]
    _get_default(argspec["value"]["forks"])

    argspec["value"]["cache"] = PIPELINE_OPTIONS["cache"]
    _get_default(argspec["value"]["cache"])

    argspec["value"]["scheduler"] = PIPELINE_OPTIONS["scheduler"]
    _get_default(argspec["value"]["scheduler"])

    argspec["value"]["dirsig"] = PIPELINE_OPTIONS["dirsig"]
    _get_default(argspec["value"]["dirsig"])

    argspec["value"]["error_strategy"] = PIPELINE_OPTIONS["error_strategy"]
    _get_default(argspec["value"]["error_strategy"])

    argspec["value"]["num_retries"] = PIPELINE_OPTIONS["num_retries"]
    _get_default(argspec["value"]["num_retries"])

    argspec["value"]["lang"] = {
        "desc": "The interpreter to run the script",
        "hidden": True,
        "placeholder": proc.lang,
        # Don't include it in the config file if not specified
        "value": None,
        "default": None,
    }

    return argspec


def _load_additional(additional: str, **kwargs) -> Mapping[str, Any]:
    """Load additional config files

    Args:
        additional: The additional config file to load
        kwargs: Key-value pairs to render the additional config file,
            which is a liquid/jinja2 template
    """
    if not additional:
        return {}

    if additional.startswith("gh://"):
        # To avoid the first part being parsed as hostname
        additional = f"gh:{additional[5:]}"

    parsed = urlparse(additional)
    cache_dir = Path(gettempdir()) / "pipen-cli-config-additional-configs"
    cache_dir.mkdir(parents=True, exist_ok=True)
    if parsed.scheme in ("http", "https", "ftp", "ftps", "gh"):
        from hashlib import sha256
        from urllib.error import URLError
        from urllib.request import urlretrieve

        if parsed.scheme == "gh":
            try:
                user, repo, file_path = parsed.path.split("/", 2)
            except ValueError:
                raise ValueError(f"Invalid gh:// URL: {additional}")
            branch = "master"
            if "@" in file_path:
                file_path, branch = file_path.split("@")
            parsed = urlparse(
                "https://raw.githubusercontent.com/"
                f"{user}/{repo}/{branch}/{file_path}"
            )

        url = parsed.geturl()
        cache_key = sha256(url.encode("utf-8")).hexdigest()
        additional = cache_dir / f"{cache_key}-{parsed.path.split('/')[-1]}"
        if not additional.exists():
            try:
                urlretrieve(url, additional)
            except URLError:
                raise ValueError(
                    f"Could not retrieve remote path: {additional}"
                ) from None

    if kwargs:
        # kwargs passed, treat the file as a template
        additional = Path(additional)
        tpl = Liquid(additional.read_text(), mode="wild", from_file=False)
        additional = cache_dir.joinpath(
            f"{slugify(str(additional.resolve()))}.rendered{additional.suffix}"
        )
        additional.write_text(tpl.render(**kwargs))

    out = Config.load(additional)
    if "ADDITIONAL_OPTIONS" in out:
        for val in out["ADDITIONAL_OPTIONS"].values():
            _get_default(val)

    return out


def _update_dict(d1: Mapping[str, Any], d2: Mapping[str, Any]) -> None:
    """Update d1 with d2 recursively"""
    for key, val in d2.items():
        if key in d1 and isinstance(val, dict) and isinstance(d1[key], dict):
            _update_dict(d1[key], val)
        else:
            d1[key] = val


async def _get_config_data(
    args: Namespace,
    name: str | None,
) -> Mapping[str, Any]:
    """Get the pipeline data"""
    try:
        old_argv = sys.argv
        sys.argv = ["@pipen-board"] + args.pipeline_args
        logger.info("[bold][yellow]DBG[/yellow][/bold] Fetching pipeline data ...")
        try:
            pipeline = parse_pipeline(args.pipeline)
            # Initialize the pipeline so that the arguments definied by
            # other plugins (i.e. pipen-args) to take in place.
            pipeline.workdir = Path(pipeline.config.workdir).joinpath(
                name or pipeline.name
            )
            await pipeline._init()
            pipeline.workdir.mkdir(parents=True, exist_ok=True)
            pipeline.build_proc_relationships()
        finally:
            sys.argv = old_argv

        data = {}
        data[SECTION_PIPELINE_OPTIONS] = PIPELINE_OPTIONS.copy()
        data[SECTION_PIPELINE_OPTIONS]["name"] = {
            "type": "str",
            "value": name or pipeline.name,
            "default": pipeline.name,
            "placeholder": name or pipeline.name,
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
                "The description of the pipeline, " "shows in the log and report."
            ),
        }
        data[SECTION_PIPELINE_OPTIONS]["outdir"] = {
            "desc": "The output directory of your pipeline",
            "placeholder": "./<name>-output",
            "type": "str",
            "value": None,
        }
        for key, val in data[SECTION_PIPELINE_OPTIONS].items():
            _get_default(val, key in ("plugin_opts", "scheduler_opts"))

        data[SECTION_PROCESSES] = {}

        if pipeline.config.plugin_opts.get("args_flatten") is True or (
            "args_flatten" not in pipeline.config.plugin_opts
            and len(pipeline.procs) == 1
        ):
            data[SECTION_PIPELINE_OPTIONS]["plugin_opts"]["value"][
                "args_flatten"
            ] = {
                "desc": (
                    "Flatten the arguments of the pipeline. "
                    "For example, [envs] will ba treated as [<Process>.envs]. "
                    "Only works for single-process pipeline"
                ),
                "type": "bool",
                "value": True,
                "default": True,
                "readonly": True,
            }

        pg_sec = {}
        for i, proc in enumerate(pipeline.procs):
            logger.info(
                "[bold][yellow]DBG[/yellow][/bold] Parsing process: %s ...",
                proc,
            )

            pg = proc.__meta__["procgroup"]
            if pg:
                if pg.name not in pg_sec:
                    pg_sec[pg.name] = {"PROCESSES": {}}
                    pg_anno = annotate(pg.__class__)
                    # desc
                    pg_summ = pg_anno.get("Summary", {"short": "", "long": ""})
                    pg_sec[pg.name][
                        "desc"
                    ] = f'# {pg_summ["short"]}\n\n{pg_summ["long"]}'
                    # args
                    pg_args = _anno_to_argspec(pg_anno.get("Args")) or {}
                    # Implemented by pipen-annotate 0.7.3
                    # for arg, arginfo in pg_args.items():
                    #     arginfo["value"] = pg.DEFAULTS.get(arg)
                    pg_sec[pg.name]["ARGUMENTS"] = pg_args
                pg_sec[pg.name][SECTION_PROCESSES][proc.name] = _proc_to_argspec(
                    proc,
                    proc in pipeline.starts,
                    get_marked(proc, "board_config_hidden", False),
                    order=i,
                )
            else:
                data[SECTION_PROCESSES][proc.name] = _proc_to_argspec(
                    proc,
                    proc in pipeline.starts,
                    get_marked(proc, "board_config_hidden", False),
                    order=i,
                )

        data[SECTION_PROCGROUPS] = pg_sec

        if args.additional:
            logger.info(
                "[bold][yellow]DBG[/yellow][/bold] "
                "Loading additional configuration items ..."
            )
            if (
                args.additional == "auto"
                and args.pipeline.rpartition(":")[0].endswith(".py")
            ):
                additional = str(
                    Path(__file__).parent.joinpath("additional_auto.toml")
                )
            else:
                additional = args.additional

            addi_data = _load_additional(
                additional,
                name=name or pipeline.name,
                pipeline=args.pipeline,
                pipeline_args=args.pipeline_args,
            )
            _update_dict(data, addi_data)

    except Exception as e:
        import traceback
        return {"error": traceback.format_exc()}

    return data


class DataManager:
    """Gather and manager the pipeline data"""

    # Send data every 5 seconds to the client, via websocket
    INTERVAL = 5

    def __init__(self) -> None:
        self.running: int | bool = False
        self._config_data = None
        self._run_data = None
        self._timer = None
        self._proc_running_order = 0
        self._command = None

    def _get_config_data(
        self,
        args: Namespace,
        configfile: str,
    ):
        """Get the config data of the pipeline

        Args:
            args: The arguments from the CLI
            configfile: The name to the config file
        """
        if configfile and not configfile.startswith("new:") and not args.dev:
            with PIPEN_BOARD_DIR.joinpath(configfile).open() as f:
                self._config_data = json.load(f)
                return

        self._config_data = None
        if not configfile:
            name = None
        elif configfile.startswith("new:"):
            name = configfile[4:]
        else:
            self._config_data = json.loads(
                PIPEN_BOARD_DIR.joinpath(configfile).read_text()
            )
            name = self._config_data[SECTION_PIPELINE_OPTIONS]["name"]["value"]

        if not self._config_data:
            # Use multiprocessing to get a clean environment
            # to load the pipeline to avoid conflicts
            def target(conn):
                conn.send(
                    json.dumps(
                        asyncio.run(_get_config_data(args, name))
                    ).encode()
                )
                conn.close()

            parent_conn, child_conn = Pipe()
            p = Process(target=target, args=(child_conn,))
            p.start()
            data = parent_conn.recv()
            p.join()

            self._config_data = json.loads(data)
            if "error" in self._config_data:
                for line in self._config_data["error"].splitlines():
                    logger.error(line)

                from quart import abort
                abort(500)

        self._config_data[SECTION_PIPELINE_OPTIONS]["name"]["value"] = (
            name
            or self._config_data[SECTION_PIPELINE_OPTIONS]["name"]["default"]
        )

    def _get_prev_run(self, args: Namespace, configfile: str | None):
        """Get data for the previous run

        Args:
            args: The parsed arguments from cli
            configfile: The config file to use, if not specified, use a
                fresh one loaded from the pipeline object
                It could also be "new:<name>" for a new instance.
        """
        out = self._run_data = {SECTION_LOG: None, "FINISHED": True}
        self._get_config_data(args, configfile=configfile)
        name = self._config_data[SECTION_PIPELINE_OPTIONS]["name"]["value"]
        pipeline_dir = Path(args.workdir).joinpath(name)
        if not pipeline_dir.is_dir():
            # no previous run, return defaults
            self._run_data = DEFAULT_RUN_DATA
            return

        # Get the log
        logfile = pipeline_dir.joinpath("run-latest.log")
        if logfile.exists() and logfile.is_file():
            out[SECTION_LOG] = logfile.read_text()
        else:
            # no previous run, return defaults
            self._run_data = DEFAULT_RUN_DATA
            return

        config_data = self._config_data
        outdir = config_data[SECTION_PIPELINE_OPTIONS].get(
            "outdir",
            {"value": None},
        )["value"]
        if not outdir:
            outdir = Path(args.workdir).parent.joinpath(f"{name}-output")
        else:
            outdir = Path(outdir)

        report_procs_dir = outdir.joinpath("REPORTS", "procs")
        if report_procs_dir.is_dir() and [
            p for p in report_procs_dir.glob("*") if p.is_dir()
        ]:
            out[SECTION_REPORTS] = str(outdir)

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
        self._proc_running_order = 0
        if not keep_log:
            self._run_data = deepcopy(DEFAULT_RUN_DATA)
        else:
            log = self._run_data[SECTION_LOG]
            self._run_data = deepcopy(DEFAULT_RUN_DATA)
            self._run_data[SECTION_LOG] = log

    def get_data(self, args: Namespace, configfile: str | None):
        """Get the data"""
        if not self.running:
            self._get_prev_run(args, configfile=configfile)
            return {
                "runStarted": False,
                "config": self._config_data,
                "run": self._run_data,
            }

        self._get_config_data(args, configfile=configfile)
        return {
            "runStarted": True,
            "config": self._config_data,
            "run": self._run_data,
        }

    async def send_run_data(self, ws, force: bool = False):
        if ws is None:
            return
        if not force and time.time() - self._timer < self.INTERVAL:
            return

        # Send data
        logger.debug(
            "[bold][yellow]DBG[/yellow][/bold] Sending run data to the frontend"
        )
        try:
            await ws.send(json.dumps(self._run_data))
        except BrokenPipeError:
            pass

        # Reset timer
        self._timer = time.time()

    async def on_start(self, data, ws):
        self._proc_running_order = 0
        # { SECTION_PROCESSES: [p1, p2], SECTION_PROCGROUPS: {pg1: [p3, p4]} }
        if isinstance(data, str):
            data = json.loads(data)

        logger.info("WS/PIPELINE Received: Pipeline started")

        if SECTION_DIAGRAM in data:
            self._run_data[SECTION_DIAGRAM] = data[SECTION_DIAGRAM]

        if SECTION_PROCESSES in data:
            for proc in data[SECTION_PROCESSES]:
                self._run_data[SECTION_PROCESSES][proc] = {
                    "order": 0,
                    "status": "init",
                    "jobs": [],
                }

        if SECTION_PROCGROUPS in data:
            for pg in data[SECTION_PROCGROUPS]:
                self._run_data[SECTION_PROCGROUPS][pg] = {}
                for proc in data[SECTION_PROCGROUPS][pg]:
                    self._run_data[SECTION_PROCGROUPS][pg][proc] = {
                        "status": "init",
                        "jobs": [],
                    }

        self.timer = time.time()
        await self.send_run_data(ws, force=True)

    async def on_complete(self, data, ws):
        if isinstance(data, str):
            data = json.loads(data)

        logger.info(
            "WS/PIPELINE Received: Pipeline completed (succeeded=%s)",
            data['succeeded'],
        )

        if SECTION_REPORTS in data:
            self._run_data[SECTION_REPORTS] = data[SECTION_REPORTS]

        self.running = False
        self._run_data["FINISHED"] = True
        await self.send_run_data(ws, force=True)
        self._proc_running_order = 0

    async def on_proc_start(self, data, ws):
        if isinstance(data, str):
            data = json.loads(data)

        proc, group, njobs = data["proc"], data["procgroup"], data["njobs"]

        logger.info(
            "WS/PIPELINE Received: Process started: %s (size=%s)",
            proc,
            njobs,
        )

        if not group:
            self._run_data[SECTION_PROCESSES][proc][
                "order"
            ] = self._proc_running_order
            self._run_data[SECTION_PROCESSES][proc]["status"] = "running"
            self._run_data[SECTION_PROCESSES][proc]["jobs"] = ["init"] * njobs
        else:
            self._run_data[SECTION_PROCGROUPS][group][proc][
                "order"
            ] = self._proc_running_order
            self._run_data[SECTION_PROCGROUPS][group][proc][
                "status"
            ] = "running"
            self._run_data[SECTION_PROCGROUPS][group][proc]["jobs"] = [
                "init"
            ] * njobs

        self._proc_running_order += 1
        await self.send_run_data(ws, force=True)

    async def on_proc_done(self, data, ws):
        if isinstance(data, str):
            data = json.loads(data)

        proc, group, succeeded = (
            data["proc"],
            data["procgroup"],
            data["succeeded"],
        )

        logger.info(
            "WS/PIPELINE Received: Process done: %s (succeeded=%s)",
            proc,
            succeeded,
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

        logger.info(
            "WS/PIPELINE Received: Job %s (%s#%s)",
            status,
            proc,
            job,
        )

        if not group:
            self._run_data[SECTION_PROCESSES][proc]["jobs"][job] = status
        else:
            self._run_data[SECTION_PROCGROUPS][group][proc]["jobs"][
                job
            ] = status
        await self.send_run_data(ws)

    async def on_job_queued(self, data, ws):
        await self._on_job(data, "queued", ws)

    async def on_job_submitted(self, data, ws):
        await self._on_job(data, "submitted", ws)

    async def on_job_running(self, data, ws):
        await self._on_job(data, "running", ws)
        # Notify the frontend that the job is running
        await self.send_run_data(ws, force=True)

    async def on_job_killed(self, data, ws):
        await self._on_job(data, "killed", ws)

    async def on_job_failed(self, data, ws):
        await self._on_job(data, "failed", ws)

    async def on_job_succeeded(self, data, ws):
        await self._on_job(data, "succeeded", ws)

    async def on_job_cached(self, data, ws):
        await self._on_job(data, "succeeded", ws)

    async def run_pipeline(self, command, port, ws_clients):
        """Run a command and send the output to the websocket"""
        self.clear_run_data()
        self._run_data[SECTION_LOG] = self._run_data[SECTION_LOG] or ""

        p = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            p.stdin.write(f"pipen-board:{port}\n".encode())
            p.stdin.close()
        except RuntimeError:
            # command is already finished, probably due to an error
            pass
        self.running = p.pid
        self._command = command

        while True:
            line = await p.stdout.readline()
            if not line:
                break

            self._run_data[SECTION_LOG] += line.decode()
            # In case it's too long to data between hooks
            await self.send_run_data(ws_clients.get("web"))

        await p.wait()
        # In case the pipeline fails to start
        self._run_data["FINISHED"] = True
        self.running = False
        await self.send_run_data(ws_clients.get("web"), force=True)

    async def stop_pipeline(self):
        """Stop the pipeline"""
        if not self.running:
            return {"ok": False, "msg": "Pipeline is not running"}

        logger.debug(
            "[bold][yellow]DBG[/yellow][/bold] Killing pipeline at %s ...",
            self.running,
        )

        # Let the pipeline send signals to the jobs
        # The jobs could be on some scheduler systems
        try:
            os.kill(self.running, signal.SIGINT)
        except ProcessLookupError:
            return {
                "ok": False,
                "msg": (
                    "Pipeline probably failed to start. You may want to "
                    "restart the pipen-board server and try again."
                ),
            }

        await asyncio.sleep(3)
        # Start killing
        import psutil

        try:
            proc = psutil.Process(self.running)
        except psutil.NoSuchProcess:
            # Might be killed by SIGINT
            pass
        else:
            for child in proc.children(recursive=True):
                try:
                    child.terminate()
                    await asyncio.sleep(1)
                except psutil.NoSuchProcess:
                    pass
                try:
                    child.kill()
                    await asyncio.sleep(1)
                except psutil.NoSuchProcess:
                    pass

            try:
                proc.terminate()
                await asyncio.sleep(1)
                proc.kill()
                await asyncio.sleep(1)
            except psutil.NoSuchProcess:
                pass

        self.running = False
        self._run_data["FINISHED"] = True
        return {"ok": True, "msg": "Pipeline killed"}


data_manager = DataManager()
