from __future__ import annotations

import logging
import json
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING

import websocket
from slugify import slugify
from pipen.utils import get_marked
from pipen.pluginmgr import plugin

from .defaults import (
    NAME,
    SECTION_PROCESSES,
    SECTION_PROCGROUPS,
    SECTION_DIAGRAM,
    SECTION_REPORTS,
    logger,
)

if TYPE_CHECKING:
    from pipen import Pipen, Proc
    from pipen.job import Job


class PipenBoardPlugin:
    name = NAME
    # Let other plugins run first
    order = 9999

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

    def _connect(self, pipen: Pipen):
        portfile = (
            "pipen-board."
            f"{slugify(str(Path('.').resolve()))}."
            f"{slugify(pipen.name)}.port"
        )
        portfile = Path(gettempdir()).joinpath(portfile)
        if not portfile.is_file():
            logger.debug("No port file found, skip.")
            return

        port = portfile.read_text().strip()
        try:
            port = int(port)
        except ValueError:
            logger.debug("Not a valid port, skip.")
            return

        self.ws = websocket.WebSocket()
        try:
            self.ws.connect(f"ws://localhost:{port}/ws")
        except ConnectionRefusedError:
            logger.debug("Cannot connect to pipen-board, skip.")
            self.ws = None
        else:
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
        self._connect(pipen)
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
            if reports_dir.joinpath("index.html").is_file():
                data[SECTION_REPORTS] = str(reports_dir)

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
                }
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
                }
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
                }
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
                }
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
                }
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
                }
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
                }
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
                }
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
                }
            },
            log=job.log,
        )
