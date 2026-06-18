"""
JARVIS — Webhook I/O Channels
Manages custom outgoing webhooks (Slack, Discord, Generic) and incoming triggers (GitHub, Stripe).
"""

import os
import json
import sqlite3
import threading
import requests
from backend.config import DATA_DIR
from backend.logger import get_logger

logger = get_logger("core.webhooks")

WEBHOOKS_DB_PATH = os.path.join(DATA_DIR, "webhooks.db")

def init_webhooks_db():
    """Create the webhook management tables if they do not exist."""
    try:
        conn = sqlite3.connect(WEBHOOKS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outgoing_webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                name TEXT,
                url TEXT,
                service TEXT, -- 'slack', 'discord', 'generic'
                is_active INTEGER DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incoming_webhook_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                source TEXT, -- 'github', 'stripe', 'generic'
                payload TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to initialize webhooks database: {e}")

# Initialize schema immediately on import
init_webhooks_db()


# ── Webhook CRUD Helper Functions ────────────────────────────────────
def list_outgoing_webhooks(user_id: str) -> list[dict]:
    """Retrieve all outgoing webhooks for a user."""
    try:
        conn = sqlite3.connect(WEBHOOKS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM outgoing_webhooks WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to list outgoing webhooks: {e}")
        return []

def add_outgoing_webhook(user_id: str, name: str, url: str, service: str) -> int:
    """Add a new outgoing webhook URL configuration."""
    try:
        conn = sqlite3.connect(WEBHOOKS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO outgoing_webhooks (user_id, name, url, service)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, url, service.lower()))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return new_id
    except Exception as e:
        logger.error(f"Failed to add outgoing webhook: {e}")
        return -1

def delete_outgoing_webhook(user_id: str, webhook_id: int) -> bool:
    """Remove a configured outgoing webhook configuration."""
    try:
        conn = sqlite3.connect(WEBHOOKS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM outgoing_webhooks WHERE id = ? AND user_id = ?",
            (webhook_id, user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to delete outgoing webhook {webhook_id}: {e}")
        return False


# ── Incoming Logs Helper Functions ───────────────────────────────────
def log_incoming_webhook(user_id: str, source: str, payload: dict):
    """Log an incoming webhook payload to the database for audit history."""
    try:
        conn = sqlite3.connect(WEBHOOKS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO incoming_webhook_logs (user_id, source, payload)
            VALUES (?, ?, ?)
        """, (user_id, source, json.dumps(payload)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log incoming webhook payload: {e}")

def list_incoming_logs(user_id: str, limit: int = 20) -> list[dict]:
    """List recent incoming webhooks logs for a user."""
    try:
        conn = sqlite3.connect(WEBHOOKS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM incoming_webhook_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to retrieve incoming webhook logs: {e}")
        return []


# ── Outgoing Webhook Trigger Dispatcher ──────────────────────────────
def _dispatch_post(url: str, payload: dict, service: str):
    """Internal runner executing HTTP requests with format mapping."""
    try:
        headers = {"Content-Type": "application/json"}
        res = requests.post(url, json=payload, headers=headers, timeout=8)
        logger.info(f"Dispatched outgoing webhook ({service}) -> Status: {res.status_code}")
    except Exception as e:
        logger.error(f"Failed to dispatch outgoing webhook to {url}: {e}")

def trigger_outgoing_webhooks(user_id: str, title: str, message: str, level: str = "info"):
    """
    Spins up background threads to dispatch events to all active
    outgoing webhooks registered for the user.
    """
    webhooks = list_outgoing_webhooks(user_id)
    active_hooks = [w for w in webhooks if w.get("is_active", 1) == 1]
    
    if not active_hooks:
        return

    # Standardize emojis for visual status
    emoji = {"success": "✅", "warning": "⚠️", "error": "🚨", "info": "ℹ️"}.get(level, "🔔")
    formatted_msg = f"{emoji} *{title}*\n{message}"

    for hook in active_hooks:
        url = hook["url"]
        service = hook["service"]
        
        # Format payloads per service API
        if service == "slack":
            payload = {"text": formatted_msg}
        elif service == "discord":
            # Discord uses content block syntax similar to Slack
            payload = {"content": f"**{emoji} {title}**\n{message}"}
        else:
            # Generic JSON structure
            payload = {
                "title": title,
                "message": message,
                "level": level,
                "user_id": user_id
            }

        # Dispatch asynchronously in background thread to avoid blocking main server tasks
        thread = threading.Thread(
            target=_dispatch_post,
            args=(url, payload, service),
            daemon=True
        )
        thread.start()
