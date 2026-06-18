"""
JARVIS — System Usage Analytics
Tracks token usage, latencies, and estimated API pricing costs per query/user.
"""

import os
import time
import sqlite3
import contextvars
from langchain_core.callbacks import BaseCallbackHandler
from backend.config import DATA_DIR, current_user_id
from backend.logger import get_logger

logger = get_logger("core.analytics")

# ── Context Variables ────────────────────────────────────────────────
current_session_id = contextvars.ContextVar("current_session_id", default="default")
current_query_id = contextvars.ContextVar("current_query_id", default="")
current_step_name = contextvars.ContextVar("current_step_name", default="unknown")

# ── Pricing Definitions (per token) ──────────────────────────────────
MODEL_PRICING = {
    "llama-3.3-70b-versatile": {
        "input": 0.59 / 1_000_000,
        "output": 0.79 / 1_000_000
    },
    "default": {
        "input": 0.50 / 1_000_000,
        "output": 0.80 / 1_000_000
    }
}

# ── Database Initialization ──────────────────────────────────────────
ANALYTICS_DB_PATH = os.path.join(DATA_DIR, "analytics.db")

def init_analytics_db():
    """Create the analytics table if it does not exist."""
    try:
        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_id TEXT,
                query TEXT,
                step_name TEXT,
                model_name TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms REAL,
                estimated_cost_usd REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to initialize analytics database: {e}")

# Initialize database schema immediately on import
init_analytics_db()


# ── SQLite Logger Helper ─────────────────────────────────────────────
def log_token_usage(
    user_id: str,
    session_id: str,
    query: str,
    step_name: str,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float
):
    """Calculate the estimated cost and record LLM usage log to SQLite."""
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["default"])
    cost = (prompt_tokens * pricing["input"]) + (completion_tokens * pricing["output"])
    total_tokens = prompt_tokens + completion_tokens

    try:
        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usage_analytics (
                user_id, session_id, query, step_name, model_name,
                prompt_tokens, completion_tokens, total_tokens,
                latency_ms, estimated_cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, session_id, query, step_name, model_name,
            prompt_tokens, completion_tokens, total_tokens,
            latency_ms, cost
        ))
        conn.commit()
        conn.close()
        logger.info(
            f"Logged LLM Usage -> Step: {step_name}, Model: {model_name}, "
            f"Tokens: {total_tokens} (Cost: ${cost:.6f}), Latency: {latency_ms:.1f}ms"
        )
    except Exception as e:
        logger.error(f"Failed to save usage log to database: {e}")


# ── LangChain Callback Interceptor ──────────────────────────────────
class AnalyticsCallbackHandler(BaseCallbackHandler):
    """
    LangChain Callback Handler that tracks token usage and latency.
    Saves logs dynamically using ContextVars metadata.
    """
    def __init__(self):
        super().__init__()
        # Map run_id to start time to calculate latency accurately
        self._runs = {}

    def on_llm_start(self, serialized, prompts, **kwargs):
        run_id = kwargs.get("run_id")
        if run_id:
            self._runs[run_id] = time.time()

    def on_llm_end(self, response, **kwargs):
        run_id = kwargs.get("run_id")
        latency_ms = 0.0
        if run_id and run_id in self._runs:
            latency_ms = (time.time() - self._runs[run_id]) * 1000.0
            del self._runs[run_id]

        # Extract model name and token usage
        model_name = "default"
        prompt_tokens = 0
        completion_tokens = 0

        # Try to inspect the LLM output metadata
        if response.llm_output:
            model_name = response.llm_output.get("model_name", "default")
            token_usage = response.llm_output.get("token_usage")
            if token_usage:
                prompt_tokens = token_usage.get("prompt_tokens", 0)
                completion_tokens = token_usage.get("completion_tokens", 0)

        # Fallback to checking individual generations if llm_output didn't have token counts
        if (prompt_tokens == 0 or completion_tokens == 0) and response.generations:
            for generation in response.generations:
                for gen in generation:
                    message = getattr(gen, "message", None)
                    if message and hasattr(message, "response_metadata"):
                        meta = message.response_metadata
                        token_usage = meta.get("token_usage")
                        if token_usage:
                            prompt_tokens = token_usage.get("prompt_tokens", 0)
                            completion_tokens = token_usage.get("completion_tokens", 0)
                        
                        # Set model name if present in metadata
                        model_name = meta.get("model_name", model_name)
                        break

        # Capture dynamic request context
        user_id = current_user_id.get() or "default"
        session_id = current_session_id.get() or "default"
        query = current_query_id.get() or ""
        step_name = current_step_name.get() or "unknown"

        # If we didn't receive any tokens, default to simple prompt length estimation to prevent empty logs
        if prompt_tokens == 0 and completion_tokens == 0:
            prompt_tokens = 100 # average fallback estimation
            completion_tokens = 200

        log_token_usage(
            user_id=user_id,
            session_id=session_id,
            query=query,
            step_name=step_name,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms
        )
