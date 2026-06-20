"""
JARVIS — Shared Configuration
Single source of truth for all LLM instances, paths, and settings.
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# ── Load environment variables ──────────────────────────────────────
load_dotenv()

# ── Project Paths ───────────────────────────────────────────────────
# PROJECT_ROOT points to the JARVIS/ directory (one level above backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")
FAISS_DIR = os.path.join(DATA_DIR, "faiss_index")
WORKSPACE_DIR = os.path.join(DATA_DIR, "workspace")
GENERATED_IMAGES_DIR = os.path.join(DATA_DIR, "generated_images")
DATABASE_PATH = os.path.join(DATA_DIR, "jarvis.db")

# Ensure directories exist
for _dir in [DATA_DIR, DOCUMENTS_DIR, FAISS_DIR, WORKSPACE_DIR, GENERATED_IMAGES_DIR]:
    os.makedirs(_dir, exist_ok=True)

# ── Dynamic Multi-User Scoping ──────────────────────────────────────
import contextvars

current_user_id = contextvars.ContextVar("current_user_id", default=None)

def get_user_documents_dir() -> str:
    """Get the documents directory path for the current active user."""
    user_id = current_user_id.get()
    if user_id:
        # Sanitize user_id to prevent directory traversal
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        path = os.path.join(DOCUMENTS_DIR, safe_user_id)
        os.makedirs(path, exist_ok=True)
        return path
    return DOCUMENTS_DIR

def get_user_faiss_dir() -> str:
    """Get the FAISS index directory path for the current active user."""
    user_id = current_user_id.get()
    if user_id:
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        path = os.path.join(FAISS_DIR, safe_user_id)
        os.makedirs(path, exist_ok=True)
        return path
    return FAISS_DIR

def get_user_database_path() -> str:
    """Get the SQLite database file path for the current active user."""
    user_id = current_user_id.get()
    if user_id:
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        db_dir = os.path.join(DATA_DIR, "databases")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, f"jarvis_{safe_user_id}.db")
    return DATABASE_PATH

def get_user_image_filename(filename: str) -> str:
    """Get user-prefixed image filename."""
    user_id = current_user_id.get()
    if user_id:
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        return f"{safe_user_id}_{filename}"
    return filename

def get_user_image_path(filename: str) -> str:
    """Get image file path, ensuring it is user-scoped in name."""
    user_filename = get_user_image_filename(filename)
    return os.path.join(GENERATED_IMAGES_DIR, user_filename)

# ── API Keys ────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# ── LLM Instances (shared across all agents) ───────────────────────
from backend.core.analytics import AnalyticsCallbackHandler
analytics_handler = AnalyticsCallbackHandler()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    groq_api_key=GROQ_API_KEY,
    callbacks=[analytics_handler]
)

vision_llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.1,
    groq_api_key=GROQ_API_KEY,
    callbacks=[analytics_handler]
)

# ── Model Settings ──────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
FAISS_SEARCH_K = 4
RERANK_TOP_N = 3
SEMANTIC_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


# ── Workspace Profile Configuration ──────────────────────────────────
import json
import logging

config_logger = logging.getLogger("config")

DEFAULT_ROLE_AGENTS = {
    "developer": ["code", "devops", "package_manager", "database", "search", "summary", "agent_builder", "visualization", "scraper"],
    "analyst": ["analyse", "visualization", "finance", "database", "search", "summary", "scraper"],
    "designer": ["image_gen", "visualization", "search", "summary", "translation"],
    "manager": ["calendar", "email", "notification", "summary", "search"],
    "guest": ["search", "summary", "translation"]
}

def get_profile_config_path(user_id: str) -> str:
    """Get the profile config JSON path for a user."""
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
    db_dir = os.path.join(DATA_DIR, "databases")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, f"profile_{safe_user_id}.json")

def load_enabled_agents(user_id: str) -> list[str]:
    """Load the list of enabled agent names for the specified user."""
    if not user_id:
        return []
    path = get_profile_config_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("enabled_agents", [])
        except Exception as e:
            config_logger.error(f"Failed to load profile config for {user_id}: {e}")
            
    # Fallback to default roles if it matches a key in DEFAULT_ROLE_AGENTS
    user_lower = user_id.lower()
    for role, agents in DEFAULT_ROLE_AGENTS.items():
        if role in user_lower:
            return agents
            
    # Default fallback for custom or unknown workspaces: basic search and summary agents
    return ["search", "summary"]

def save_enabled_agents(user_id: str, enabled_agents: list[str]) -> None:
    """Save the list of enabled agent names for the specified user."""
    if not user_id:
        return
    path = get_profile_config_path(user_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"enabled_agents": enabled_agents}, f, indent=2)
    except Exception as e:
        config_logger.error(f"Failed to save profile config for {user_id}: {e}")


