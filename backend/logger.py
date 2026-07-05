import os
import json
import logging
import sys
from datetime import datetime


# ── LangSmith Tracing Automatic Integration ─────────────────────────
if os.environ.get("LANGCHAIN_TRACING_V2") == "true" or os.environ.get("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    # Ensure standard tracer names/projects are configured if not explicitly set
    if not os.environ.get("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = "JARVIS-DevOps-Agents"
    logging.getLogger("config").info(f"🚀 LangSmith Tracing enabled. Project: {os.environ.get('LANGCHAIN_PROJECT')}")


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


class JSONFormatter(logging.Formatter):
    """Custom formatter returning structured JSON payloads for logs aggregation."""
    def format(self, record):
        # Extract request context if propagated inside threads
        from backend.config import current_user_id
        from backend.core.analytics import current_session_id, current_query_id, current_step_name
        
        user_id = current_user_id.get() if current_user_id else None
        session_id = current_session_id.get() if current_session_id else None
        query_id = current_query_id.get() if current_query_id else None
        step_name = current_step_name.get() if current_step_name else None

        log_payload = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "context": {
                "user_id": user_id,
                "session_id": session_id,
                "query_id": query_id,
                "step_name": step_name
            }
        }
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a color-coded logger for a module that outputs colored logs to stdout
    and structured JSON logs to data/jarvis_app.json.

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
        
        # Structured JSON File Handler
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.abspath(os.path.join(current_dir, "..", "data"))
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "jarvis_app.json")
            
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        except Exception:
            pass
            
        logger.propagate = False

    return logger
