"""
JARVIS — Base Agent
Abstract base class for all agents. Subclass this to create new agents.
"""

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Abstract base class for all JARVIS agents.

    To create a new agent:
        1. Subclass BaseAgent
        2. Set `name` and `description`
        3. Implement `run(query) -> str`
        4. Register it in backend/agents/__init__.py

    Example:
        class MyAgent(BaseAgent):
            name = "my_agent"
            description = "Does something cool"

            def run(self, query: str) -> str:
                return "result"
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, query: str) -> str:
        """Execute the agent's task and return a string result."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Agent:{self.name}>"
