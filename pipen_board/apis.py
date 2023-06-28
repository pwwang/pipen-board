from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from quart import abort, request, redirect, send_file
from slugify import slugify

from .version import __version__
from .defaults import (
    JOB_STATUS,
    PIPEN_BOARD_DIR,
    SECTION_PIPELINE_OPTIONS,
    logger,
)
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
        return redirect("index.html?dev=1")
    return redirect("index.html")


async def history():
    logger.info("[bold][yellow]API[/yellow][/bold] Getting histories")
    args = request.cli_args
    out = {}
    out["pipeline"] = args.pipeline
    out["histories"] = []
    curr_workdir = Path(args.workdir).resolve()

    for histfile in PIPEN_BOARD_DIR.glob(f"{slugify(args.pipeline)}.*.*.json"):
        name = histfile.stem.split(".")[-2]
        workdir = base64.b64decode(
            histfile.stem.split(".")[-1] + "=="
        ).decode()
        out["histories"].append(
            {
                "name": name,
                "configfile": histfile.name,
                "workdir": workdir,
                "is_current": Path(workdir).resolve() == curr_workdir,
                # 2023-01-01_00-00-00 to
                # 2023-01-01 00:00:00
                "ctime": (
                    datetime.fromtimestamp(histfile.stat().st_ctime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),
                "mtime": (
                    datetime.fromtimestamp(histfile.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ),
            }
        )

    return out


async def version():
    """Get the version of pipen-board"""
    return __version__


async def pipeline_data():
    logger.info("[bold][yellow]API[/yellow][/bold] Getting pipeline data")
    configfile = (await request.get_json()).get("configfile")
    return data_manager.get_data(request.cli_args, configfile)


async def reports(report_path):
    """Get the reports"""
    root, rest = report_path.split("/", 1)
    root = root.replace("|", "/")

    report_path = Path(root) / rest
    if report_path.is_dir():
        report_path = report_path / "index.html"

    if not report_path.is_file():
        return abort(404)
    # Serve the file
    return await send_file(report_path)


async def report_building_log():
    """Get the building log of a report"""
    args = request.cli_args
    name = request.args["name"]
    report_file = Path(args.workdir).joinpath(
        name,
        ".report-workdir",
        "pipen-report.log",
    )
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Getting building log: %s",
        report_file,
    )
    if not report_file.is_file():
        return {"ok": False, "content": "No report building log file found."}

    pattern = re.compile(r"\x1B\[\d+(;\d+){0,2}m")
    return {"ok": True, "content": pattern.sub("", report_file.read_text())}


async def history_del():
    configfile = (await request.get_json())["configfile"]
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Deleting history: %s",
        configfile,
    )
    PIPEN_BOARD_DIR.joinpath(configfile).unlink()
    return {"ok": True}


async def history_saveas():
    req = await request.get_json()
    args = request.cli_args
    configfile = req["configfile"]
    newname = req["new_name"]

    logger.info(
        "[bold][yellow]API[/yellow][/bold] Save history: %s with new name: %s",
        configfile,
        newname,
    )
    try:
        jdata = json.loads(PIPEN_BOARD_DIR.joinpath(configfile).read_text())
        jdata[SECTION_PIPELINE_OPTIONS]["name"]["value"] = newname

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        workdir = Path(args.workdir).resolve().as_posix()
        out = {
            "name": newname,
            "is_current": True,
            "mtime": now,
            "ctime": now,
            "workdir": workdir,
        }
        enc = base64.b64encode(workdir.encode()).decode().rstrip("=")
        newconfigfile = PIPEN_BOARD_DIR.joinpath(
            f"{slugify(args.pipeline)}.{newname}.{enc}.json"
        )

        if newconfigfile.is_file():
            return {"ok": False, "error": "File already exists."}

        for val in jdata.get("RUNNING_OPTIONS", {}).values():
            configfile_opt = val.get("configfile", "configfile")
            if not val["value"][configfile_opt].get("changed"):
                val["value"][configfile_opt]["value"] = val["value"][
                    configfile_opt
                ]["placeholder"] = f"{newname}.config.toml"

        newconfigfile.write_text(json.dumps(jdata, indent=4))
        out["configfile"] = newconfigfile.name

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return out


async def history_download():
    req = await request.get_json()
    configfile = req["configfile"]
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Downloading schema: %s",
        configfile,
    )
    return await send_file(
        PIPEN_BOARD_DIR.joinpath(configfile),
        as_attachment=True,
    )


async def history_upload():
    # get form data
    form = await request.files
    # load as json
    jdata = json.load(form["schema_file"])
    name = jdata[SECTION_PIPELINE_OPTIONS]["name"]["value"]
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Receiving schema file with name: %s",
        name,
    )
    workdir = Path(request.cli_args.workdir).resolve().as_posix()
    enc = base64.b64encode(workdir.encode()).decode().rstrip("=")
    schema_file = PIPEN_BOARD_DIR.joinpath(
        f"{slugify(request.cli_args.pipeline)}.{name}.{enc}.json"
    )
    if schema_file.is_file():
        return {"ok": False, "error": "File already exists."}

    schema_file.write_text(json.dumps(jdata, indent=4))
    return {
        "name": name,
        "mtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ctime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workdir": workdir,
        "is_current": True,
        "configfile": schema_file.name,
    }


async def history_fromurl():
    # get form data
    url = (await request.get_json())["url"]
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Receiving schema file from url: %s",
        url,
    )
    try:
        import urllib.request
        with urllib.request.urlopen(url) as response:
            jdata = json.loads(response.read().decode())

        name = jdata[SECTION_PIPELINE_OPTIONS]["name"]["value"]
        workdir = Path(request.cli_args.workdir).resolve().as_posix()
        enc = base64.b64encode(workdir.encode()).decode().rstrip("=")
        schema_file = PIPEN_BOARD_DIR.joinpath(
            f"{slugify(request.cli_args.pipeline)}.{name}.{enc}.json"
        )
        if schema_file.is_file():
            return {"ok": False, "error": "File already exists."}

        schema_file.write_text(json.dumps(jdata, indent=4))
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    return {
        "name": name,
        "mtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ctime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workdir": workdir,
        "is_current": True,
        "configfile": schema_file.name,
    }


async def config_save():
    args = request.cli_args
    data = await request.get_json()
    configfile = data.get("configfile")
    configdata = data["data"]
    jdata = json.loads(configdata)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = jdata[SECTION_PIPELINE_OPTIONS]["name"]["value"]
    workdir = Path(args.workdir).resolve().as_posix()
    out = {"name": name, "mtime": now}
    enc = base64.b64encode(workdir.encode()).decode().rstrip("=")
    if not configfile:
        # base64 encode the workdir path
        configfile = PIPEN_BOARD_DIR.joinpath(
            f"{slugify(args.pipeline)}.{name}.{enc}.json"
        )
        for val in jdata.get("RUNNING_OPTIONS", {}).values():
            configfile_opt = val.get("configfile", "configfile")
            if not val["value"][configfile_opt].get("changed"):
                val["value"][configfile_opt]["value"] = val["value"][
                    configfile_opt
                ]["placeholder"] = f"{name}.config.toml"

        out["ctime"] = now
        out["is_current"] = True
        out["workdir"] = workdir
        logger.info(
            "[bold][yellow]API[/yellow][/bold] Saving config to a new file: "
            f"{configfile}"
        )
    elif configfile.startswith("new:"):
        name = (
            configfile[4:]
            or jdata[SECTION_PIPELINE_OPTIONS]["name"]["default"]
        )
        jdata[SECTION_PIPELINE_OPTIONS]["name"]["value"] = name
        for val in jdata.get("RUNNING_OPTIONS", {}).values():
            configfile_opt = val.get("configfile", "configfile")
            if not val["value"][configfile_opt].get("changed"):
                val["value"][configfile_opt]["value"] = val["value"][
                    configfile_opt
                ]["placeholder"] = f"{name}.config.toml"

        configdata = json.dumps(jdata, indent=4)
        configfile = PIPEN_BOARD_DIR.joinpath(
            f"{slugify(args.pipeline)}.{name}.{enc}.json"
        )
        if configfile.exists():
            return {"ok": False, "error": "File already exists."}

        out["name"] = name
        out["ctime"] = now
        out["is_current"] = True
        out["workdir"] = workdir
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
    jobdir = Path(args.workdir).joinpath(
        data["name"],
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
        return {
            "type": "bigtext-part",
            "content": _get_file_content(path, how),
        }

    logger.info(
        "[bold][yellow]API[/yellow][/bold] Fetching file for "
        f"{data['proc']}/{data['job']}: {path}"
    )
    if path.name.startswith("job.wrapped.") or path.name in (
        "job.script",
        "job.signature.toml",
        "job.rc",
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


async def job_get_file_metadata():
    data = await request.get_json()
    path = Path(data["path"])
    logger.info(
        "[bold][yellow]API[/yellow][/bold] Fetching file metadata for "
        f"{data['proc']}/{data['job']}: {path}"
    )

    size = size_human = path.stat().st_size
    base = 1024
    size_human = abs(float(size_human))
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if size_human < base:
            break
        size_human /= base

    return {
        "name": path.name,
        "size": size,
        "size_human": f"{size_human:.2f} {unit}",
        "ctime": datetime.fromtimestamp(path.stat().st_ctime).isoformat(
            sep=" ", timespec="seconds"
        ),
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(
            sep=" ", timespec="seconds"
        ),
    }


async def pipeline_stop():
    return await data_manager.stop_pipeline()


async def ws_web(data, clients):
    logger.info(f"WS/WEB Received: {data}")


async def ws_pipeline(data, clients):
    # logdata = str(data)
    # if len(logdata) > 100:
    #     logdata = logdata[:100] + "..."

    # logger.info(f"WS/PIPELINE Received: {logdata}")
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
    "/api/history/saveas": history_saveas,
    "/api/history/download": history_download,
    "/api/history/upload": history_upload,
    "/api/history/fromurl": history_fromurl,
    "/api/config/save": config_save,
    "/api/job/get_tree": job_get_tree,
    "/api/job/get_file": job_get_file,
    "/api/job/get_file_metadata": job_get_file_metadata,
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
