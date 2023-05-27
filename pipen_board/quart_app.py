from __future__ import annotations

import os
import json
from pathlib import Path
from typing import TYPE_CHECKING

from quart import (
    Request,
    websocket,
    request,
    # copy_current_websocket_context,
)

from .defaults import Quart, logger
from .apis import GETS, POSTS, WS
from .data_manager import data_manager

if TYPE_CHECKING:
    from argparse import Namespace


def get_app(args: Namespace):
    """Get the Quart app."""

    class PipenBoardRequrest(Request):
        def __init__(self, *ags, **kwargs) -> None:
            super().__init__(*ags, **kwargs)
            self.cli_args = args

    os.environ["QUART_ENV"] = "development"
    app = Quart(
        __package__,
        static_folder=Path(__file__).parent / "frontend" / "build",
        static_url_path="/",
    )
    app.request_class = PipenBoardRequrest

    if args.dev:
        print(
            " * To enable dev mode in the UI, try: "
            f"http://127.0.0.1:{args.port}?dev=1"
        )

    @app.after_request
    async def _(r):
        if args.dev:
            r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            r.headers["Pragma"] = "no-cache"
            r.headers["Expires"] = "0"
            r.headers['Cache-Control'] = 'public, max-age=0'
        return r

    for route, handler in GETS.items():
        app.route(route, methods=["GET"])(handler)

    for route, handler in POSTS.items():
        app.route(route, methods=["POST"])(handler)

    clients = {}

    @app.websocket("/ws")
    async def ws():
        """The websocket handler"""
        client = None
        try:
            while True:
                message = await websocket.receive()
                message = json.loads(message)
                client = message["client"]
                if message["type"] == "connect":
                    clients[client] = websocket._get_current_object()
                    await WS[f"{client}/conn"](clients)
                else:
                    await WS[client](message, clients)
        finally:
            await WS[f"{client}/disconn"](clients)

    @app.route("/api/run", methods=["POST"])
    async def run():
        data = await request.get_json()

        command = data["command"]
        overwriteConfig = data["overwriteConfig"]
        config = data["config"]
        tomlfile = Path(data["tomlfile"])
        if not overwriteConfig and tomlfile.exists():
            return {}, 409
        try:
            tomlfile.write_text(config)
        except Exception:
            return {}, 410

        logger.info(
            f"[bold][yellow]API[/yellow][/bold] Running pipeline: {command}"
        )
        # Run command at background
        app.add_background_task(
            data_manager.run_pipeline,
            command,
            args.port,
        )
        return {"ok": True}

    @app.route("/api/pipeline/rerun", methods=["POST"])
    async def rerun():
        logger.info(
            f"[bold][yellow]API[/yellow][/bold] Re-Running pipeline: %s",
            data_manager._command,
        )
        # Run command at background
        app.add_background_task(
            data_manager.run_pipeline,
            data_manager._command,
            args.port,
        )
        return {"ok": True}

    return app
