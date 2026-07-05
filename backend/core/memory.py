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
        self.history_summary: str = ""
        
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
        self._compress_if_needed()
        self.save()

    def get_history(self) -> List[Dict[str, str]]:
        return self.messages

    def _compress_if_needed(self):
        """Compresses older turns into a running summary once the message count exceeds the threshold (10 messages)."""
        # We keep the last 10 turns (5 full user-assistant loops)
        threshold = 10
        if len(self.messages) <= threshold:
            return

        # Split into what we keep (recent turns) and what we compress (older turns)
        to_keep = self.messages[-threshold:]
        to_compress = self.messages[:-threshold]

        logger.info(f"Compressing {len(to_compress)} older turns into running conversation summary...")

        # Format older turns for LLM input
        formatted_turns = []
        for msg in to_compress:
            role = "User" if msg["role"] == "user" else "JARVIS"
            formatted_turns.append(f"{role}: {msg['content']}")
        turns_text = "\n".join(formatted_turns)

        # Prompt LLM to update summary
        from backend.config import llm
        from langchain_core.messages import SystemMessage, HumanMessage
        
        system_prompt = (
            "You are the Memory Consolidation module of JARVIS.\n"
            "Your task is to take a running summary of the conversation history so far, combined with a new set of older turns, "
            "and generate a single, highly cohesive, concise paragraph summarizing the entire conversation so far.\n"
            "Focus only on key factual information, goals, user instructions, and accomplished tasks. Avoid conversational filler."
        )
        
        user_prompt = f"Current summary:\n{self.history_summary or 'No summary yet.'}\n\nOlder turns to add to summary:\n{turns_text}"
        
        try:
            resp = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            new_summary = resp.content if hasattr(resp, "content") else str(resp)
            self.history_summary = new_summary.strip()
            self.messages = to_keep
            logger.info("Conversation summary updated successfully.")
        except Exception as e:
            logger.error(f"Failed to compress conversation memory summary: {e}")

    def get_context_string(self) -> str:
        """Format the history as a string including the running summary + the sliding window turns."""
        formatted = []
        if self.history_summary:
            formatted.append(f"[Conversation Summary of older turns]:\n{self.history_summary}\n")
            
        if self.messages:
            formatted.append("[Recent Turns]:")
            for msg in self.messages:
                role = "User" if msg["role"] == "user" else "JARVIS"
                formatted.append(f"{role}: {msg['content']}")
                
        return "\n".join(formatted)

    def clear(self):
        self.messages = []
        self.history_summary = ""
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
            cursor.execute("SELECT messages, history_summary FROM conversations WHERE session_id = ?", (self.session_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                if row["messages"]:
                    self.messages = json.loads(row["messages"])
                if "history_summary" in row.keys() and row["history_summary"]:
                    self.history_summary = row["history_summary"]
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
            INSERT INTO conversations (session_id, user_id, title, messages, history_summary, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                messages = excluded.messages,
                title = excluded.title,
                history_summary = excluded.history_summary,
                updated_at = CURRENT_TIMESTAMP
            """, (self.session_id, self.user_id, title, messages_json, self.history_summary))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save memory for session {self.session_id} to DB: {e}")
