from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from quart import Quart, Request

from .apis import GETS, POSTS

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
    def _(r):
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

    return app
