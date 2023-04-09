from __future__ import annotations

import json
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING

from slugify import slugify
from quart import (
    Request,
    websocket,
    request,
    # copy_current_websocket_context,
)

from .defaults import Quart, logger
from .apis import GETS, POSTS, WS
from .ws_broker import Broker
from .data_manager import data_manager

if TYPE_CHECKING:
    from argparse import Namespace


def get_app(args: Namespace):
    """Get the Quart app."""

    class PipenBoardRequrest(Request):
        def __init__(self, *ags, **kwargs) -> None:
            super().__init__(*ags, **kwargs)
            self.cli_args = args

    app = Quart(
        __package__,
        static_folder=Path(__file__).parent / "frontend" / "build",
        static_url_path="/",
    )
    app.request_class = PipenBoardRequrest

    @app.after_request
    async def _(r):
        if args.dev:
            r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            r.headers["Pragma"] = "no-cache"
            r.headers["Expires"] = "0"
            r.headers['Cache-Control'] = 'public, max-age=0'
        return r

    @app.before_serving
    async def _():
        # save the port to the file
        # with given root and name
        # so that the plugin can read it and connect to it
        portfile = (
            "pipen-board."
            f"{slugify(str(Path(args.root).resolve()))}."
            f"{slugify(args.name)}.port"
        )
        Path(gettempdir()).joinpath(portfile).write_text(str(args.port))

    @app.after_serving
    async def _():
        portfile = (
            "pipen-board."
            f"{slugify(str(Path(args.root).resolve()))}."
            f"{slugify(args.name)}.port"
        )
        try:
            Path(gettempdir()).joinpath(portfile).unlink()
        except FileNotFoundError:
            pass

    for route, handler in GETS.items():
        app.route(route, methods=["GET"])(handler)

    for route, handler in POSTS.items():
        app.route(route, methods=["POST"])(handler)

    broker = Broker()
    clients = {}
    async def _receive() -> None:
        while True:
            message = await websocket.receive()
            message = json.loads(message)
            if message["type"] == "connect":
                client = message["client"]
                clients[client] = websocket._get_current_object()
                await WS[f"{client}/conn"](clients)
            else:
                await broker.publish(message)

    @app.websocket("/ws")
    async def ws():
        """The websocket handler"""
        # try:
        #     task = asyncio.ensure_future(_receive())
        #     async for message in broker.subscribe():
        #         client = message["client"]
        #         await WS[client](message, clients)
        # finally:
        #     task.cancel()
        #     await task
        #     await WS[f"{client}/disconn"](clients)
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

        logger.info(f"API Running pipeline: {command}")
        # Run command at background
        app.add_background_task(
            data_manager.run_pipeline,
            command,
            clients.get("web"),
        )
        return {"ok": True}

    return app
