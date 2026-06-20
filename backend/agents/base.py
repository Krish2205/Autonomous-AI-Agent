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

    def get_llm(self, default_model: str = "llama-3.3-70b-versatile", default_temp: float = 0.3):
        """Get the ChatGroq LLM instance for this agent based on current user configuration."""
        from backend.config import current_user_id, load_profile_config, GROQ_API_KEY, analytics_handler
        from langchain_groq import ChatGroq
        
        user_id = current_user_id.get()
        if user_id:
            config = load_profile_config(user_id)
            agent_cfg = config.get("agent_configs", {}).get(self.name, {})
            model = agent_cfg.get("model", default_model)
            temp = agent_cfg.get("temperature", default_temp)
        else:
            model = default_model
            temp = default_temp
            
        return ChatGroq(
            model=model,
            temperature=float(temp),
            groq_api_key=GROQ_API_KEY,
            callbacks=[analytics_handler]
        )

    def get_system_prompt(self, default_prompt: str) -> str:
        """Get the custom system prompt for this agent based on current user configuration."""
        from backend.config import current_user_id, load_profile_config
        user_id = current_user_id.get()
        if user_id:
            config = load_profile_config(user_id)
            return config.get("agent_configs", {}).get(self.name, {}).get("system_prompt", default_prompt)
        return default_prompt

    def __repr__(self) -> str:
        return f"<Agent:{self.name}>"
