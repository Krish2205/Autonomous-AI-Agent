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
        user_id = current_user_id.get()
        if user_id:
            safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
            self.file_path = os.path.join(DATA_DIR, "sessions", safe_user_id, f"{session_id}.json")
        else:
            self.file_path = os.path.join(DATA_DIR, "sessions", f"{session_id}.json")
            
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
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
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception as e:
                logger.error(f"Failed to remove session file {self.file_path}: {e}")
        logger.info(f"Cleared memory for session: {self.session_id}")

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.messages = json.load(f)
                logger.info(f"Loaded memory for session: {self.session_id}")
            except Exception as e:
                logger.error(f"Failed to load memory for session {self.session_id}: {e}")
                self.messages = []

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save memory for session {self.session_id}: {e}")
