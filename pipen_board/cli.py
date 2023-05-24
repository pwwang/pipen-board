"""Provides PipenCliConfigPlugin"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from pipen.cli import CLIPlugin

from .version import __version__
from .defaults import NAME, logger
from .quart_app import get_app

if TYPE_CHECKING:  # pragma: no cover
    from argx import ArgumentParser, Namespace


class PipenCliBoardPlugin(CLIPlugin):
    """Configure and run pipen pipelines on the web"""

    name = NAME
    __version__ = __version__

    def __init__(
        self,
        parser: ArgumentParser,
        subparser: ArgumentParser,
    ) -> None:
        super().__init__(parser, subparser)
        subparser.usage = "%(prog)s [options] <pipeline> -- [pipeline options]"
        subparser.add_argument(
            "-p",
            "--port",
            type=int,
            default=18521,
            help="Port to serve the UI wizard",
        )
        subparser.add_argument(
            "-n",
            "--name",
            help=(
                "The name of the pipeline. Default to the pipeline class name. "
                "You can use a different name to associate with a different "
                "set of configurations."
            )
        )
        subparser.add_argument(
            "-a",
            "--additional",
            metavar="FILE",
            help=(
                "Additional arguments for the pipeline, "
                "in YAML, INI, JSON or TOML format. "
                "Can have sections `ADDITIONAL_OPTIONS` and `RUNNING_OPTIONS`"
            ),
        )
        subparser.add_argument(
            "--loglevel",
            default="auto",
            choices=["auto", "debug", "info", "warning", "error", "critical"],
            help=(
                "The logging level. If `auto`, it will be set to `debug` "
                "if `--dev` is set, otherwise `info`."
            ),
        )
        subparser.add_argument(
            "--dev",
            action="store_true",
            help=(
                "Run the pipeline in development/debug mode. "
                "This will reload the server when changes are made to this "
                "package and reload the pipeline when page reloads for new "
                "configurations. Page cache is also disabled in this mode."
            ),
        )
        subparser.add_argument(
            "--root",
            help="The root directory of the pipeline.",
            default=".",
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
        args, rest = args[:idx], args[idx + 1:]
        parsed = self.parser.parse_args(args=args)
        parsed.name = parsed.name or parsed.pipeline.rpartition(":")[-1]
        parsed.pipeline_args = rest
        return parsed

    def exec_command(self, args: Namespace) -> None:
        """Execute the command"""
        if args.loglevel == "auto":
            logger.setLevel("DEBUG" if args.dev else "INFO")
        else:
            logger.setLevel(args.loglevel.upper())

        print(" * ")
        print(" *        __   __  __         __  __      __  __")
        print(" *       |__)||__)|_ |\ | __ |__)/  \ /\ |__)|  \\")
        print(" *       |   ||   |__| \|    |__)\__//--\| \ |__/")
        print(" * ")
        print(" *                   version: %s" % __version__)
        print(" * ")
        print("\n".join(map(lambda x: f" * {x}", self.__doc__.splitlines())))
        print(" * ")

        app = get_app(args)
        # See https://github.com/pallets/quart/issues/224
        # for customizing logger in the future
        app.run(port=args.port, debug=args.dev, use_reloader=args.dev)
