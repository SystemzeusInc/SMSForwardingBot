import platform
import logging
import logging.handlers
from typing import Any, Union

# Check platform
WINDOWS_OR_WSL = True if 'Windows' in platform.platform() or 'microsoft' in platform.platform() else False  # pragma: no cover
if not WINDOWS_OR_WSL:  # pragma: no cover
    from cysystemd import journal  # type: ignore

try:
    import coloredlogs  # type: ignore
except ImportError:
    pass


class Logger():
    """Logger.
    """

    # LOGGING_FMT = '[%(asctime)s.%(msecs)-3d][%(levelname)8s] %(message)s'
    LOGGING_FMT = '[%(asctime)s.%(msecs)-3d][%(levelname)8s][%(name)20.20s] %(message)s'
    LOGGING_DATE_FMT = '%Y/%m/%d %H:%M:%S'

    def __init__(self, name: Union[str, None] = None, filename: Union[str, None] = None,
                 stream: bool = True, journal_output: bool = False, level: Union[str, None] = logging.INFO) -> None:
        """Initialize.

        Args:
            name (Union[str, None], optional): Logger name. Defaults to None.
            filename (Union[str, None], optional): Filename to save log. Defaults to None.
            stream (bool, optional): Output to stream. Defaults to True.
            journal_output (bool, optional): Output to journal. Defaults to False.
            level (Union[str, None], optional): Log level. Defaults to logging.INFO.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        self.level = level

        fmt = logging.Formatter(fmt=self.LOGGING_FMT, datefmt=self.LOGGING_DATE_FMT)
        if filename is not None:  # File
            file_handler = logging.handlers.RotatingFileHandler(filename, encoding='utf-8', maxBytes=100000, backupCount=10)
            file_handler.setFormatter(fmt)
            self.logger.addHandler(file_handler)
        if stream:  # Stream
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(fmt)
            self.logger.addHandler(stream_handler)
        if not WINDOWS_OR_WSL and journal_output:  # pragma: no cover
            self.logger.addHandler(journal.JournaldLogHandler())

        # Coloring
        self.coloring()

    def set_level(self, level: int) -> None:
        """Set log level.

        Args:
            level (int): Log level
        """
        self.logger.setLevel(level)

    def debug(self, message: Any) -> None:
        """Debug log.

        Args:
            message (Any): Debug log message
        """
        self.logger.debug(message)

    def info(self, message: Any) -> None:
        """Info log.

        Args:
            message (Any): Info log message
        """
        self.logger.info(message)

    def warn(self, message: Any) -> None:
        """Warning log.

        Args:
            message (Any): Warning log message
        """
        self.logger.warn(message)

    def error(self, message: Any) -> None:
        """Error log.

        Args:
            message (Any): Error log message
        """
        self.logger.error(message)

    def critical(self, message: Any) -> None:
        """Critical log.

        Args:
            message (Any): Critical log message
        """
        self.logger.critical(message)

    # --------------------------------------------------

    def coloring(self,):
        """Coloring logs.
        """
        try:
            LEVEL_STYLES = dict(debug=dict(color='green'),
                                info=dict(),
                                warning=dict(color='yellow'),
                                error=dict(color='red'),
                                critical=dict(color='magenta'))
            FIELD_STYLES = dict(asctime=dict(color=''),
                                levelname=dict(color='black', bold=True))

            coloredlogs.install(logger=self.logger,
                                level=self.level,
                                fmt=self.LOGGING_FMT,
                                datefmt=self.LOGGING_DATE_FMT,
                                level_styles=LEVEL_STYLES,
                                field_styles=FIELD_STYLES)
        except (ImportError, NameError):
            pass
