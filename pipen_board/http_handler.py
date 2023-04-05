from __future__ import annotations

import http.server
import itertools
from typing import TYPE_CHECKING, Any, Type

from .api import GETS, POSTS
from .defaults import logger

if TYPE_CHECKING:
    from argparse import Namespace
    from pathlib import Path


def http_handler(
    root: Path,
    args: Namespace,
) -> Type[http.server.SimpleHTTPRequestHandler]:
    """
    Create a HTTP handler for the board server
    """
    class HTTPHandler(http.server.SimpleHTTPRequestHandler):
        # python 3.9 doesn't have self
        _control_char_table = str.maketrans(
            {
                c: rf"\x{c:02x}"
                for c in itertools.chain(range(0x20), range(0x7F, 0xA0))
            }
        )
        _control_char_table[ord("\\")] = r"\\"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root, **kwargs)

        def handle(self) -> None:
            try:
                return super().handle()
            except BrokenPipeError:
                pass

        def do_GET(self):
            if self.path in GETS:
                GETS[self.path](self, args)
            else:
                try:
                    super().do_GET()
                except BrokenPipeError:
                    pass

        def do_POST(self):
            if self.path in POSTS:
                POSTS[self.path](self, args)

        def log_message(self, format: str, *ags: Any) -> None:
            if not args.dev and (ags and ags[1] in ('200', '304')):
                return

            message = format % ags
            message = (
                f"[{self.address_string()}] "
                f"{message.translate(self._control_char_table)}"
            )
            logger.info(message)

    return HTTPHandler
