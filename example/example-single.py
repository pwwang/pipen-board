from pipen import Pipen, Proc


class Process(Proc):
    """Emulate the recursive output directory being shown correctly in job tree
    """
    input = "var"
    output = "outfile:file:out.txt"
    script = """
    echo {{in.var}} > {{out.outfile}}
    """


class SingleProcPipeline(Pipen):
    """An example pipeline showing how pipen-board works."""
    starts = Process
    # plugin_opts = {
    #     "args_flatten": False,
    # }


if __name__ == "__main__":
    SingleProcPipeline().run()
