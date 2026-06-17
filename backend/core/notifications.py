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
        self.queues: list[asyncio.Queue] = []

    def register_queue(self) -> asyncio.Queue:
        """Register a new subscriber queue."""
        q = asyncio.Queue()
        self.queues.append(q)
        logger.info(f"Notification subscriber registered. Total subscribers: {len(self.queues)}")
        return q

    def unregister_queue(self, q: asyncio.Queue):
        """Unregister a subscriber queue."""
        if q in self.queues:
            self.queues.remove(q)
            logger.info(f"Notification subscriber disconnected. Total subscribers: {len(self.queues)}")

    def broadcast(self, notification: dict):
        """Send a notification dictionary payload to all registered subscribers."""
        logger.info(f"Broadcasting notification: {notification.get('title', 'No Title')}")
        for q in self.queues:
            try:
                q.put_nowait(notification)
            except Exception as e:
                logger.warning(f"Failed to put notification into queue: {e}")


# Global singleton instance
notification_manager = NotificationManager()
