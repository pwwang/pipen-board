from pipen import Pipen, Proc, ProcGroup
from pipen.utils import mark


@mark(board_config_no_input=True)
class P1(Proc):
    """The P1 process

    See https://google.com

    Input:
        invar: The input variable

    Envs:
        number (choice): The number of whatever
            - 1: One (long tail description ...).
                Some description about one 1.
                Some description about one 2.
                Some description about one 3.
                Some description about one 4.
            - 2: Two (long tail description ...).
                Some description about two
            - 3: Three (long tail description ...).
                Some description about three
        gene_qc (ns): Filter genes. Currently only `min_cells` is supported.
            `gene_qc` is applied after `cell_qc`.
            - min_cells: the minimum number of cells that a gene must be
                expressed in to be kept.
    """
    input = "invar:var"
    output = "outfile:file:{{in.invar}}.out"
    envs = {"number": None, "gene_qc": {"min_cells": 3}}
    script = "echo {{in.invar}} P1 > {{out.outfile}}"


class MyGroup(ProcGroup):
    """Group description
    """

    @ProcGroup.add_proc
    def p2(self):
        @mark(board_config_hidden=True)
        class P2(Proc):
            """The P2 process"""
            requires = P1
            input = "infile:file"
            forks = 2
            output = "outfile:file:{{in.infile | split: '/' | last | split: '.' | first}}.out"
            lang = "bash"
            cache = False
            script = "cat {{in.infile}} > {{out.outfile}}; sleep 3; echo P2 >> {{out.outfile}}"
        return P2

    @ProcGroup.add_proc
    def p3(self):
        class P3(Proc):
            requires = self.p2
            input = "infile:file"
            input_data = lambda ch: list(ch.outfile)[:1]
            output = "outfile:file:{{in.infile | split: '/' | last | split: '.' | first}}.out"
            script = """
                cat {{in.infile}} > {{out.outfile}}
                echo P3 >> {{out.outfile}}
                mkdir -p {{out.outfile | dirname | dirname}}/ja_subdir
                for i in $(seq 1 10); do
                    echo $i >> {{out.outfile | dirname | dirname}}/ja_subdir/$i.txt
                done
                convert -size 200x200 xc:white {{out.outfile | dirname}}/image.png
                # exit 1
            """
            plugin_opts = {
                "report": """
                    <script>import { Image } from '$libs';</script>
                    <h1>P3</h1>
                    <Image src="{{job.outdir}}/image.png" />
                """
            }
        return P3


mg = MyGroup()


class P4(Proc):
    """The P4 process

    Envs:
        abc (required): The `abc` env
            >>> code code code
            >>> more code
        method (ns): The [`method`](https://google.com) to use.
            More description about method.
            >>> code code code code code code code code code code code code code code code code code code code code
            >>> more code
            - a: Use method a
            - b: Use method b
            - c: Use method c
            - <more>: More methods
    """
    requires = mg.p2
    input = "infile:file"
    output = "outfile:file:{{in.infile | split: '/' | last | split: '.' | first}}.out"
    envs = {"abc": None, "method": {"a": 1}}
    script = "cat {{in.infile}} > {{out.outfile}}; echo P4 >> {{out.outfile}};"
    plugin_opts = {"report": "<h1>P4</h1><p>{{envs.abc}}</p>"}


class P5(Proc):
    """Emulate the recursive output directory being shown correctly in job tree
    """
    requires = P4
    input = "infile:file"
    output = "outdir:dir:p5outdir"
    script = """
    outdir="{{out.outdir}}"
    cat {{in.infile}} > $outdir/a0.txt
    mkdir -p $outdir/subdir1
    echo "a1" > $outdir/subdir1/a1.txt
    echo "a11" > $outdir/subdir1/a11.txt
    mkdir -p $outdir/subdir2
    echo "a2" > $outdir/subdir2/a2.txt
    echo "a22" > $outdir/subdir2/a22.txt
    mkdir -p $outdir/subdir3
    echo "a3" > $outdir/subdir3/a3.txt
    echo "a33" > $outdir/subdir3/a33.txt
    mkdir -p $outdir/subdir3/subdir4
    echo "a4" > $outdir/subdir3/subdir4/a4.txt
    echo "a44" > $outdir/subdir3/subdir4/a44.txt
    """


class ExamplePipeline(Pipen):
    """An example pipeline showing how pipen-board works."""
    starts = P1
    data = [["123"] * 10]
    loglevel = "debug"


if __name__ == "__main__":
    ExamplePipeline().run()
