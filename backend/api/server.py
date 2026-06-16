"""
JARVIS — FastAPI Backend
REST API for the multi-agent system.
"""

import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastapi.staticfiles import StaticFiles
from backend.config import DOCUMENTS_DIR, GENERATED_IMAGES_DIR

from backend.core.registry import AgentRegistry
from backend.core.orchestrator import Orchestrator
from backend.core.memory import ConversationMemory
from backend.agents import ALL_AGENTS
from backend.logger import get_logger

logger = get_logger("api")

# ── App Setup ───────────────────────────────────────────────────────
app = FastAPI(
    title="JARVIS API",
    description="Autonomous AI Operating System — Multi-Agent Orchestrator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory=GENERATED_IMAGES_DIR), name="images")

# ── Initialize on startup ──────────────────────────────────────────
registry = AgentRegistry()
for AgentClass in ALL_AGENTS:
    registry.register(AgentClass())

orchestrator = Orchestrator(registry)
logger.info(f"JARVIS API initialized with {len(registry)} agents.")


# ── Request/Response Models ─────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"


class QueryResponse(BaseModel):
    query: str
    response: str
    agents_used: list[str] | None = None


class AgentInfo(BaseModel):
    name: str
    description: str


# ── Routes ──────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agents_registered": len(registry),
        "version": "1.0.0",
    }


@app.get("/api/agents", response_model=list[AgentInfo])
def list_agents():
    """List all registered agents with their capabilities."""
    return registry.list_agents()


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), session_id: str = "default"):
    """Upload a file to the documents folder and rebuild the FAISS index."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    logger.info(f"Received file upload request: {file.filename} (session: {session_id})")

    # Validate file extension
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    allowed_extensions = {"txt", "md", "pdf", "docx", "pptx", "png", "jpg", "jpeg"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type .{ext}. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save file to DOCUMENTS_DIR
    file_path = os.path.join(DOCUMENTS_DIR, file.filename)
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"File saved to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Add file upload notification to session memory
    try:
        memory = ConversationMemory(session_id)
        memory.add_message("assistant", f"📁 File Uploaded Successfully: {file.filename}")
    except Exception as e:
        logger.warning(f"Could not record file upload to session memory: {e}")

    # Rebuild index on the analyse agent
    try:
        analyse_agent = registry.get("analyse")
        if analyse_agent and hasattr(analyse_agent, "rebuild_index"):
            analyse_agent.rebuild_index()
            logger.info("FAISS vector database index successfully updated.")
        else:
            logger.warning("Analyse agent not found or does not support rebuild_index.")
    except Exception as e:
        logger.error(f"Failed to rebuild vector index: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"File uploaded, but failed to update search index: {str(e)}"
        )

    return {
        "status": "success",
        "filename": file.filename,
        "message": f"File '{file.filename}' uploaded and indexed successfully."
    }


@app.post("/api/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """Send a query to the JARVIS orchestrator."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info(f"API query received (session: {request.session_id}): {request.query[:80]}...")
    try:
        result = orchestrator.run(request.query, session_id=request.session_id)
        return QueryResponse(
            query=request.query,
            response=result["response"],
            agents_used=result["agents_used"],
        )
    except Exception as e:
        logger.error(f"API query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}/history")
def get_session_history(session_id: str):
    """Get the conversation history for a given session."""
    try:
        memory = ConversationMemory(session_id)
        return {"session_id": session_id, "history": memory.get_history()}
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/{session_id}/clear")
def clear_session(session_id: str):
    """Clear conversation history for a given session."""
    try:
        memory = ConversationMemory(session_id)
        memory.clear()
        return {"status": "success", "message": f"Session {session_id} history cleared."}
    except Exception as e:
        logger.error(f"Failed to clear session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agent/{agent_name}")
def run_single_agent(agent_name: str, request: QueryRequest):
    """Run a specific agent directly, bypassing the planner."""
    if agent_name not in registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available: {registry.get_target_names()}",
        )

    logger.info(f"Direct agent call: {agent_name} — {request.query[:60]}")
    try:
        result = registry.run(agent_name, request.query)
        return {"agent": agent_name, "query": request.query, "result": result}
    except Exception as e:
        logger.error(f"Agent {agent_name} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
