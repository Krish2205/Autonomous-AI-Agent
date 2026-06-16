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

    def __init__(self, agent_descriptions: str, valid_targets: list[str]):
        self.valid_targets = valid_targets
        self.agent_descriptions = agent_descriptions

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the central planner for JARVIS, an autonomous AI operating system.\n"
                "Your job is to solve the user's request step-by-step by deciding which agent to invoke next, or when to finish.\n\n"
                "Available agents you can invoke:\n"
                "{agent_descriptions}\n\n"
                "Guidelines:\n"
                "- Only select target agents from the available list above.\n"
                "- If the user's request requires performing an action (e.g. sending/drafting an email, writing/updating code or files, searching), you MUST run the corresponding agent using 'run_agent'. Do not choose 'finish' until the action has actually been executed.\n"
                "- Choose 'finish' ONLY when all requested actions are complete and you have all the information required to formulate the final response."
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

    def plan(self, query: str, chat_history: str = "", scratchpad: str = "") -> PlannerStep:
        """Decide the next step to take."""
        logger.info(f"Planning next step for query: {query[:80]}...")
        try:
            step = self.chain.invoke({
                "agent_descriptions": self.agent_descriptions,
                "query": query,
                "chat_history": chat_history,
                "scratchpad": scratchpad,
            })
            
            # Post-validation of target
            if step.action == "run_agent":
                if not step.target or step.target.strip().lower() not in self.valid_targets:
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

