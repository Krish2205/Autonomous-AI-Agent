"""
JARVIS — Core Notification Manager
Provides real-time broadcasting of push notifications to active frontend sessions.
"""

import asyncio
import json
from backend.logger import get_logger

logger = get_logger("core.notifications")


class NotificationManager:
    """Manages active notification queues for client SSE (Server-Sent Events) connections."""

    def __init__(self):
        # Map user_id to a list of subscriber queues
        self.queues: dict[str, list[asyncio.Queue]] = {}

    def register_queue(self, user_id: str = "default") -> asyncio.Queue:
        """Register a new subscriber queue for a user."""
        q = asyncio.Queue()
        if user_id not in self.queues:
            self.queues[user_id] = []
        self.queues[user_id].append(q)
        logger.info(f"Notification subscriber registered for user '{user_id}'. Subscriptions count: {len(self.queues[user_id])}")
        return q

    def unregister_queue(self, user_id: str, q: asyncio.Queue):
        """Unregister a subscriber queue for a user."""
        if user_id in self.queues and q in self.queues[user_id]:
            self.queues[user_id].remove(q)
            logger.info(f"Notification subscriber disconnected for user '{user_id}'. Subscriptions remaining: {len(self.queues[user_id])}")
            if not self.queues[user_id]:
                del self.queues[user_id]

    def broadcast(self, notification: dict, user_id: str = None):
        """Send a notification dictionary payload to all registered subscribers for a specific user."""
        if not user_id:
            from backend.config import current_user_id
            user_id = current_user_id.get() or "default"

        logger.info(f"Broadcasting notification to user '{user_id}': {notification.get('title', 'No Title')}")
        target_queues = self.queues.get(user_id, [])
        for q in target_queues:
            try:
                q.put_nowait(notification)
            except Exception as e:
                logger.warning(f"Failed to put notification into user '{user_id}' queue: {e}")


# Global singleton instance
notification_manager = NotificationManager()
