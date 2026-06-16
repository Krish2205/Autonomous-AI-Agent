"""
JARVIS — Agent Registry
The heart of the plugin system. Agents register themselves here,
and the planner auto-discovers available targets.
"""

from backend.logger import get_logger
from backend.agents.base import BaseAgent

logger = get_logger("registry")


class AgentRegistry:
    """
    Central registry for all JARVIS agents.

    Usage:
        registry = AgentRegistry()
        registry.register(SearchAgent())
        registry.register(CodeAgent())

        # Auto-generate planner targets
        targets = registry.get_target_descriptions()

        # Execute a specific agent
        result = registry.run("search", "latest AI news")
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        if not agent.name:
            raise ValueError(f"Agent {agent.__class__.__name__} must have a 'name' attribute.")
        if agent.name in self._agents:
            logger.warning(f"Agent '{agent.name}' is already registered. Overwriting.")
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name} -- {agent.description}")

    def get(self, name: str) -> BaseAgent | None:
        """Get an agent by name."""
        return self._agents.get(name)

    def run(self, name: str, query: str) -> str:
        """Run a specific agent by name."""
        agent = self._agents.get(name)
        if not agent:
            return f"Error: No agent registered with name '{name}'"
        return agent.run(query)

    def list_agents(self) -> list[dict]:
        """Return a list of all registered agents with their metadata."""
        return [
            {"name": a.name, "description": a.description}
            for a in self._agents.values()
        ]

    def get_target_names(self) -> list[str]:
        """Return all registered agent names (for planner target validation)."""
        return list(self._agents.keys())

    def get_target_descriptions(self) -> str:
        """
        Auto-generate the planner prompt section describing available agents.
        This is injected into the planner's system prompt dynamically.
        """
        lines = []
        for name, agent in self._agents.items():
            lines.append(f"- '{name}': {agent.description}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        return name in self._agents
