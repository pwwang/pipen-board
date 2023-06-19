from .version import __version__
from .cli import PipenCliBoardPlugin
from .plugin import PipenBoardPlugin

# Need the instance to make self work
pipen_board_plugin = PipenBoardPlugin()


def from_pipen_board():
    import sys

    return sys.argv[0] == "@pipen-board"
