"""
JARVIS — Agent Registry
The heart of the plugin system. Agents register themselves here,
and the planner auto-discovers available targets.
"""

from backend.logger import get_logger
from backend.agents.base import BaseAgent
import os
import sys
import importlib
import pkgutil
import inspect
from backend.config import PROJECT_ROOT

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
        agent.registry = self
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

    def scan_and_register_agents(self) -> None:
        """
        Dynamically scan the backend.agents directory and register any new subclasses of BaseAgent.
        """
        logger.info("Scanning for new agents in backend.agents...")
        agents_dir = os.path.join(PROJECT_ROOT, "backend", "agents")
        
        # We need to ensure we can reload if it's already in sys.modules, but for newly created ones, 
        # importlib.import_module is sufficient.
        for _, module_name, _ in pkgutil.iter_modules([agents_dir]):
            if module_name in ("base", "__init__", "team_base"):
                continue
            try:
                full_module_name = f"backend.agents.{module_name}"
                # If it's already loaded, we might want to reload it, but `pkgutil` finds it.
                # Just import or get the module.
                if full_module_name in sys.modules:
                    module = sys.modules[full_module_name]
                    importlib.reload(module)
                else:
                    module = importlib.import_module(full_module_name)
                    
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseAgent) and obj is not BaseAgent and obj.__module__ == module.__name__:
                        # Instantiate and register if not already registered (or overwrite if changed)
                        agent_instance = obj()
                        if agent_instance.name not in self._agents:
                            self.register(agent_instance)
                            
            except Exception as e:
                logger.error(f"Error scanning/registering module {module_name}: {e}")

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        return name in self._agents
