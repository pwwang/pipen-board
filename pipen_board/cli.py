"""Provides PipenCliConfigPlugin"""
from __future__ import annotations

import asyncio
import signal
import sys
from typing import TYPE_CHECKING, Any
from pathlib import Path

from panpath import PanPath
from pipen.cli import AsyncCLIPlugin
from quart.utils import MustReloadError, observe_changes, restart

from .version import __version__
from .defaults import NAME, logger
from .quart_app import get_app

if TYPE_CHECKING:  # pragma: no cover
    from argx import ArgumentParser, Namespace


class PipenCliBoardPlugin(AsyncCLIPlugin):
    """Configure and run pipen pipelines from the web"""

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
            "-a",
            "--additional",
            metavar="FILE",
            help=(
                "Additional arguments for the pipeline, "
                "in YAML, INI, JSON or TOML format. "
                "Can have sections `ADDITIONAL_OPTIONS` and `RUNNING_OPTIONS`. "
                "It can also have other sections and items to override the "
                "configurations generated from the pipeline. "
                "If the pipeline is provided as a python script, such as "
                "`/path/to/pipeline.py:<pipeline>`, and `<pipeline>` runs "
                "under `__name__ == '__main__'`, the additional file can also "
                "be specified as `auto` to generate a `RUNNING OPTIONS/Local` "
                "section to run the pipeline locally."
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
            "-w",
            "--workdir",
            help="The working directory of the pipeline.",
            default=".pipen",
        )
        subparser.add_argument(
            "-s",
            "--schema-dir",
            dest="schema_dir",
            help="The directory to store the configuration schemas.",
            default="./.pipen-board",
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

    async def parse_args(self, known_parsed, unparsed_argv) -> Namespace:
        """Parse the arguments"""
        # split the args into two parts, separated by `--`
        # the first part is the args for pipen_cli_config
        # the second part is the args for the pipeline
        args = sys.argv[1:]
        idx = args.index("--") if "--" in args else len(args)
        args, rest = args[:idx], args[idx + 1:]
        parsed = self.parser.parse_args(args=args)
        parsed.pipeline_args = rest
        parsed.schema_dir = PanPath(parsed.schema_dir)
        if isinstance(parsed.schema_dir, Path):
            parsed.schema_dir.expanduser()
        parsed.workdir = PanPath(parsed.workdir)
        if isinstance(parsed.workdir, Path):
            parsed.workdir.expanduser()
        return parsed

    async def exec_command(self, args: Namespace) -> None:
        """Execute the command"""

        if args.loglevel == "auto":
            logger.setLevel("DEBUG" if args.dev else "INFO")
        else:
            logger.setLevel(args.loglevel.upper())

        print(" * ")
        print(" *        __   __  __.  .     __  __   +  __  __")
        print(" *       |__)||__)|_ |\\ | __ |__)/  \\ /\\ |__)|  \\")
        print(" *       |   ||   |__| \\|    |__)\\__//--\\| \\ |__/")
        print(" * ")
        print(" *                   version: %s" % __version__)
        print(" * ")
        print("\n".join(map(lambda x: f" * {x}", self.__doc__.splitlines())))
        print(" * ")
        print(f" * Running on http://0.0.0.0:{args.port} (CTRL + C to quit)")

        app = get_app(args)
        # See https://github.com/pallets/quart/issues/224
        # for customizing logger in the future
        if not args.dev:
            await app.run_task(host="0.0.0.0", port=args.port, debug=False)
            return

        # In dev mode, reload the server when the package is changed
        # (mirroring quart's sync `run()` implementation, as `run_task`
        # does not support `use_reloader`)
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def _signal_handler(*_: Any) -> None:
            shutdown_event.set()

        for signal_name in {"SIGINT", "SIGTERM", "SIGBREAK"}:
            if hasattr(signal, signal_name):
                try:
                    loop.add_signal_handler(
                        getattr(signal, signal_name), _signal_handler
                    )
                except NotImplementedError:
                    signal.signal(getattr(signal, signal_name), _signal_handler)

        tasks = [
            loop.create_task(
                app.run_task(
                    host="0.0.0.0",
                    port=args.port,
                    debug=True,
                    shutdown_trigger=shutdown_event.wait,
                )
            ),
            loop.create_task(observe_changes(asyncio.sleep, shutdown_event)),
        ]
        reload_ = False
        try:
            await asyncio.gather(*tasks)
        except MustReloadError:
            reload_ = True
        finally:
            # Cancel the tasks to release the sockets before restarting
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        if reload_:
            restart()
