from __future__ import annotations

import logging
import json
import sys
import selectors
from typing import TYPE_CHECKING

import websocket
from pipen.utils import get_marked, get_logger
from pipen.pluginmgr import plugin

from .version import __version__
from .defaults import (
    NAME,
    SECTION_PROCESSES,
    SECTION_PROCGROUPS,
    SECTION_DIAGRAM,
    SECTION_REPORTS,
)

if TYPE_CHECKING:
    from pipen import Pipen, Proc
    from pipen.job import Job

logger = get_logger(NAME)


class PipenBoardPlugin:
    name = NAME
    # Let other plugins run first
    priority = 9999
    __version__ = __version__

    def __init__(self):
        self.ws = None

    def _send(self, data, log=None):
        if self.ws:
            data["client"] = "pipeline"
            try:
                self.ws.send(json.dumps(data))
            except BrokenPipeError:
                pass

            logdata = str(data)
            if len(logdata) > 100:
                logdata = logdata[:100] + "..."
            logmsg = f"SENDING {logdata}"
            if log is None:
                logger.debug(logmsg)
            else:
                log("debug", logmsg, logger=logger)

    def _connect(self):
        """Connect to pipen-board server"""
        if not sys.stdin.readable():
            self.ws = None
            logger.debug("Stdin is not readable, skip.")
            return

        sel = selectors.DefaultSelector()
        sel.register(sys.stdin, selectors.EVENT_READ)
        if not sel.select(timeout=1):
            self.ws = None
            logger.debug("No data in stdin, skip.")
            return

        port = sys.stdin.readline().strip()
        if not port.startswith("pipen-board:"):
            self.ws = None
            logger.debug("Not spawned by pipen-board server, skip.")
            return

        # Now that we are spawned by pipen-board
        port = int(port[12:])
        self.ws = websocket.WebSocket()
        self.ws.connect(f"ws://localhost:{port}/ws")
        logger.info(f"Connected to pipen-board at ws://localhost:{port}/ws")
        self._send({"type": "connect", "client": "pipeline"})

    def _disconnect(self):
        if self.ws:
            self.ws.close()
            self.ws = None

    @plugin.impl
    async def on_start(self, pipen: Pipen):
        logger.setLevel(
            getattr(logging, pipen.config.get("loglevel", "INFO").upper())
        )
        self._connect()
        if not self.ws:
            return

        data = {}
        diagram = pipen.outdir.joinpath("diagram.svg")
        if diagram.is_file():
            data[SECTION_DIAGRAM] = diagram.read_text()

        for proc in pipen.procs:
            pg = get_marked(proc, "procgroup")
            if pg:
                group = data.setdefault(SECTION_PROCGROUPS, {})
                group.setdefault(pg.name, []).append(proc.name)
            else:
                data.setdefault(SECTION_PROCESSES, []).append(proc.name)

        self._send({"type": "on_start", "data": data})

    @plugin.impl
    async def on_complete(self, pipen: Pipen, succeeded: bool):
        data = {"succeeded": succeeded}
        if succeeded:
            reports_dir = pipen.outdir.joinpath("REPORTS")
            if (
                reports_dir.joinpath("index.html").is_file()
                and reports_dir.joinpath("procs").is_dir()
                and [p for p in reports_dir.joinpath("procs").iterdir()]
            ):
                data[SECTION_REPORTS] = str(reports_dir.parent)

        self._send({"type": "on_complete", "data": data})
        self._disconnect()

    @plugin.impl
    async def on_proc_start(self, proc: Proc):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_proc_start",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "njobs": len(proc.jobs),
                },
            },
            log=proc.log,
        )

    @plugin.impl
    async def on_proc_done(self, proc: Proc, succeeded: bool):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_proc_done",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "succeeded": succeeded,
                },
            },
            log=proc.log,
        )

    @plugin.impl
    async def on_job_queued(self, proc: Proc, job: Job):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_job_queued",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "job": job.index,
                },
            },
            log=job.log,
        )

    @plugin.impl
    async def on_job_submitted(self, proc: Proc, job: Job):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_job_submitted",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "job": job.index,
                },
            },
            log=job.log,
        )

    @plugin.impl
    async def on_job_running(self, proc: Proc, job: Job):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_job_running",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "job": job.index,
                },
            },
            log=job.log,
        )

    @plugin.impl
    async def on_job_killed(self, proc: Proc, job: Job):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_job_killed",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "job": job.index,
                },
            },
            log=job.log,
        )

    @plugin.impl
    async def on_job_succeeded(self, proc: Proc, job: Job):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_job_succeeded",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "job": job.index,
                },
            },
            log=job.log,
        )

    @plugin.impl
    async def on_job_failed(self, proc: Proc, job: Job):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_job_failed",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "job": job.index,
                },
            },
            log=job.log,
        )

    @plugin.impl
    async def on_job_cached(self, proc: Proc, job: Job):
        group = get_marked(proc, "procgroup")
        if group:
            group = group.name

        self._send(
            {
                "type": "on_job_cached",
                "data": {
                    "proc": proc.name,
                    "procgroup": group,
                    "job": job.index,
                },
            },
            log=job.log,
        )
