import os
from pipen import Pipen, Proc
from dotenv import load_dotenv

load_dotenv()
BUCKET = os.getenv("BUCKET")


class Process(Proc):
    """Emulate the recursive output directory being shown correctly in job tree
    """
    input = "var"
    output = "outfile:file:out.txt"
    script = """
    echo {{in.var}} | cloudsh sink {{out.outfile}}
    """
    plugin_opts = {"report": "<h1>Process</h1><p>{{job.out.outfile | read()}}</p>"}


class CloudProcPipeline(Pipen):
    """An example pipeline showing how pipen-board works in cloud."""
    starts = Process
    workdir = f"gs://{BUCKET}/pipen-board/workdir"
    outdir = f"gs://{BUCKET}/pipen-board/outdir"
    data = [[123]]
    plugin_opts = {"diagram_loglevel": "DEBUG"}


if __name__ == "__main__":
    CloudProcPipeline().run()
