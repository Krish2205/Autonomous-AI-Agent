"""
JARVIS — Structured Logging
Color-coded console output with module names.
"""

import logging
import sys


# ── Color Codes ─────────────────────────────────────────────────────
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors based on log level."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.GRAY,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        timestamp = self.formatTime(record, "%H:%M:%S")

        formatted = (
            f"{Colors.GRAY}{timestamp}{Colors.RESET} "
            f"{color}{record.levelname:<8}{Colors.RESET} "
            f"{Colors.BOLD}{record.name}{Colors.RESET} -> "
            f"{record.getMessage()}"
        )
        return formatted


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a color-coded logger for a module that outputs to stdout and data/jarvis_app.log.

    Usage:
        from backend.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Agent started")
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)
        
        # File Handler
        try:
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.abspath(os.path.join(current_dir, "..", "data"))
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "jarvis_app.log")
            
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s -> %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass
            
        logger.propagate = False

    return logger
