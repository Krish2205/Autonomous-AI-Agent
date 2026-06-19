"""
JARVIS — Voice Agent
Backend dummy agent to register voice capabilities with the planner registry.
Actual speech synthesis and speech recognition run free on the client side.
"""

from backend.agents.base import BaseAgent
from backend.logger import get_logger

logger = get_logger("agents.voice")


class VoiceAgent(BaseAgent):
    name = "voice"
    description = (
        "Speak responses aloud to the user. Trigger this agent when the user explicitly "
        "asks to read an answer, speak a message, or talk out loud."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Voice Agent with query: {query[:80]}...")
        # Client handles the text-to-speech rendering, this is a conformation message
        return "🔊 Speaking response out loud."
