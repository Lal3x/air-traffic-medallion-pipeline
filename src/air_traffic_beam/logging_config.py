"""Configura logging técnico em arquivo e mensagens resumidas no terminal."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH = Path("data/observability/logs/pipeline.log")


class TerminalLogFilter(logging.Filter):
    """Mantém INFO do projeto e erros do Beam visíveis no terminal."""

    def __init__(self, verbose: bool = False):
        super().__init__()
        self.verbose = verbose

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "air_traffic_beam" or record.name.startswith(
            "air_traffic_beam."
        ):
            return record.levelno >= logging.INFO
        if (
            record.name == "apache_beam"
            or record.name.startswith("apache_beam.")
            or record.name == "PrismRunner"
        ):
            return (
                self.verbose
                and record.levelno >= logging.INFO
                or record.levelno >= logging.ERROR
            )
        return record.levelno >= logging.ERROR


class TerminalFormatter(logging.Formatter):
    """Evita traceback duplicado no terminal após o handler de arquivo processar o evento."""

    def format(self, record: logging.LogRecord) -> str:
        exception_info = record.exc_info
        exception_text = record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            return super().format(record)
        finally:
            record.exc_info = exception_info
            record.exc_text = exception_text


def configure_logging(verbose: bool = False, log_path: str | Path = LOG_PATH) -> Path:
    """Configura handlers rotativos e retorna o caminho do log técnico."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    file_handler = RotatingFileHandler(
        path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    terminal_handler = logging.StreamHandler()
    terminal_handler.setLevel(logging.INFO)
    terminal_handler.addFilter(TerminalLogFilter(verbose=verbose))
    terminal_handler.setFormatter(TerminalFormatter("%(levelname)s %(message)s"))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(terminal_handler)
    logging.getLogger("air_traffic_beam").setLevel(logging.INFO)
    logging.getLogger("apache_beam").setLevel(logging.INFO)
    logging.getLogger("PrismRunner").setLevel(logging.INFO)
    return path
