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
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, query: str) -> str:
        """Execute the agent's task and return a string result."""
        raise NotImplementedError

    def get_llm(self, default_model: str = None, default_temp: float = 0.1):
        """
        Get the LLM for this agent.

        Priority order:
          1. Per-agent model override from user profile config (agent_configs[name].model)
          2. HuggingFace Qwen3-32B-Instruct (when HF token is set)
          3. Groq llama-3.3-70b-versatile (fallback when HF token is missing)
        """
        from backend.config import (
            current_user_id, load_profile_config,
            HF_TOKEN_AVAILABLE, HF_PLANNER_MODEL, HF_BASE_URL,
            HUGGINGFACE_API_TOKEN, GROQ_API_KEY, analytics_handler,
        )

        user_id = current_user_id.get()
        model_override = None
        temp_override = None

        if user_id:
            config = load_profile_config(user_id)
            agent_cfg = config.get("agent_configs", {}).get(self.name, {})
            model_override = agent_cfg.get("model")
            temp_override = agent_cfg.get("temperature")

        final_temp = float(temp_override) if temp_override is not None else default_temp

        # If there's a per-agent model override, respect it
        if model_override:
            if HF_TOKEN_AVAILABLE:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model_override,
                    openai_api_base=HF_BASE_URL,
                    openai_api_key=HUGGINGFACE_API_TOKEN,
                    temperature=final_temp,
                    max_tokens=4096,
                    callbacks=[analytics_handler],
                )
            else:
                from langchain_groq import ChatGroq
                return ChatGroq(
                    model=model_override,
                    temperature=final_temp,
                    groq_api_key=GROQ_API_KEY,
                    callbacks=[analytics_handler],
                )

        # Return the global llm instance (already correctly set for HF or Groq)
        from backend.config import llm
        return llm

    def get_code_llm(self, default_temp: float = 0.05):
        """
        Get the dedicated code-generation LLM.
        Uses Qwen3-Coder-480B-A35B-Instruct via HuggingFace when available,
        falls back to the standard llm.
        """
        from backend.config import code_llm
        return code_llm

    def get_vision_llm(self, default_temp: float = 0.1):
        """
        Get the vision / multimodal LLM.
        Uses Qwen2.5-VL-72B-Instruct via HuggingFace when available.
        """
        from backend.config import vision_llm
        return vision_llm

    def get_system_prompt(self, default_prompt: str = "") -> str:
        """Get the system prompt for this agent, resolved dynamically based on active profile."""
        from backend.config import current_user_id, load_profile_config
        from backend.agent_prompts import get_agent_prompt

        user_id = current_user_id.get() or "developer"
        config = load_profile_config(user_id)
        override_prompt = config.get("agent_configs", {}).get(self.name, {}).get("system_prompt")

        if override_prompt:
            custom_prompt = override_prompt
        else:
            custom_prompt = get_agent_prompt(user_id, self.name, default_prompt)

        try:
            from backend.core.orchestrator import get_expertise
            expertise_prompt = get_expertise(self.name)
        except Exception:
            expertise_prompt = ""

        if expertise_prompt:
            return f"{expertise_prompt}\n\n{custom_prompt}"
        return custom_prompt

    def __repr__(self) -> str:
        return f"<Agent:{self.name}>"
