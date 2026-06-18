"""
JARVIS — FastAPI Backend
REST API for the multi-agent system.
"""

import os
import json
import asyncio
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from fastapi.staticfiles import StaticFiles
from backend.config import (
    DOCUMENTS_DIR,
    GENERATED_IMAGES_DIR,
    current_user_id,
    get_user_documents_dir,
    get_user_database_path,
)

from backend.core.registry import AgentRegistry
from backend.core.orchestrator import Orchestrator
from backend.core.memory import ConversationMemory
from backend.core.notifications import notification_manager
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


# ── Auth Helpers & Dependency ───────────────────────────────────────
def verify_supabase_token(token: str, supabase_url: str, supabase_anon_key: str) -> dict:
    """Send JWT token to Supabase /auth/v1/user endpoint to verify its validity."""
    headers = {
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {token}"
    }
    url = f"{supabase_url.rstrip('/')}/auth/v1/user"
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError(f"Invalid token from Supabase: {response.text}")


async def get_current_user(authorization: str = Header(None)) -> str:
    """Dependency that extracts and verifies authorization tokens, setting ContextVars."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")

    # Graceful degradation to Local Developer Mode if Supabase isn't configured
    if not supabase_url or not supabase_anon_key:
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            current_user_id.set(token)
            return token
        current_user_id.set("default")
        return "default"

    # Enforce token if Supabase is active
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]
    try:
        user_info = verify_supabase_token(token, supabase_url, supabase_anon_key)
        user_id = user_info.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
        current_user_id.set(user_id)
        return user_id
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


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
    """Health check endpoint. Tells the client if live Supabase auth is active."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
    auth_provider = "supabase" if (supabase_url and supabase_anon_key) else "local"
    return {
        "status": "ok",
        "agents_registered": len(registry),
        "version": "1.0.0",
        "auth_provider": auth_provider,
    }


@app.get("/api/agents", response_model=list[AgentInfo])
def list_agents():
    """List all registered agents with their capabilities."""
    return registry.list_agents()


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...), 
    session_id: str = "default",
    current_user: str = Depends(get_current_user)
):
    """Upload a file to the user's documents folder and rebuild their FAISS index."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    docs_dir = get_user_documents_dir()
    logger.info(f"Received file upload request: {file.filename} (user: {current_user}, session: {session_id})")

    # Validate file extension
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    allowed_extensions = {"txt", "md", "pdf", "docx", "pptx", "png", "jpg", "jpeg"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type .{ext}. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save file to user's documents folder
    file_path = os.path.join(docs_dir, file.filename)
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
def query(request: QueryRequest, current_user: str = Depends(get_current_user)):
    """Send a query to the JARVIS orchestrator under user context."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info(f"API query received (user: {current_user}, session: {request.session_id}): {request.query[:80]}...")
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
def get_session_history(session_id: str, current_user: str = Depends(get_current_user)):
    """Get the conversation history for a given session under user context."""
    try:
        memory = ConversationMemory(session_id)
        return {"session_id": session_id, "history": memory.get_history()}
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/{session_id}/clear")
def clear_session(session_id: str, current_user: str = Depends(get_current_user)):
    """Clear conversation history for a given session under user context."""
    try:
        memory = ConversationMemory(session_id)
        memory.clear()
        return {"status": "success", "message": f"Session {session_id} history cleared."}
    except Exception as e:
        logger.error(f"Failed to clear session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/workspace/{workspace_id}")
def delete_workspace_data(workspace_id: str, current_user: str = Depends(get_current_user)):
    """Delete all backend data associated with a workspace (documents, FAISS, databases, sessions, generated assets)."""
    # Sanitize workspace_id
    safe_workspace_id = "".join(c for c in workspace_id if c.isalnum() or c in ("-", "_"))
    if not safe_workspace_id:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")
        
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if supabase_url and supabase_anon_key:
        if current_user != workspace_id:
            raise HTTPException(status_code=403, detail="You can only delete your own workspace data")

    import shutil
    from backend.config import DATA_DIR, DOCUMENTS_DIR, FAISS_DIR, GENERATED_IMAGES_DIR
    
    # 1. Documents dir
    user_docs_dir = os.path.join(DOCUMENTS_DIR, safe_workspace_id)
    if os.path.exists(user_docs_dir):
        try:
            shutil.rmtree(user_docs_dir)
            logger.info(f"Deleted documents directory: {user_docs_dir}")
        except Exception as e:
            logger.error(f"Failed to delete documents directory {user_docs_dir}: {e}")

    # 2. FAISS index dir
    user_faiss_dir = os.path.join(FAISS_DIR, safe_workspace_id)
    if os.path.exists(user_faiss_dir):
        try:
            shutil.rmtree(user_faiss_dir)
            logger.info(f"Deleted FAISS directory: {user_faiss_dir}")
        except Exception as e:
            logger.error(f"Failed to delete FAISS directory {user_faiss_dir}: {e}")

    # 3. SQLite database
    db_path = os.path.join(DATA_DIR, "databases", f"jarvis_{safe_workspace_id}.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info(f"Deleted database file: {db_path}")
        except Exception as e:
            logger.error(f"Failed to delete database file {db_path}: {e}")

    # 4. Sessions directory
    user_sessions_dir = os.path.join(DATA_DIR, "sessions", safe_workspace_id)
    if os.path.exists(user_sessions_dir):
        try:
            shutil.rmtree(user_sessions_dir)
            logger.info(f"Deleted sessions directory: {user_sessions_dir}")
        except Exception as e:
            logger.error(f"Failed to delete sessions directory {user_sessions_dir}: {e}")

    # 5. Generated images
    if os.path.exists(GENERATED_IMAGES_DIR):
        try:
            for filename in os.listdir(GENERATED_IMAGES_DIR):
                if filename.startswith(f"{safe_workspace_id}_"):
                    img_path = os.path.join(GENERATED_IMAGES_DIR, filename)
                    if os.path.isfile(img_path):
                        os.remove(img_path)
                        logger.info(f"Deleted image asset: {img_path}")
        except Exception as e:
            logger.error(f"Error deleting user images in {GENERATED_IMAGES_DIR}: {e}")

    return {"status": "success", "message": f"Workspace {workspace_id} data deleted successfully."}



@app.post("/api/agent/{agent_name}")
def run_single_agent(agent_name: str, request: QueryRequest, current_user: str = Depends(get_current_user)):
    """Run a specific agent directly, bypassing the planner, under user context."""
    if agent_name not in registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available: {registry.get_target_names()}",
        )

    logger.info(f"Direct agent call (user: {current_user}): {agent_name} — {request.query[:60]}")
    try:
        result = registry.run(agent_name, request.query)
        return {"agent": agent_name, "query": request.query, "result": result}
    except Exception as e:
        logger.error(f"Agent {agent_name} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/stream")
async def notifications_stream(token: str = Query(None)):
    """SSE endpoint for streaming real-time notifications to the frontend."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")

    user_id = "default"
    if not supabase_url or not supabase_anon_key:
        if token:
            user_id = token
    else:
        if token:
            try:
                user_info = verify_supabase_token(token, supabase_url, supabase_anon_key)
                user_id = user_info.get("id", "default")
            except Exception as e:
                logger.error(f"SSE Auth failed: {e}")
                raise HTTPException(status_code=401, detail="Unauthorized notification stream connection")
        else:
            raise HTTPException(status_code=401, detail="Missing auth token for notifications")

    # Set user context for this stream task
    current_user_id.set(user_id)
    queue = notification_manager.register_queue(user_id)

    async def event_generator():
        try:
            while True:
                # Wait for a notification to be broadcasted
                notification = await queue.get()
                yield f"data: {json.dumps(notification)}\n\n"
        except asyncio.CancelledError:
            # Clean up when connection closes
            pass
        finally:
            notification_manager.unregister_queue(user_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class TestAlertRequest(BaseModel):
    title: str
    message: str
    level: str = "info"


@app.post("/api/notifications/test")
def trigger_test_notification(request: TestAlertRequest, current_user: str = Depends(get_current_user)):
    """Debug endpoint to manually fire notifications for testing."""
    notification_payload = {
        "title": request.title,
        "message": request.message,
        "level": request.level,
    }
    notification_manager.broadcast(notification_payload)
    return {"status": "success", "message": "Test notification broadcasted."}
