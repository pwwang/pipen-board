"""Provides PipenCliConfigPlugin"""
from __future__ import annotations

import socketserver
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pipen.cli import CLIPlugin

from .defaults import logger
from .http_handler import http_handler

if TYPE_CHECKING:  # pragma: no cover
    from argx import ArgumentParser, Namespace


class PipenCliBoardPlugin(CLIPlugin):
    """Visualize configuration and running of pipen pipelines on the web"""

    name = "board"

    def __init__(
        self,
        parser: ArgumentParser,
        subparser: ArgumentParser,
    ) -> None:
        super().__init__(parser, subparser)
        subparser.usage = "%(prog)s [options] <pipeline> -- [pipeline options]"
        subparser.add_argument(
            "--port",
            type=int,
            default=18521,
            help="Port to serve the UI wizard",
        )
        subparser.add_argument(
            "--name",
            help=(
                "The name of the pipeline. Default to the pipeline class name. "
                "You can use a different name to associate with a different "
                "set of configurations."
            )
        )
        subparser.add_argument(
            "--additional",
            metavar="FILE",
            help=(
                "Additional arguments for the pipeline, "
                "in YAML, INI, JSON or TOML format. "
                "Can have sections `ADDITIONAL_OPTIONS` and `RUNNING_OPTIONS`"
            ),
        )
        subparser.add_argument(
            "--dev",
            action="store_true",
            help=(
                "Run the pipeline in development mode. "
                "This will print verbosal logging information and reload "
                "the pipeline if a new instantce starts when page reloads."
            ),
        )
        subparser.add_argument(
            "--root",
            help="The root directory of the pipeline.",
            default=".",
        )
        subparser.add_argument(
            "--loglevel",
            help=(
                "Logging level. If `auto`, "
                "set to `debug` if `--dev` is set, otherwise `info`"
            ),
            choices=("auto", "debug", "info", "warning", "error", "critical"),
            default="auto",
        )
        subparser.add_argument(
            "pipeline",
            help=(
                "The pipeline and the CLI arguments to run the pipeline. "
                "For the pipeline either `/path/to/pipeline.py:<pipeline>` "
                "or `<module.submodule>:<pipeline>` "
                "`<pipeline>` must be an instance of `Pipen` and running "
                "the pipeline should be called under `__name__ == '__main__'."
            ),
        )

    def parse_args(self) -> Namespace:
        """Parse the arguments"""
        # split the args into two parts, separated by `--`
        # the first part is the args for pipen_cli_config
        # the second part is the args for the pipeline
        args = sys.argv[1:]
        idx = args.index("--") if "--" in args else len(args)
        args, rest = args[:idx], args[idx + 1 :]
        parsed = self.parser.parse_args(args=args)
        parsed.name = parsed.name or parsed.pipeline.rpartition(":")[-1]
        parsed.pipeline_args = rest
        return parsed

    def exec_command(self, args: Namespace) -> None:
        """Execute the command"""
        if args.loglevel == "auto":
            args.loglevel = "debug" if args.dev else "info"
        logger.setLevel(args.loglevel.upper())

        logger.info(
            f"[bold]pipen-{self.name}: [/bold]{self.__doc__}"
        )
        logger.info(f"[bold]version: [/bold]{self.__version__}")
        logger.info("")

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(
            ("", args.port),
            http_handler(
                Path(__file__).parent.joinpath("frontend", "build"),
                args,
            ),
        ) as httpd:
            port = httpd.server_address[1]
            url = f"Serving UI at http://localhost:{port}"
            logger.info(f"{url}?dev=1" if args.dev else url)
            logger.info("Press Ctrl+C to exit")
            logger.info("")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logger.error("Stopping the server")
