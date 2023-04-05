from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from slugify import slugify

from .defaults import PIPEN_BOARD_DIR, JOB_STATUS, logger
from .pipeline_parsing import get_pipeline_data_process, parse_perv_run

if TYPE_CHECKING:
    from argparse import Namespace
    from http.server import SimpleHTTPRequestHandler


def _end_with_json(
    handler: SimpleHTTPRequestHandler,
    data: str | Mapping[str, Any],
    is_string: bool = False,
):
    handler.send_response(200)
    handler.send_header("Content-type", "application/json")
    handler.end_headers()
    if not is_string:
        data = json.dumps(data).encode()
    handler.wfile.write(data)


def _end_with_text(
    handler: SimpleHTTPRequestHandler,
    data: str | Mapping[str, Any],
):
    handler.send_response(200)
    handler.send_header("Content-type", "text/plain")
    handler.end_headers()
    handler.wfile.write(data.encode())


def _post_data(
    handler: SimpleHTTPRequestHandler,
    as_string: bool = False,
) -> Mapping[str, Any]:
    string = handler.rfile.read(int(handler.headers["Content-Length"])).decode()
    if as_string:
        return string
    return json.loads(string)


def history(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Get the history of the current pipeline."""
    logger.info("[API] Getting histories")
    out = {}
    out["pipeline"] = args.pipeline
    out["histories"] = []

    for histfile in PIPEN_BOARD_DIR.glob(
        f"{slugify(args.pipeline)}.{slugify(args.name)}.*.json"
    ):
        out["histories"].append({
            "name": args.name,
            "configfile": histfile.name,
            # 2023-01-01_00-00-00 to
            # 2023-01-01 00:00:00
            "ctime": (
                histfile.stem.split(".")[-1]
                .replace("_", " ")
                .replace("-", ":")
                .replace(":", "-", 2)
            ),
            "mtime": (
                datetime.fromtimestamp(histfile.stat().st_mtime)
                .strftime("%Y-%m-%d %H:%M:%S")
            ),
        })

    _end_with_json(handler, out)


def history_get(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Get pipeline data from a history file."""
    configfile = _post_data(handler)["configfile"]
    logger.info("[API] Getting history from: %s", configfile)
    _end_with_json(
        handler,
        PIPEN_BOARD_DIR.joinpath(configfile).read_bytes(),
        is_string=True,
    )


def history_del(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Delete a history file."""
    configfile = _post_data(handler)["configfile"]
    logger.info("[API] Deleting history: %s", configfile)
    PIPEN_BOARD_DIR.joinpath(configfile).unlink()
    _end_with_text(handler, "OK")


def config_pipeline_data(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Get the pipeline data from the config file."""
    logger.info("[API] Getting a fresh pipeline data")
    # Use multiprocessing to get a clean environment
    # to load the pipeline to avoid conflicts
    data = get_pipeline_data_process(args)
    _end_with_json(handler, data, is_string=True)


def config_save(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Save the pipeline config to the loaded file."""
    data = _post_data(handler)
    configfile = data.get("configfile")
    configdata = data["data"]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = {"name": args.name, "mtime": now}
    if not configfile:
        configfile = PIPEN_BOARD_DIR.joinpath(
            f"{slugify(args.pipeline)}.{slugify(args.name)}."
            f"{now.replace(' ', '_').replace(':', '-')}.json"
        )
        out["ctime"] = now
        logger.info("[API] Saving config to a new file: %s", configfile)
    else:
        configfile = PIPEN_BOARD_DIR.joinpath(configfile)
        logger.info("[API] Saving config to: %s", configfile)

    out["configfile"] = configfile.name
    configfile.write_text(configdata)
    _end_with_json(handler, out)


def run_prev(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Collect the previous run data."""
    logger.info("[API] Fetching previous run data")
    data = _post_data(handler)
    configfile = data.get("configfile")
    parsed = parse_perv_run(args, configfile)
    _end_with_json(handler, parsed)


def _get_children(parent: Path, idx: int = 0) -> Mapping[str, Any]:
    """Get the children of a parent path"""
    out = []
    for child in parent.glob("*"):
        idx += 1
        item = {"id": idx, "text": child.name, "full": str(child)}
        if child.is_dir():
            item["children"] = _get_children(child, idx)
            idx += len(item["children"])
        out.append(item)
    return out


def job_get_tree(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Get the file tree of the given job"""
    data = _post_data(handler)
    logger.info("[API] Fetching tree for: %s/%s", data["proc"], data["job"])
    jobdir = Path(args.root).joinpath(
        ".pipen",
        slugify(args.name),
        slugify(data["proc"]),
        str(data["job"]),
    )
    if not jobdir.is_dir():
        return _end_with_json(handler, [])

    # compose a treeview data
    # see: https://carbon-components-svelte.onrender.com/components/TreeView
    _end_with_json(handler, _get_children(jobdir))


def _get_file_content(path: Path, how: str) -> str:
    how, n = how.split(" ", 1)
    n = int(n)
    lines = path.read_text().splitlines()

    if how == "Head":
        return "\n".join(lines[:n])

    return "\n".join(lines[-n:])


def _is_text_file(file_path: str | Path) -> bool:
    """Check if the file is a text file"""
    try:
        with open(file_path) as file:
            file.read(1)
    except UnicodeDecodeError:
        return False
    return True


def job_get_file(handler: SimpleHTTPRequestHandler, args: Namespace):
    """Get file details"""
    data = _post_data(handler)
    how = data.get("how", "full")
    path = Path(data["path"])
    if how != "full":
        logger.info(
            "[API] Fetching file for %s/%s: %s (%s)",
            data["proc"],
            data["job"],
            path,
            how,
        )
        return _end_with_json(
            handler,
            {"type": "bigtext-part", "content": _get_file_content(path, how)},
        )

    logger.info(
        "[API] Fetching file for %s/%s: %s",
        data["proc"],
        data["job"],
        path,
    )
    if (
        path.name.startswith("job.wrapped.")
        or path.name in ("job.script", "job.signature.toml", "job.rc")
    ):
        return _end_with_json(
            handler,
            {"type": "text", "content": path.read_text()},
        )

    if path.name == "job.status":
        st_code = path.read_text().strip()
        status = JOB_STATUS.get(st_code, "UNKNOWN")
        return _end_with_json(
            handler,
            {"type": "text", "content": f"{st_code} ({status})"},
        )

    # check different types of files and sizes of them
    if path.suffix in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
        return _end_with_json(
            handler,
            # content should be a base64 encoded string
            {
                "type": "image",
                "content": (
                    f"data:image/{path.suffix[1:]};base64,"
                    f"{base64.b64encode(path.read_bytes()).decode()}"
                ),
            },
        )

    if _is_text_file(path):
        # check the size of the file
        size = path.stat().st_size
        if size > 1024 * 1024:  # 1MB
            # read first 100 lines
            lines = []
            with path.open() as f:
                for i, line in enumerate(f):
                    lines.append(line)
                    if i > 100:
                        break
            return _end_with_json(
                handler,
                {"type": "bigtext", "content": "".join(lines)},
            )

        return _end_with_json(
            handler,
            {"type": "text", "content": path.read_text()},
        )

    return _end_with_json(
        handler,
        {"type": "binary"},
    )


GETS = {
    "/api/history": history,
    "/api/config/pipeline": config_pipeline_data,
}

POSTS = {
    "/api/run/prev": run_prev,
    "/api/history/del": history_del,
    "/api/history/get": history_get,
    "/api/config/save": config_save,
    "/api/job/get_tree": job_get_tree,
    "/api/job/get_file": job_get_file,
}
