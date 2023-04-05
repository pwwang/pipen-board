from __future__ import annotations
import base64

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich import print
from quart import request, redirect
from slugify import slugify

from .defaults import JOB_STATUS, PIPEN_BOARD_DIR
from .pipeline_parsing import get_pipeline_data_process, parse_perv_run

if TYPE_CHECKING:
    from typing import Mapping, Any


# Helper functions
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
    print(" * [API] Getting histories")
    args = request.cli_args
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

    return out


async def history_get():
    configfile = (await request.get_json())["configfile"]
    print(" * [API] Getting history from: %s", configfile)
    return PIPEN_BOARD_DIR.joinpath(configfile).read_text()


async def history_del():
    configfile = (await request.get_json())["configfile"]
    print(" * [API] Deleting history: %s", configfile)
    PIPEN_BOARD_DIR.joinpath(configfile).unlink()
    return "OK"


async def config_pipeline_data():
    print(" * [API] Getting a fresh pipeline data")
    # Use multiprocessing to get a clean environment
    # to load the pipeline to avoid conflicts
    return get_pipeline_data_process(request.cli_args)


async def config_save():
    args = request.cli_args
    data = await request.get_json()
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
        print(f" * [API] Saving config to a new file: {configfile}")
    else:
        configfile = PIPEN_BOARD_DIR.joinpath(configfile)
        print(f" * [API] Saving config to: {configfile}")

    out["configfile"] = configfile.name
    configfile.write_text(configdata)
    return out


async def run_prev():
    print(" * [API] Fetching previous run data")
    data = await request.get_json()
    configfile = data.get("configfile")
    return parse_perv_run(request.cli_args, configfile)


async def job_get_tree():
    args = request.cli_args
    data = await request.get_json()
    print(f" * [API] Fetching tree for: {data['proc']}/{data['job']}")
    jobdir = Path(args.root).joinpath(
        ".pipen",
        slugify(args.name),
        slugify(data["proc"]),
        str(data["job"]),
    )
    if not jobdir.is_dir():
        return []

    # compose a treeview data
    # see: https://carbon-components-svelte.onrender.com/components/TreeView
    return _get_children(jobdir)


async def job_get_file():
    """Get file details"""
    data = await request.get_json()
    how = data.get("how", "full")
    path = Path(data["path"])
    if how != "full":
        print(
            " * [API] Fetching file for "
            f"{data['proc']}/{data['job']}: {path} ({how})"
        )
        return {"type": "bigtext-part", "content": _get_file_content(path, how)}

    print(
        " * [API] Fetching file for "
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


GETS = {
    "/": index,
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