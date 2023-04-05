from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from quart import Quart, Request

from .defaults import logger
from .apis import GETS, POSTS

if TYPE_CHECKING:
    from argparse import Namespace


def get_app(args: Namespace):
    """Get the Quart app."""
    if args.dev:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")

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

    for route, handler in GETS.items():
        app.route(route, methods=["GET"])(handler)

    for route, handler in POSTS.items():
        app.route(route, methods=["POST"])(handler)

    return app
