from pipen import Pipen, Proc, ProcGroup
from pipen.utils import mark


@mark(board_config_no_input=True)
class P4(Proc):
    """The P1 process

    Input:
        invar: The input variable
    """
    input = "invar:var"
    output = "outfile:file:{{in.invar}}.out"
    script = "echo {{in.invar}} P1 > {{out.outfile}}"


class MyGroup(ProcGroup):

    @ProcGroup.add_proc
    def p2(self):
        @mark(board_config_hidden=True)
        class P3(Proc):
            """The P2 process"""
            input = "infile:file"
            output = "outfile:file:{{in.infile | split: '/' | last | split: '.' | first}}.out"
            lang = "bash"
            cache = False
            script = "cat {{in.infile}} > {{out.outfile}}; sleep 30; echo P2 >> {{out.outfile}}"
        return P3

    @ProcGroup.add_proc
    def p3(self):
        class P1(Proc):
            requires = self.p2
            input = "infile:file"
            output = "outfile:file:{{in.infile | split: '/' | last | split: '.' | first}}.out"
            script = "cat {{in.infile}} > {{out.outfile}}; echo P3 >> {{out.outfile}}; exit 1"
        return P1


mg = MyGroup()
mg.p2.requires = P4


class P2(Proc):
    """The P4 process

    Envs:
        abc: The abc env
        method (ns): The method to use.
            More description about method.
            >>> code code code code code code code code code code code code code code code code code code code code
            >>> more code
            - a: Use method a
            - b: Use method b
            - c: Use method c
    """
    requires = mg.p2
    input = "infile:file"
    output = "outfile:file:{{in.infile | split: '/' | last | split: '.' | first}}.out"
    envs = {"abc": "123", "method": {"a": 1}}
    script = "cat {{in.infile}} > {{out.outfile}}; echo P4 >> {{out.outfile}};"
    # plugin_opts = {"report": "<h1>Report</h1>"}


class ExamplePipeline(Pipen):
    """An example pipeline showing how pipen-cli-config works."""
    starts = P4
    data = [["123"] * 10]
    loglevel = "debug"


if __name__ == "__main__":
    ExamplePipeline().run()
