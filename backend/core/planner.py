"""
JARVIS — Planner
Decomposes user queries into sub-tasks and routes them to agents.
Extracted from router.py. Now dynamically discovers agents from the registry.
"""

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from backend.config import llm
from backend.logger import get_logger

logger = get_logger("core.planner")


from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from backend.config import llm
from backend.logger import get_logger

logger = get_logger("core.planner")


# ── Structured Output Model ──────────────────────────────────────────
class PlannerStep(BaseModel):
    action: Literal["run_agent", "finish"] = Field(
        description="Choose 'run_agent' if there are still actions to perform (like sending/drafting an email, writing code, searching the web) or if you need to gather more information. Choose 'finish' ONLY when all requested tasks/actions are fully completed."
    )
    target: str = Field(
        default="",
        description="The agent name to target. Set to empty string if action is finish."
    )
    query: str = Field(
        default="",
        description="The query or prompt to pass to the target agent. Set to empty string if action is finish."
    )
    thought: str = Field(
        description="Your reasoning for taking this step: what information you have, and what you still need."
    )


class Planner:
    """
    Step-by-step planner for JARVIS. 
    Decides the next action to take based on history and current execution progress.
    """

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the central planner for JARVIS, an autonomous AI operating system.\n"
                "Your job is to solve the user's request step-by-step by deciding which agent to invoke next, or when to finish.\n\n"
                "Available agents you can invoke:\n"
                "{agent_descriptions}\n\n"
                "Guidelines:\n"
                "- Behave like an attentive, precise human assistant. Do ONLY what is explicitly asked in the user request. Do NOT assume, invent, or run unrequested actions or extra agents.\n"
                "- IMAGE GENERATION RULE: Only invoke the 'image_gen' agent if the user's explicit prompt specifically asks to generate, draw, or render an image, thumbnail, graphic, or picture. If the user did NOT explicitly ask for an image, NEVER invoke 'image_gen'.\n"
                "- SCRIPT/MEDIA RULE: If the user specifically asks for video scripts or short scripts, invoke the corresponding media agent to generate them.\n"
                "- If the user asks for a capability that you do not possess, use 'agent_builder' to build a new agent.\n"
                "- Choose 'finish' as soon as all explicitly requested actions are complete."
            ),
            (
                "human",
                "Conversation History:\n{chat_history}\n\n"
                "Original User Request: {query}\n\n"
                "Previous steps taken in this execution loop:\n{scratchpad}\n\n"
                "Decide your next step."
            ),
        ])

        planner_llm = llm.with_structured_output(PlannerStep)
        self.chain = self.prompt | planner_llm

    def plan(self, query: str, agent_descriptions: str, valid_targets: list[str], chat_history: str = "", scratchpad: str = "") -> PlannerStep:
        """Decide the next step to take."""
        logger.info(f"Planning next step for query: {query[:80]}...")
        try:
            step = self.chain.invoke({
                "agent_descriptions": agent_descriptions,
                "query": query,
                "chat_history": chat_history,
                "scratchpad": scratchpad,
            })
            
            # Post-validation of target
            if step.action == "run_agent":
                if not step.target or step.target.strip().lower() not in valid_targets:
                    logger.warning(f"Planner suggested invalid target '{step.target}'. Forcing finish.")
                    step.action = "finish"
                    step.target = ""
                    step.query = ""
            
            logger.info(f"Planner decision: Action={step.action}, Target={step.target}, Thought={step.thought[:60]}...")
            return step
        except Exception as e:
            logger.error(f"Planning step failed: {e}. Defaulting to finish.")
            return PlannerStep(
                action="finish",
                thought=f"Planning failed due to error: {str(e)}",
            )

