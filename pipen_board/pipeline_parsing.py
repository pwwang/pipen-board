from __future__ import annotations
from curses.ascii import isdigit

import sys
import json
import asyncio
import importlib
import importlib.util
from multiprocessing import Pipe, Process
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING, Any, Mapping, Type
from urllib.parse import urlparse

from liquid import Liquid
from simpleconf import Config
from slugify import slugify
from pipen import Proc, ProcGroup, Pipen
from pipen.utils import get_marked
from pipen_annotate import annotate

from .defaults import (
    PIPEN_BOARD_DIR,
    SECTION_PIPELINE_OPTIONS,
    SECTION_PROCESSES,
    SECTION_PROCGROUPS,
    PIPELINE_OPTIONS,
    logger,
)

if TYPE_CHECKING:
    from argparse import Namespace


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


def anno_to_argspec(
    anno: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
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
            argspec[arg]["value"] = anno_to_argspec(arginfo.terms)
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


def proc_to_argspec(
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
            "value": anno_to_argspec(anno.get("Input", {})),
        }
    argspec["value"]["envs"] = {
        "desc": "Environment variables for the process, used across jobs",
        "value": anno_to_argspec(anno.get("Envs", {})),
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


def load_additional(additional: str, **kwargs) -> Mapping[str, Any]:
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


async def get_pipeline_data(args: Namespace) -> Mapping[str, Any]:
    """Get the pipeline data"""
    old_argv = sys.argv
    sys.argv = ["from-pipen-cli-config"] + args.pipeline_args
    logger.info("Fetching pipeline data ...")
    try:
        pipeline = parse_pipeline(args.pipeline)
        # Initialize the pipeline so that the arguments definied by
        # other plugins (i.e. pipen-args) to take in place.
        await pipeline._init()
        pipeline.build_proc_relationships()
    finally:
        sys.argv = old_argv

    if args.additional:
        logger.info("Loading additional configuration items ...")
        data = load_additional(
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
        logger.debug("Parsing process %s ..." % proc.name)

        pg = proc.__meta__["procgroup"]
        if pg:
            if pg.name not in pg_sec:
                pg_sec[pg.name] = {"PROCESSES": {}}
                pg_args = anno_to_argspec(
                    annotate(pg.__class__).get("Args")
                )
                if pg_args:
                    for arg, arginfo in pg_args.items():
                        arginfo["value"] = pg.DEFAULTS.get(arg)
                    pg_sec[pg.name]["ARGUMENTS"] = pg_args

            pg_sec[pg.name][SECTION_PROCESSES][proc.name] = proc_to_argspec(
                proc,
                proc in pipeline.starts,
                get_marked(proc, "board_config_hidden", False),
            )
        else:
            data[SECTION_PROCESSES][proc.name] = proc_to_argspec(
                proc,
                proc in pipeline.starts,
                get_marked(proc, "board_config_hidden", False),
            )

    data[SECTION_PROCGROUPS] = pg_sec
    return data


def get_pipeline_data_process(
    args: Namespace,
    use_cached: bool | str = "auto",
) -> str:
    """Get the pipeline data in a separate process

    Args:
        args: The arguments from the CLI
        use_cached: Whether to use the cached data
            - auto: use the cached data if args.dev is True, otherwise don't
            - True: use the cached data regardless of args.dev
            - False: don't use the cached data anyway regardless of args.dev
    """
    if (
        (use_cached is True or (use_cached == "auto" and args.dev))
        and get_pipeline_data_process.cached
    ):
        return get_pipeline_data_process.cached

    # Use multiprocessing to get a clean environment
    # to load the pipeline to avoid conflicts
    def target(conn):
        conn.send(
            json.dumps(asyncio.run(get_pipeline_data(args))).encode()
        )
        conn.close()

    parent_conn, child_conn = Pipe()
    p = Process(target=target, args=(child_conn,))
    p.start()
    data = parent_conn.recv()
    p.join()

    get_pipeline_data_process.cached = data
    return data


get_pipeline_data_process.cached = None


def parse_perv_run(
    args: Namespace,
    configfile: str | None,
) -> Mapping[str, Any]:
    """Get previous run data"""
    out = {}
    pipeline_dir = Path(args.root).joinpath(".pipen", slugify(args.name))
    if not pipeline_dir.is_dir():
        return out

    if not configfile:
        pipeline_data = json.loads(
            get_pipeline_data_process(args, use_cached=True)
        )
    else:
        with PIPEN_BOARD_DIR.joinpath(configfile).open() as f:
            pipeline_data = json.load(f)

    outdir = pipeline_data[SECTION_PIPELINE_OPTIONS].get(
        "outdir",
        {"value": None},
    )["value"]
    outdir = outdir or Path(args.root).joinpath(f"{slugify(args.name)}_results")
    reports_dir = outdir.joinpath("REPORTS")
    if reports_dir.joinpath("index.html").is_file():
        out["reports"] = str(reports_dir)

    diagram = outdir.joinpath("diagram.svg")
    if diagram.is_file():
        out["diagram"] = diagram.read_text()

    out[SECTION_PROCESSES] = {}
    out[SECTION_PROCGROUPS] = {}

    def process_proc(proc: str, container: dict):
        procdir = pipeline_dir.joinpath(slugify(proc))
        container[proc] = []
        if not procdir.is_dir():
            return
        for jobdir in sorted(
            [j for j in procdir.glob("*") if j.name.isdigit()],
            key=lambda x: int(x.name),
        ):
            rcfile = jobdir / "job.rc"
            try:
                container[proc].append(
                    int(rcfile.read_text().strip())
                )
            except Exception:
                container[proc].append(-8525)

    for proc in pipeline_data[SECTION_PROCESSES]:
        process_proc(proc, out[SECTION_PROCESSES])

    for pg in pipeline_data[SECTION_PROCGROUPS]:
        out[SECTION_PROCGROUPS][pg] = {}
        for proc in pipeline_data[SECTION_PROCGROUPS][pg][SECTION_PROCESSES]:
            process_proc(proc, out[SECTION_PROCGROUPS][pg])

    return out
