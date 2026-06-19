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
from fastapi.responses import StreamingResponse, FileResponse
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


async def get_current_user(
    authorization: str = Header(None),
    token: str = Query(None)
) -> str:
    """Dependency that extracts and verifies authorization tokens, setting ContextVars."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")

    # Extract token from header or query param
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]
    elif token:
        auth_token = token

    # Graceful degradation to Local Developer Mode if Supabase isn't configured
    if not supabase_url or not supabase_anon_key:
        if auth_token:
            current_user_id.set(auth_token)
            return auth_token
        current_user_id.set("default")
        return "default"

    # Enforce token if Supabase is active
    if not auth_token:
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")

    try:
        user_info = verify_supabase_token(auth_token, supabase_url, supabase_anon_key)
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
    confirm_build: bool | None = None


class QueryResponse(BaseModel):
    query: str
    response: str
    agents_used: list[str] | None = None
    needs_builder_confirmation: bool | None = None
    pending_builder_query: str | None = None


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
    allowed_extensions = {"txt", "md", "pdf", "docx", "pptx", "png", "jpg", "jpeg", "mp4", "mkv", "avi", "mov", "webm"}
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


@app.get("/api/download/{filename}")
def download_file(
    filename: str,
    current_user: str = Depends(get_current_user)
):
    """Download or stream a file from the user's documents directory."""
    docs_dir = get_user_documents_dir()
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(docs_dir, safe_filename)
    if not os.path.exists(file_path):
         raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.get("/api/workspace/files")
def list_workspace_files(current_user: str = Depends(get_current_user)):
    """List all documents, audio, and databases in the user's workspace."""
    docs_dir = get_user_documents_dir()
    if not os.path.exists(docs_dir):
        return []
        
    files_list = []
    for f in os.listdir(docs_dir):
        file_path = os.path.join(docs_dir, f)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            ext = os.path.splitext(f)[1].lower()
            
            # Map type category
            if ext in (".mp3", ".wav", ".m4a"):
                file_type = "audio"
            elif ext in (".mp4", ".mov", ".webm", ".mkv", ".avi"):
                file_type = "video"
            elif ext in (".png", ".jpg", ".jpeg", ".gif"):
                file_type = "image"
            elif ext == ".db":
                file_type = "database"
            else:
                file_type = "document"
                
            files_list.append({
                "filename": f,
                "size": stat.st_size,
                "type": file_type,
                "modified": stat.st_mtime
            })
            
    # Sort files: most recently modified first
    files_list.sort(key=lambda x: x["modified"], reverse=True)
    return files_list


@app.delete("/api/workspace/files/{filename}")
def delete_workspace_file(filename: str, current_user: str = Depends(get_current_user)):
    """Delete a workspace file and rebuild the search index."""
    docs_dir = get_user_documents_dir()
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(docs_dir, safe_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        os.remove(file_path)
        logger.info(f"Deleted workspace file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete file {safe_filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
        
    # Rebuild search index
    try:
        analyse_agent = registry.get("analyse")
        if analyse_agent and hasattr(analyse_agent, "rebuild_index"):
            analyse_agent.rebuild_index()
            logger.info("FAISS vector database index successfully updated after file deletion.")
    except Exception as e:
        logger.warning(f"Could not rebuild search index after file deletion: {e}")
        
    return {"status": "success", "message": f"File '{safe_filename}' deleted successfully."}


@app.post("/api/query", response_model=QueryResponse)
def query(request: QueryRequest, current_user: str = Depends(get_current_user)):
    """Send a query to the JARVIS orchestrator under user context."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    logger.info(f"API query received (user: {current_user}, session: {request.session_id}): {request.query[:80]}...")
    try:
        result = orchestrator.run(
            request.query, 
            session_id=request.session_id, 
            confirm_build=request.confirm_build
        )
        return QueryResponse(
            query=request.query,
            response=result["response"],
            agents_used=result["agents_used"],
            needs_builder_confirmation=result.get("needs_builder_confirmation"),
            pending_builder_query=result.get("pending_builder_query"),
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


# ── Webhook / Analytics Schemas and Endpoints ────────────────────────
class WebhookCreate(BaseModel):
    name: str
    url: str
    service: str  # 'slack', 'discord', 'generic'


@app.post("/api/webhooks/incoming/{user_id}/{source}")
async def handle_incoming_webhook(user_id: str, source: str, payload: dict):
    """Handle incoming webhooks (GitHub, Stripe, etc.) for a user, log and notify."""
    from backend.core.webhooks import log_incoming_webhook
    
    # 1. Log the payload to SQLite
    log_incoming_webhook(user_id, source, payload)
    
    # 2. Format custom message based on source
    title = f"Webhook: {source.upper()}"
    message = "Received incoming trigger event."
    level = "info"
    
    if source.lower() == "github":
        repo = payload.get("repository", {}).get("name", "Unknown Repo")
        pusher = payload.get("pusher", {}).get("name", "Someone")
        commits = payload.get("commits", [])
        commit_msg = commits[0].get("message", "No message") if commits else "No commit list"
        message = f"Push to '{repo}' by '{pusher}': \"{commit_msg}\""
        level = "success"
    elif source.lower() == "stripe":
        event_type = payload.get("type", "unknown_event")
        data_obj = payload.get("data", {}).get("object", {})
        amount = data_obj.get("amount", 0) / 100.0 if "amount" in data_obj else None
        currency = data_obj.get("currency", "usd").upper()
        if amount:
            message = f"Stripe '{event_type}': Received {amount:.2f} {currency}"
        else:
            message = f"Stripe '{event_type}' event processed."
        level = "warning" if "fail" in event_type else "success"
    else:
        message = f"Generic event payload: {json.dumps(payload)[:100]}..."
        
    # 3. Broadcast notification to user's SSE queue
    notification_manager.broadcast(
        {"title": title, "message": message, "level": level},
        user_id=user_id
    )
    return {"status": "success", "message": f"Webhook from {source} processed."}


@app.get("/api/webhooks/outgoing")
def get_outgoing_webhooks(current_user: str = Depends(get_current_user)):
    """Retrieve all configured outgoing webhooks for the user."""
    from backend.core.webhooks import list_outgoing_webhooks
    return list_outgoing_webhooks(current_user)


@app.post("/api/webhooks/outgoing")
def create_outgoing_webhook(request: WebhookCreate, current_user: str = Depends(get_current_user)):
    """Configure a new outgoing webhook trigger."""
    from backend.core.webhooks import add_outgoing_webhook
    new_id = add_outgoing_webhook(current_user, request.name, request.url, request.service)
    if new_id < 0:
        raise HTTPException(status_code=500, detail="Failed to create outgoing webhook")
    return {"status": "success", "id": new_id}


@app.delete("/api/webhooks/outgoing/{webhook_id}")
def remove_outgoing_webhook(webhook_id: int, current_user: str = Depends(get_current_user)):
    """Delete an outgoing webhook trigger configuration."""
    from backend.core.webhooks import delete_outgoing_webhook
    ok = delete_outgoing_webhook(current_user, webhook_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete outgoing webhook")
    return {"status": "success"}


@app.get("/api/webhooks/incoming/logs")
def get_incoming_webhook_logs(current_user: str = Depends(get_current_user)):
    """Retrieve history of received incoming webhook logs."""
    from backend.core.webhooks import list_incoming_logs
    return list_incoming_logs(current_user)


@app.get("/api/analytics/summary")
def get_analytics_summary(current_user: str = Depends(get_current_user)):
    """Fetch usage query statistics, token totals, latency averages, and costs."""
    import sqlite3
    from backend.core.analytics import ANALYTICS_DB_PATH
    try:
        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        cursor = conn.cursor()
        
        # General stats
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT query) as total_queries,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                AVG(latency_ms) as avg_latency,
                SUM(estimated_cost_usd) as total_cost
            FROM usage_analytics
            WHERE user_id = ?
        """, (current_user,))
        row = cursor.fetchone()
        
        total_queries = row[0] or 0
        total_prompt_tokens = row[1] or 0
        total_completion_tokens = row[2] or 0
        total_tokens = row[3] or 0
        avg_latency = row[4] or 0.0
        total_cost = row[5] or 0.0
        
        # Grouped by step_name
        cursor.execute("""
            SELECT step_name, SUM(total_tokens) as tokens, SUM(estimated_cost_usd) as cost, AVG(latency_ms) as latency
            FROM usage_analytics
            WHERE user_id = ?
            GROUP BY step_name
        """, (current_user,))
        step_rows = cursor.fetchall()
        by_step = [
            {"step_name": r[0], "total_tokens": r[1] or 0, "estimated_cost_usd": r[2] or 0.0, "avg_latency_ms": r[3] or 0.0}
            for r in step_rows
        ]
        
        # Grouped by model_name
        cursor.execute("""
            SELECT model_name, SUM(total_tokens) as tokens, SUM(estimated_cost_usd) as cost
            FROM usage_analytics
            WHERE user_id = ?
            GROUP BY model_name
        """, (current_user,))
        model_rows = cursor.fetchall()
        by_model = [
            {"model_name": r[0], "total_tokens": r[1] or 0, "estimated_cost_usd": r[2] or 0.0}
            for r in model_rows
        ]
        
        conn.close()
        
        return {
            "total_queries": total_queries,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "avg_latency_ms": avg_latency,
            "total_cost_usd": total_cost,
            "breakdown_by_step": by_step,
            "breakdown_by_model": by_model
        }
    except Exception as e:
        logger.error(f"Failed to fetch analytics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/history")
def get_analytics_history(current_user: str = Depends(get_current_user)):
    """Fetch recent execution step logs for token tracking audit."""
    import sqlite3
    from backend.core.analytics import ANALYTICS_DB_PATH
    try:
        conn = sqlite3.connect(ANALYTICS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, query, step_name, model_name,
                   prompt_tokens, completion_tokens, total_tokens,
                   latency_ms, estimated_cost_usd, timestamp
            FROM usage_analytics
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (current_user,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to fetch analytics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Agent Builder / Management Endpoints ──────────────────────────────
class AgentCodeRequest(BaseModel):
    code: str


class BuildAgentRequest(BaseModel):
    prompt: str


@app.get("/api/agents/code")
def list_agent_files(current_user: str = Depends(get_current_user)):
    """List all agent Python files in backend/agents directory."""
    from backend.config import PROJECT_ROOT
    import os
    agents_dir = os.path.join(PROJECT_ROOT, "backend", "agents")
    if not os.path.exists(agents_dir):
        raise HTTPException(status_code=404, detail="Agents directory not found")
    
    files = os.listdir(agents_dir)
    agent_files = []
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(agents_dir, f)
            is_dynamic = f.endswith("_agent.py") and f != "agent_builder_agent.py"
            agent_files.append({
                "filename": f,
                "name": f[:-9] if f.endswith("_agent.py") else f[:-3],
                "size": os.path.getsize(path),
                "is_dynamic": is_dynamic
            })
    return agent_files


@app.get("/api/agents/code/{filename}")
def get_agent_code(filename: str, current_user: str = Depends(get_current_user)):
    """Get the source code of an agent file."""
    from backend.config import PROJECT_ROOT
    import os
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    if not safe_filename.endswith(".py") or ".." in safe_filename:
        raise HTTPException(status_code=400, detail="Invalid agent file name")
        
    agents_dir = os.path.join(PROJECT_ROOT, "backend", "agents")
    file_path = os.path.join(agents_dir, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Agent file '{safe_filename}' not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        return {"filename": safe_filename, "code": code}
    except Exception as e:
        logger.error(f"Failed to read agent file {safe_filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/code/{filename}")
def save_agent_code(filename: str, request: AgentCodeRequest, current_user: str = Depends(get_current_user)):
    """Save code to an agent file after performing syntax and import validations."""
    from backend.config import PROJECT_ROOT
    import os
    import sys
    import subprocess
    
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    if not safe_filename.endswith(".py") or ".." in safe_filename:
        raise HTTPException(status_code=400, detail="Invalid agent file name")
        
    agents_dir = os.path.join(PROJECT_ROOT, "backend", "agents")
    file_path = os.path.join(agents_dir, safe_filename)
    
    agent_module_name = safe_filename[:-3]
    code = request.code
    
    # 1. Compile Check
    try:
        compile(code, safe_filename, "exec")
    except SyntaxError as se:
        raise HTTPException(
            status_code=400,
            detail=f"Syntax Error: The python code is invalid:\n{str(se)}"
        )
        
    # 2. Write and test validation, revert if fails
    backup_code = None
    file_existed = os.path.exists(file_path)
    if file_existed:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                backup_code = f.read()
        except Exception:
            pass
            
    try:
        os.makedirs(agents_dir, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # 3. Subprocess Import Check
        cmd = [sys.executable, "-c", f"import sys; sys.path.insert(0, {repr(PROJECT_ROOT)}); import backend.agents.{agent_module_name}"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if res.returncode != 0:
            # Revert change
            if file_existed and backup_code is not None:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(backup_code)
            else:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
            raise HTTPException(
                status_code=400,
                detail=f"Import/Execution Error: Code compiles, but fails on execution initialization:\n{res.stderr}"
            )
            
        # 4. Trigger Reload of package registry
        import importlib
        import backend.agents
        importlib.reload(backend.agents)
        registry._agents.clear()
        for AgentClass in backend.agents.ALL_AGENTS:
            registry.register(AgentClass())
            
        return {"status": "success", "message": f"Agent file '{safe_filename}' saved and dynamically registered."}
    except HTTPException:
        raise
    except Exception as e:
        # Revert on other exceptions
        if file_existed and backup_code is not None:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(backup_code)
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save agent code: {str(e)}")


@app.post("/api/agents/build")
def build_custom_agent(request: BuildAgentRequest, current_user: str = Depends(get_current_user)):
    """Invoke the AgentBuilderAgent directly to construct a new agent."""
    try:
        builder = registry.get("agent_builder")
        if not builder:
            raise HTTPException(status_code=404, detail="Agent Builder Agent is not registered.")
            
        result = builder.run(request.prompt)
        
        # Reload package to register the new agent if it succeeded
        if "Success" in result or "created" in result.lower() or "validated" in result.lower():
            import importlib
            import backend.agents
            importlib.reload(backend.agents)
            registry._agents.clear()
            for AgentClass in backend.agents.ALL_AGENTS:
                registry.register(AgentClass())
                
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Dynamic agent build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

