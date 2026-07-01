"""
JARVIS — Conversation Memory Persistence
Stores chat histories in a structured SQLite table rather than flat JSON files.
"""

import os
import json
from typing import List, Dict
from backend.config import DATA_DIR
from backend.logger import get_logger

logger = get_logger("core.memory")

class ConversationMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        
        # User scoping for multi-user session files
        from backend.config import current_user_id
        self.user_id = current_user_id.get() or "default"
        
        # Check if Supabase is active
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
        supabase_active = bool(supabase_url and supabase_anon_key)
        
        if not supabase_active:
            self.safe_user_id = "local"
        else:
            self.safe_user_id = "".join(c for c in self.user_id if c.isalnum() or c in ("-", "_"))
            
        # Legacy file path for automatic migration
        self.legacy_file_path = os.path.join(DATA_DIR, "sessions", self.safe_user_id, f"{session_id}.json")
        
        self.load()

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.save()

    def get_history(self) -> List[Dict[str, str]]:
        return self.messages

    def get_context_string(self) -> str:
        """Format the history as a string for inclusion in LLM prompts."""
        formatted = []
        for msg in self.messages:
            role = "User" if msg["role"] == "user" else "JARVIS"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    def clear(self):
        self.messages = []
        try:
            from backend.core.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE session_id = ?", (self.session_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to clear session {self.session_id} in DB: {e}")
            
        # Remove legacy file if exists
        if os.path.exists(self.legacy_file_path):
            try:
                os.remove(self.legacy_file_path)
            except Exception:
                pass
                
        logger.info(f"Cleared memory for session: {self.session_id}")

    def load(self):
        try:
            from backend.core.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT messages FROM conversations WHERE session_id = ?", (self.session_id,))
            row = cursor.fetchone()
            conn.close()
            if row and row["messages"]:
                self.messages = json.loads(row["messages"])
                logger.info(f"Loaded memory from DB for session: {self.session_id}")
                return
        except Exception as e:
            logger.error(f"Failed to load memory for session {self.session_id} from DB: {e}")
            
        # Fallback & Migration of legacy JSON file
        if os.path.exists(self.legacy_file_path):
            try:
                with open(self.legacy_file_path, "r", encoding="utf-8") as f:
                    self.messages = json.load(f)
                logger.info(f"Loaded memory from legacy file and migrating for session: {self.session_id}")
                self.save()  # Migrate to SQLite
            except Exception as e:
                logger.error(f"Failed to load/migrate legacy session file {self.legacy_file_path}: {e}")

    def save(self):
        try:
            from backend.core.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            messages_json = json.dumps(self.messages, ensure_ascii=False)
            
            # Simple title generation from the first query
            title = "New Chat"
            if self.messages:
                first_user_msg = next((m["content"] for m in self.messages if m["role"] == "user"), "")
                if first_user_msg:
                    title = first_user_msg[:60] + "..." if len(first_user_msg) > 60 else first_user_msg
            
            cursor.execute("""
            INSERT INTO conversations (session_id, user_id, title, messages, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                messages = excluded.messages,
                title = excluded.title,
                updated_at = CURRENT_TIMESTAMP
            """, (self.session_id, self.user_id, title, messages_json))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save memory for session {self.session_id} to DB: {e}")
