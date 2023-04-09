from .cli import PipenCliBoardPlugin
from .plugin import PipenBoardPlugin

__version__ = "0.0.0"

PipenBoardPlugin.__version__ = __version__
PipenCliBoardPlugin.__version__ = __version__

# Need the instance to make self work
pipen_board_plugin = PipenBoardPlugin()
