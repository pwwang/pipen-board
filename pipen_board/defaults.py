from __future__ import annotations

import logging
from pathlib import Path
from typing import Awaitable, Callable, Coroutine

from rich.logging import RichHandler
from hypercorn.config import Config as HyperConfig
from hypercorn.asyncio import serve
from quart import Quart as _Quart

NAME = "board"

# Use a different logger to avoid writing the logs from this plugin in
# terminal to the file (by plugin log2file)
logger = logging.getLogger(f"pipen-{NAME}")
logger.addHandler(
    RichHandler(
        show_path=False,
        omit_repeated_times=False,
        markup=True,
    )
)


class PluginNameLogFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, dict) and "s" in record.args:
            if record.args["s"] in (200, 304):
                record.levelno = logging.DEBUG
                record.levelname = "DEBUG"
            elif record.args["s"] == 404:
                record.levelno = logging.WARNING
                record.levelname = "WARNING"
            elif record.args["s"] >= 500:
                record.levelno = logging.ERROR
                record.levelname = "ERROR"
            if record.levelno < logger.level:
                return False

        return True


logger.addFilter(PluginNameLogFilter())
logging.getLogger('asyncio').setLevel(logging.WARNING)


# Subclass Quart to allow using logger
class Quart(_Quart):

    def run_task(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        debug: bool | None = None,
        ca_certs: str | None = None,
        certfile: str | None = None,
        keyfile: str | None = None,
        shutdown_trigger: Callable[..., Awaitable[None]] | None = None,
    ) -> Coroutine[None, None, None]:
        config = HyperConfig()
        config.access_log_format = "%(r)s %(s)s %(b)s %(D)s"
        config.accesslog = logger
        config.bind = [f"{host}:{port}"]
        config.ca_certs = ca_certs
        config.certfile = certfile
        if debug is not None:
            self.debug = debug
        config.errorlog = config.accesslog
        config.keyfile = keyfile

        return serve(self, config, shutdown_trigger=shutdown_trigger)


# Cached/saved pipeline data
PIPEN_BOARD_DIR = Path("~/.pipen-board").expanduser()
PIPEN_BOARD_DIR.mkdir(parents=True, exist_ok=True)

SECTION_PIPELINE_OPTIONS = "PIPELINE_OPTIONS"
SECTION_PROCGROUPS = "PROCGROUPS"
SECTION_PROCESSES = "PROCESSES"
SECTION_LOG = "LOG"
SECTION_DIAGRAM = "DIAGRAM"
SECTION_REPORTS = "REPORTS"

PIPELINE_OPTIONS = {
    "loglevel": {
        "type": "choice",
        "choices": ["debug", "info", "warning", "error", "critical"],
        "value": "info",
        "hidden": True,
        "desc": (
            "Logging level. "
            "This affects the log level of the main plugin."
        ),
    },
    "cache": {
        "type": "auto",
        "value": None,
        "placeholder": "true",
        "hidden": True,
        "desc": """# Job caching

If cache set to False (detected in the sequence of configuration files,
Pipen constructor, and process definition), the job is running anyway
regardless of previous runs.

If a previous run of a job fails, the job will be running anyway.

If a job is done successfully, a signature file will be generated for
the job. When we try to run the job again, the signature will be used
to check if we can skip running the job again but to use the results
generated by previous run.

We can also do a force-cache for a job by setting cache to "force".
This make sure of the results of previous successful run regardless of
input or script changes. This is useful for the cases that, for example,
you make some changes to input/script, but you don't want them to take
effect immediately, especially when the job takes long time to run.
""",
    },
    "submission_batch": {
        "type": "int",
        "placeholder": "8",
        "value": None,
        "hidden": True,
        "desc": "Number of jobs to submit at a time",
    },
    "scheduler": {
        "placeholder": "local",
        "value": None,
        "hidden": True,
        "desc": "The scheduler to use",
    },
    "scheduler_opts": {
        "desc": "The scheduler options",
        "value": {
            "<option_name>": {
                "type": "auto",
                "desc": "The value of the option",
            }
        }
    },
    "plugin_opts": {
        "desc": "The plugin options of your pipeline",
        "value": {
            "<plugin_name>_<plugin_opt_name>": {
                "desc": (
                    "The value of plugin option "
                    "`<plugin_name>_<plugin_opt_name>`"
                ),
                "type": "str",
            }
        }
    },
    "forks": {
        "type": "int",
        "placeholder": "1",
        "value": None,
        "desc": """Number of jobs to run in parallel for each process

The ability to run multiple jobs in parallel is provided by the the scheduler
system. For example, if you use the local scheduler, the jobs will be run in
parallel using the `multiprocessing` module. If you use the `sge` scheduler,
the jobs will be submitted to the slurm scheduler and run in parallel.
""",
    },
    "dirsig": {
        "type": "int",
        "placeholder": "1",
        "value": None,
        "hidden": True,
        "desc": "How deep we should go to check directory signature",
    },
    "error_strategy": {
        "type": "choice",
        "choices": ["ignore", "retry", "halk"],
        "choices_desc": [
            "Ignore the error and continue to run next jobs",
            "Retry the job",
            "Halt the pipeline",
        ],
        "value": "ignore",
        "desc": "What to do when a job fails",
        "hidden": True,
    },
    "num_retries": {
        "type": "int",
        "placeholder": "3",
        "value": None,
        "hidden": True,
        "desc": "Number of retries when a job fails. ",
    }
}

# See https://github.com/pwwang/xqute/blob/master/xqute/defaults.py#L34
JOB_STATUS = {
    "0": "INIT",
    "1": "RETRYING",
    "2": "QUEUED",
    "3": "SUBMITTED",
    "4": "RUNNING",
    "5": "KILLING",
    "6": "FINISHED",
    "7": "FAILED",
}
