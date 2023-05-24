from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from quart import request, redirect, send_file
from slugify import slugify

from .version import __version__
from .defaults import JOB_STATUS, PIPEN_BOARD_DIR, logger
from .data_manager import data_manager


if TYPE_CHECKING:
    from typing import Mapping, Any, Tuple


# Helper functions
def _get_children(parent: Path, idx: int = 0) -> Tuple[Mapping[str, Any], int]:
    """Get the children of a parent path"""
    out = []
    for child in parent.glob("*"):
        idx += 1
        item = {"id": idx, "text": child.name, "full": str(child)}
        if child.is_dir():
            item["children"], idx = _get_children(child, idx)
        out.append(item)
    return out, idx


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


# APIs
async def index():
    """Redirect to the index.html"""
    if request.cli_args.dev:
        return redirect('index.html?dev=1')
    return redirect('index.html')


async def history():
    logger.info("[bold][yellow]API[/yellow][/bold] Getting histories")
    args = request.cli_args
    out = {}
    out["pipeline"] = args.pipeline
    out["histories"] = []

    for histfile in PIPEN_BOARD_DIR.glob(
        f"{slugify(args.pipeline)}.{args.name}.*.json"
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

    return out


async def version():
    """Get the version of pipen-board"""
    return __version__


async def reports(report_path):
    root = request.args.get("root", None)
    root = root or reports.root
    if root is None:
        return {"error": "No root directory for reports is specified"}

    reports.root = root
    report_path = Path(root).parent / report_path
    if report_path.is_dir():
        report_path = report_path / "index.html"

    # Serve the file
    return await send_file(report_path)


# Cache the physical path of the reports
# A better way?
reports.root = None


async def report_building_log():
    """Get the building log of a report"""
    args = request.cli_args
    report_file = Path(args.root).joinpath(
        ".pipen",
        args.name,
        ".report-workdir",
        "pipen-report.log",
    )
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Getting building log: %s",
        report_file,
    )
    if not report_file.is_file():
        return {"ok": False, "content": "No report building log file found."}

    pattern =  re.compile(r'\x1B\[\d+(;\d+){0,2}m')
    return {"ok": True, "content": pattern.sub('', report_file.read_text())}


async def history_del():
    configfile = (await request.get_json())["configfile"]
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Deleting history: %s",
        configfile,
    )
    PIPEN_BOARD_DIR.joinpath(configfile).unlink()
    return {"ok": True}


async def pipeline_data():
    logger.info("[bold][yellow]API[/yellow][/bold] Getting pipeline data")
    configfile = (await request.get_json()).get("configfile")
    return data_manager.get_data(request.cli_args, configfile)


async def config_save():
    args = request.cli_args
    data = await request.get_json()
    configfile = data.get("configfile")
    configdata = data["data"]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = {"name": args.name, "mtime": now}
    if not configfile:
        configfile = PIPEN_BOARD_DIR.joinpath(
            f"{slugify(args.pipeline)}.{args.name}."
            f"{now.replace(' ', '_').replace(':', '-')}.json"
        )
        out["ctime"] = now
        logger.info(
            "[bold][yellow]API[/yellow][/bold] Saving config to a new file: "
            f"{configfile}"
        )
    else:
        configfile = PIPEN_BOARD_DIR.joinpath(configfile)
        logger.info(
            f"[bold][yellow]API[/yellow][/bold] Saving config to: {configfile}"
        )

    out["configfile"] = configfile.name
    configfile.write_text(configdata)
    return out


async def job_get_tree():
    args = request.cli_args
    data = await request.get_json()
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Fetching tree for: "
        f"{data['proc']}/{data['job']}"
    )
    jobdir = Path(args.root).joinpath(
        ".pipen",
        args.name,
        data["proc"],
        str(data["job"]),
    )
    if not jobdir.is_dir():
        return []

    # compose a treeview data
    # see: https://carbon-components-svelte.onrender.com/components/TreeView
    return _get_children(jobdir)[0]


async def job_get_file():
    """Get file details"""
    data = await request.get_json()
    how = data.get("how", "full")
    path = Path(data["path"])
    if how != "full":
        logger.info(
            "[bold][yellow]API[/yellow][/bold] Fetching file for "
            f"{data['proc']}/{data['job']}: {path} ({how})"
        )
        return {"type": "bigtext-part", "content": _get_file_content(path, how)}

    logger.info(
        "[bold][yellow]API[/yellow][/bold] Fetching file for "
        f"{data['proc']}/{data['job']}: {path}"
    )
    if (
        path.name.startswith("job.wrapped.")
        or path.name in ("job.script", "job.signature.toml", "job.rc")
    ):
        return {"type": "text", "content": path.read_text()}

    if path.name == "job.status":
        st_code = path.read_text().strip()
        status = JOB_STATUS.get(st_code, "UNKNOWN")
        return {"type": "text", "content": f"{st_code} ({status})"}

    # check different types of files and sizes of them
    if path.suffix in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
        return {
            "type": "image",
            "content": (
                f"data:image/{path.suffix[1:]};base64,"
                f"{base64.b64encode(path.read_bytes()).decode()}"
            ),
        }

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
            return {"type": "bigtext", "content": "".join(lines)}

        return {"type": "text", "content": path.read_text()}

    return {"type": "binary"}


async def pipeline_stop():
    return await data_manager.stop_pipeline()


async def ws_web(data, clients):
    logger.info(f"WS/WEB Received: {data}")


async def ws_pipeline(data, clients):
    logdata = str(data)
    # if len(logdata) > 100:
    #     logdata = logdata[:100] + "..."

    logger.info(f"WS/PIPELINE Received: {logdata}")
    type = data.get("type")
    if (
        type
        and type.startswith("on_")
        and callable(getattr(data_manager, type, None))
    ):
        await getattr(data_manager, type)(data["data"], clients.get("web"))


async def ws_web_conn(clients):
    logger.info("WS/WEB Client 'web' connected.")
    # send the current run data, to let UI know the current status
    await data_manager.send_run_data(clients["web"], True)


async def ws_pipeline_conn(clients):
    logger.info("WS/PIPELINE Client 'pipeline' connected.")


async def ws_web_disconn(clients):
    logger.info("WS/WEB Client 'web' disconnected.")


async def ws_pipeline_disconn(clients):
    logger.info("WS/PIPELINE Client 'pipeline' disconnected.")
    data_manager.running = False


GETS = {
    "/": index,
    "/api/history": history,
    "/api/version": version,
    "/api/report_building_log": report_building_log,
    "/reports/<path:report_path>": reports,
}

POSTS = {
    "/api/pipeline": pipeline_data,
    "/api/history/del": history_del,
    "/api/config/save": config_save,
    "/api/job/get_tree": job_get_tree,
    "/api/job/get_file": job_get_file,
    "/api/pipeline/stop": pipeline_stop,
}

WS = {
    "web": ws_web,
    "pipeline": ws_pipeline,
    "web/conn": ws_web_conn,
    "pipeline/conn": ws_pipeline_conn,
    "web/disconn": ws_web_disconn,
    "pipeline/disconn": ws_pipeline_disconn,
}
