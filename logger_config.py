import sys
from pathlib import Path
from loguru import logger
from datetime import datetime
import os
import pytz

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

def _get_log_filename():
    timestamp = datetime.now(pytz.timezone('America/Mexico_City')).strftime("%Y%m%d_%H%M%S")
    return f"murray_{timestamp}.log"

log_filename = _get_log_filename()


log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


file_format = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

logger.remove()


# Console handler
logger.add(
    sys.stdout,
    format=log_format,
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True,
)


# File handler - one file per execution
logger.add(
    log_dir / log_filename,
    format=file_format,
    level="INFO",
    backtrace=True,
    diagnose=True,
)


def get_logger(name: str = None, context: str = None):
    """
    Get a logger with specific context.

    Args:
        name: Module/function name
        context: Additional context (e.g: 'simulation', 'evaluation')

    Returns:
        Logger configured with context
    """
    if name:
        log = logger.bind(name=name)
    else:
        log = logger

    if context:
        log = log.bind(context=context)

    return log


__all__ = ["logger", "get_logger"]
