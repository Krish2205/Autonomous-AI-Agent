"""
JARVIS — Shared Configuration
Single source of truth for all LLM instances, paths, model IDs, and settings.

AI Provider: HuggingFace Inference API (OpenAI-compatible /v1 endpoint)
  - Planner / General Chat : Qwen/Qwen3-32B-Instruct
  - Coding                 : Qwen/Qwen3-Coder-480B-A35B-Instruct
  - Vision / OCR           : Qwen/Qwen2.5-VL-72B-Instruct
  - Embeddings             : BAAI/bge-m3
  - Reranking              : BAAI/bge-reranker-v2-m3
  - Speech-to-Text         : openai/whisper-large-v3
  - Text-to-Speech         : hexgrad/Kokoro-82M
  - Image Generation       : black-forest-labs/FLUX.1-dev
  - RAG Synthesis          : Qwen/Qwen3-32B-Instruct (same as planner)

Fallback: Groq (llama-3.3-70b-versatile) when HF token is not set.
"""

import os
from dotenv import load_dotenv

# ── Load environment variables ───────────────────────────────────────
load_dotenv()

# ── Project Paths ────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")
FAISS_DIR = os.path.join(DATA_DIR, "faiss_index")
WORKSPACE_DIR = os.path.join(DATA_DIR, "workspace")
GENERATED_IMAGES_DIR = os.path.join(DATA_DIR, "generated_images")
DATABASE_PATH = os.path.join(DATA_DIR, "jarvis.db")

for _dir in [DATA_DIR, DOCUMENTS_DIR, FAISS_DIR, WORKSPACE_DIR, GENERATED_IMAGES_DIR]:
    os.makedirs(_dir, exist_ok=True)

# ── Dynamic Multi-User Scoping ────────────────────────────────────────
import contextvars

current_user_id = contextvars.ContextVar("current_user_id", default=None)


def get_user_documents_dir() -> str:
    user_id = current_user_id.get()
    if user_id:
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        path = os.path.join(DOCUMENTS_DIR, safe_user_id)
        os.makedirs(path, exist_ok=True)
        return path
    return DOCUMENTS_DIR


def get_user_faiss_dir() -> str:
    user_id = current_user_id.get()
    if user_id:
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        path = os.path.join(FAISS_DIR, safe_user_id)
        os.makedirs(path, exist_ok=True)
        return path
    return FAISS_DIR


def get_user_database_path() -> str:
    user_id = current_user_id.get()
    if user_id:
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        db_dir = os.path.join(DATA_DIR, "databases")
        os.makedirs(db_dir, exist_ok=True)
        return os.path.join(db_dir, f"jarvis_{safe_user_id}.db")
    return DATABASE_PATH


def get_user_image_filename(filename: str) -> str:
    user_id = current_user_id.get()
    if user_id:
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        return f"{safe_user_id}_{filename}"
    return filename


def get_user_image_path(filename: str) -> str:
    user_filename = get_user_image_filename(filename)
    return os.path.join(GENERATED_IMAGES_DIR, user_filename)


# ── API Keys ──────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "")
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")

# Check if HuggingFace token is valid (not a placeholder)
HF_TOKEN_AVAILABLE = bool(
    HUGGINGFACE_API_TOKEN
    and HUGGINGFACE_API_TOKEN not in ("hf_your_token_here", "")
)

# ── HuggingFace Model IDs ─────────────────────────────────────────────
HF_BASE_URL = "https://api-inference.huggingface.co/v1"
HF_INFERENCE_URL = "https://api-inference.huggingface.co/models"

# Chat / Reasoning
HF_PLANNER_MODEL = "Qwen/Qwen3-32B-Instruct"
HF_CODER_MODEL   = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
HF_VISION_MODEL  = "Qwen/Qwen2.5-VL-72B-Instruct"

# Retrieval
HF_EMBEDDING_MODEL = "BAAI/bge-m3"
HF_RERANKER_MODEL  = "BAAI/bge-reranker-v2-m3"

# Speech
HF_STT_MODEL = "openai/whisper-large-v3"
HF_TTS_MODEL = "hexgrad/Kokoro-82M"

# Image
HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-dev"

# Vibe-Coding secondary (fast, smaller coder)
VIBE_CODING_MODEL_ID   = "sakmkmk2/Vibe-Coding-Claude-Fable-5"
VIBE_CODING_HF_API_URL = f"{HF_INFERENCE_URL}/{VIBE_CODING_MODEL_ID}"

# ── RAG / Embedding Settings ───────────────────────────────────────────
EMBEDDING_MODEL  = HF_EMBEDDING_MODEL   # BAAI/bge-m3
FAISS_SEARCH_K   = 2
RERANK_TOP_N     = 2
SEMANTIC_WEIGHT  = 0.6
KEYWORD_WEIGHT   = 0.4
CHUNK_SIZE       = 500
CHUNK_OVERLAP    = 75

# ── Analytics Handler ─────────────────────────────────────────────────
from backend.core.analytics import AnalyticsCallbackHandler
analytics_handler = AnalyticsCallbackHandler()

# ── Langfuse Tracing Integration ──────────────────────────────────────
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

langfuse_handler = None
if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    try:
        from langfuse.langchain import CallbackHandler
        langfuse_handler = CallbackHandler(
            public_key=LANGFUSE_PUBLIC_KEY,
        )
        logging.getLogger("config").info("✅ Langfuse Tracing callback initialized successfully.")
    except Exception as e:
        logging.getLogger("config").warning(f"⚠️ Failed to initialize Langfuse callback: {e}")

# ── LLM Caching Setup ──────────────────────────────────────────────────
import logging
import langchain
from langchain_community.cache import SQLiteCache

_config_logger = logging.getLogger("config")

try:
    cache_db_path = os.path.join(DATA_DIR, "databases", "langchain_cache.db")
    os.makedirs(os.path.dirname(cache_db_path), exist_ok=True)
    langchain.llm_cache = SQLiteCache(database_path=cache_db_path)
    _config_logger.info(f"LangChain SQLite cache enabled at: {cache_db_path}")
except Exception as e:
    # Fallback to InMemoryCache if SQLiteCache setup fails
    from langchain_core.caches import InMemoryCache
    langchain.llm_cache = InMemoryCache()
    _config_logger.warning(f"Failed to load SQLiteCache ({e}). Fallback to InMemoryCache.")


# ── LLM Factory ───────────────────────────────────────────────────────
def _make_hf_chat_llm(model_id: str, temperature: float = 0.1, max_tokens: int = 4096):
    """
    Create a LangChain chat LLM using HuggingFace's OpenAI-compatible /v1 endpoint.
    Requires HUGGINGFACE_API_TOKEN to be set.
    """
    from langchain_openai import ChatOpenAI
    callbacks = [analytics_handler]
    if langfuse_handler:
        callbacks.append(langfuse_handler)
    return ChatOpenAI(
        model=model_id,
        openai_api_base=HF_BASE_URL,
        openai_api_key=HUGGINGFACE_API_TOKEN,
        temperature=temperature,
        max_tokens=max_tokens,
        callbacks=callbacks,
    )


def _make_groq_llm(model: str = "llama-3.3-70b-versatile", temperature: float = 0.3):
    """Create a Groq LLM as fallback when HF token is unavailable."""
    from langchain_groq import ChatGroq
    callbacks = [analytics_handler]
    if langfuse_handler:
        callbacks.append(langfuse_handler)
    return ChatGroq(
        model=model,
        temperature=temperature,
        groq_api_key=GROQ_API_KEY,
        callbacks=callbacks,
    )


# ── Primary LLM Instances ─────────────────────────────────────────────
import requests as _requests
import time as _time

def check_hf_token_validity() -> bool:
    """Verifies HUGGINGFACE_API_TOKEN with the Hugging Face API whoami endpoint."""
    if not HUGGINGFACE_API_TOKEN or HUGGINGFACE_API_TOKEN in ("hf_your_token_here", ""):
        return False
    try:
        url = "https://huggingface.co/api/whoami"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
        resp = _requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            user_info = resp.json()
            _config_logger.info(f"✅ HUGGINGFACE_API_TOKEN validated. User: {user_info.get('name', 'unknown')} ({user_info.get('type', 'user')})")
            return True
        else:
            _config_logger.warning(f"❌ HUGGINGFACE_API_TOKEN validation failed: API returned status {resp.status_code}")
            return False
    except Exception as e:
        _config_logger.warning(f"⚠️ Could not validate HUGGINGFACE_API_TOKEN (network check failed): {e}")
        # Default to True if network is down but token is populated so that we don't break offline fallbacks
        return True

# Run health check at startup
HF_TOKEN_VALID = HF_TOKEN_AVAILABLE and check_hf_token_validity()

if HF_TOKEN_VALID:
    _config_logger.info(f"✅ Using HuggingFace models as primary AI provider.")

    # General planner / chat / RAG synthesis
    llm = _make_hf_chat_llm(HF_PLANNER_MODEL, temperature=0.1, max_tokens=4096)

    # Dedicated coding LLM (Qwen3-Coder 480B MoE)
    code_llm = _make_hf_chat_llm(HF_CODER_MODEL, temperature=0.05, max_tokens=8192)

    # Vision / multimodal LLM
    vision_llm = _make_hf_chat_llm(HF_VISION_MODEL, temperature=0.1, max_tokens=4096)

    AI_PROVIDER = "huggingface"
else:
    _config_logger.warning(
        "⚠️ Using Groq Fallback AI Provider. "
        "Set a valid HUGGINGFACE_API_TOKEN in .env to enable HuggingFace models."
    )
    # Fallback: Groq for all three roles
    llm        = _make_groq_llm("llama-3.3-70b-versatile", 0.3)
    code_llm   = _make_groq_llm("llama-3.3-70b-versatile", 0.1)
    vision_llm = _make_groq_llm("meta-llama/llama-4-scout-17b-16e-instruct", 0.1)

    AI_PROVIDER = "groq_fallback"

_config_logger.info(f"AI Provider: {AI_PROVIDER}")


# ── HuggingFace Direct API Helpers ────────────────────────────────────
def hf_inference_post(model_id: str, payload: dict, timeout: int = 120, retries: int = 3) -> dict | None:
    """
    Generic POST to the HuggingFace Inference API with exponential backoff on 503 errors.
    Returns parsed JSON response or None on error.
    """
    if not HF_TOKEN_VALID:
        _config_logger.warning(f"[HF API] Valid token not set — skipping call to {model_id}")
        return None

    # Push progress update for model start
    from backend.core.analytics import current_stream_queue, current_step_name
    stream_q = current_stream_queue.get()
    step_name = current_step_name.get()
    if stream_q:
        try:
            stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Calling HuggingFace model {model_id}..."})
        except Exception:
            pass

    url = f"{HF_INFERENCE_URL}/{model_id}"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Request wait_for_model to force HF to load the model on its end if cold
    payload_to_send = payload.copy() if payload else {}
    if "options" not in payload_to_send:
        payload_to_send["options"] = {}
    payload_to_send["options"]["wait_for_model"] = True

    delay = 2
    for attempt in range(1, retries + 1):
        try:
            resp = _requests.post(url, json=payload_to_send, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                if stream_q:
                    try:
                        stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Model {model_id} execution completed successfully."})
                    except Exception:
                        pass
                return resp.json()
            elif resp.status_code == 503:
                _config_logger.warning(f"[HF API] {model_id} is loading (503). Attempt {attempt}/{retries}. Retrying in {delay}s...")
                if stream_q:
                    try:
                        stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Model {model_id} is cold-starting. Retrying in {delay}s..."})
                    except Exception:
                        pass
                _time.sleep(delay)
                delay *= 2
            else:
                _config_logger.error(f"[HF API] {model_id} error {resp.status_code}: {resp.text[:200]}")
                if stream_q:
                    try:
                        stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Model {model_id} returned status {resp.status_code}."})
                    except Exception:
                        pass
                return None
        except Exception as e:
            _config_logger.error(f"[HF API] Request to {model_id} failed (attempt {attempt}/{retries}): {e}")
            if attempt == retries:
                return None
            _time.sleep(delay)
            delay *= 2
    return None


def hf_inference_post_binary(model_id: str, payload: dict, timeout: int = 120, retries: int = 3) -> bytes | None:
    """POST to HF Inference API expecting binary response (images, audio) with exponential backoff on 503."""
    if not HF_TOKEN_VALID:
        return None

    from backend.core.analytics import current_stream_queue, current_step_name
    stream_q = current_stream_queue.get()
    step_name = current_step_name.get()
    if stream_q:
        try:
            stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Generating binary asset using HF {model_id}..."})
        except Exception:
            pass

    url = f"{HF_INFERENCE_URL}/{model_id}"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload_to_send = payload.copy() if payload else {}
    if "options" not in payload_to_send:
        payload_to_send["options"] = {}
    payload_to_send["options"]["wait_for_model"] = True

    delay = 2
    for attempt in range(1, retries + 1):
        try:
            resp = _requests.post(url, json=payload_to_send, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                if stream_q:
                    try:
                        stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Binary generation from {model_id} completed successfully."})
                    except Exception:
                        pass
                return resp.content
            elif resp.status_code == 503:
                _config_logger.warning(f"[HF API] {model_id} is loading (503). Attempt {attempt}/{retries}. Retrying in {delay}s...")
                if stream_q:
                    try:
                        stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Model {model_id} is cold-starting. Retrying in {delay}s..."})
                    except Exception:
                        pass
                _time.sleep(delay)
                delay *= 2
            else:
                _config_logger.error(f"[HF API] {model_id} binary error {resp.status_code}: {resp.text[:200]}")
                if stream_q:
                    try:
                        stream_q.put({"type": "progress_chunk", "agent": step_name, "message": f"Model {model_id} returned binary status {resp.status_code}."})
                    except Exception:
                        pass
                return None
        except Exception as e:
            _config_logger.error(f"[HF API] Binary request to {model_id} failed (attempt {attempt}/{retries}): {e}")
            if attempt == retries:
                return None
            _time.sleep(delay)
            delay *= 2
    return None



# ── Workspace Profile Configuration ──────────────────────────────────
import json

DEFAULT_ROLE_AGENTS = {
    "developer": ["code", "devops", "package_manager", "database", "search", "summary", "agent_builder", "visualization", "scraper", "dev_team", "sheets", "calendar", "notes"],
    "analyst": ["analyse", "visualization", "finance", "database", "search", "summary", "scraper", "analyst_team", "sheets", "calendar"],
    "designer": ["image_gen", "visualization", "search", "summary", "translation"],
    "manager": ["calendar", "email", "notification", "summary", "search", "ops_team", "sheets", "notes"],
    "guest": ["search", "summary", "translation"],
    "cloud_devops": ["cloud_infra", "github_workflow", "devops", "code", "package_manager", "database", "search", "summary"],
    "financial_analyst": ["market_intelligence", "financial_reporting", "finance", "analyse", "visualization", "database", "search", "summary", "sheets"],
    "cybersec_auditor": ["sec_ops", "compliance", "code", "database", "search", "summary"],
    "healthcare_researcher": ["biomedical_rag", "analyse", "search", "summary", "translation"],
    "creative_marketer": ["marketing_campaign", "multimedia_processor", "image_gen", "visualization", "search", "summary"],
    "legal_ops": ["legal_contract", "talent_ops", "summary", "search", "analyse"],
    "edtech_studio": ["teacher_executive_assistant", "document_exam_scanner", "sheets_gradebook_agent", "sheets", "calendar_scheduler_agent", "calendar", "notes_manager_agent", "notes", "lesson_architect", "exam_generator", "whatsapp_notice_curator", "hinglish_socratic_tutor", "cce_report_card_architect", "search", "summary", "analyse"],
}


def get_profile_config_path(user_id: str) -> str:
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
    db_dir = os.path.join(DATA_DIR, "databases")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, f"profile_{safe_user_id}.json")


def load_profile_config(user_id: str) -> dict:
    if not user_id:
        return {}
    try:
        from backend.core.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT config FROM profile_configs WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row["config"]:
            return json.loads(row["config"])
    except Exception as e:
        _config_logger.error(f"Failed to load profile config for {user_id} from DB: {e}")
    path = get_profile_config_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                save_profile_config(user_id, config_data)
                return config_data
        except Exception as e:
            _config_logger.error(f"Failed to load legacy profile config file: {e}")
    return {}


def save_profile_config(user_id: str, config: dict) -> None:
    if not user_id:
        return
    try:
        from backend.core.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        config_json = json.dumps(config, indent=2)
        cursor.execute("""
        INSERT INTO profile_configs (user_id, config, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            config = excluded.config,
            updated_at = CURRENT_TIMESTAMP
        """, (user_id, config_json))
        conn.commit()
        conn.close()
    except Exception as e:
        _config_logger.error(f"Failed to save profile config for {user_id} to DB: {e}")


def load_enabled_agents(user_id: str) -> list[str]:
    if not user_id:
        user_id = "default"
    try:
        config = load_profile_config(user_id)
        if config and "enabled_agents" in config and config["enabled_agents"]:
            return config["enabled_agents"]
    except Exception as e:
        _config_logger.warning(f"Failed to load enabled agents from user config: {e}")
    if user_id in DEFAULT_ROLE_AGENTS:
        return DEFAULT_ROLE_AGENTS[user_id]
    try:
        from backend.agents import ALL_AGENTS
        names = [a.name for a in ALL_AGENTS if hasattr(a, "name") and a.name]
        if names:
            return list(set(names))
    except Exception as e:
        _config_logger.warning(f"Failed dynamic load of all agents: {e}")
    return ["teacher_executive_assistant", "document_exam_scanner", "sheets_gradebook_agent", "sheets",
            "calendar_scheduler_agent", "calendar", "notes_manager_agent", "notes", "lesson_architect",
            "exam_generator", "whatsapp_notice_curator", "hinglish_socratic_tutor", "cce_report_card_architect",
            "search", "summary", "analyse", "code", "devops", "cloud_infra", "github_workflow"]


def save_enabled_agents(user_id: str, enabled_agents: list[str]) -> None:
    config = load_profile_config(user_id)
    config["enabled_agents"] = enabled_agents
    save_profile_config(user_id, config)


def get_user_integration(provider: str) -> dict:
    user_id = current_user_id.get()
    keys_to_check = [user_id, "edtech_studio", "developer", "default"]
    for k in keys_to_check:
        if k:
            cfg = load_profile_config(k).get("integrations", {}).get(provider, {})
            if cfg.get("connected"):
                return cfg
    return {}
