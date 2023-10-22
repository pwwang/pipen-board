from .version import __version__  # noqa: F401
from .cli import PipenCliBoardPlugin  # noqa: F401
from .plugin import PipenBoardPlugin

# Need the instance to make self work
pipen_board_plugin = PipenBoardPlugin()
