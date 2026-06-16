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

# ── API Keys ────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

# ── LLM Instances (shared across all agents) ───────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    groq_api_key=GROQ_API_KEY,
)

vision_llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.1,
    groq_api_key=GROQ_API_KEY,
)

# ── Model Settings ──────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
FAISS_SEARCH_K = 4
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
