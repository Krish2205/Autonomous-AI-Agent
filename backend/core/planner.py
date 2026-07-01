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
                "Workspace Rules & Profile directives:\n"
                "{workspace_rules}\n\n"
                "Available agents you can invoke:\n"
                "{agent_descriptions}\n\n"
                "Guidelines:\n"
                "- Behave like an attentive, precise human assistant. Do ONLY what is explicitly asked in the user request. Do NOT assume, invent, or run unrequested actions or extra agents.\n"
                "- TEXT/CODE REQUEST RULE: If the user is asking for code, a query, a command, a script, or an explanation (e.g., 'give me code to pull my repo', 'write a SQL query to...', 'how do I check...'), do NOT try to actually execute or perform the action on the system, and do NOT build a custom agent. Simply route the request to the 'code' agent (or another text agent) to generate and return the code/text directly, and then 'finish'.\n"
                "- ACTION-ORIENTED EXECUTION RULE: When the user asks to create, build, set, or generate an action item (e.g. 'create a sheet for Class 2 sections A-F', 'set a meeting', 'draft lesson plan'), DO NOT call 'search' or return tutorial instructions! You MUST directly invoke the specific execution agent (e.g. 'sheets', 'calendar', 'ncert_lesson_architect') to execute the creation task immediately.\n"
                "- IMAGE GENERATION RULE: Only invoke the 'image_gen' agent if the user's explicit prompt specifically asks to generate, draw, or render an image, thumbnail, graphic, or picture. If the user did NOT explicitly ask for an image, NEVER invoke 'image_gen'.\n"
                "- SCRIPT/MEDIA RULE: If the user specifically asks for video scripts or short scripts, invoke the corresponding media agent to generate them.\n"
                "- If the user asks for a capability that you do not possess, use 'agent_builder' to build a new agent.\n"
                "- SELF-CORRECTION & ERROR RECOVERY MANDATE: If a previous step failed or returned an error (as shown in the previous steps scratchpad), analyze the error reason, refine the task query, and invoke either the same agent with corrected input or a different agent to resolve the issue. Do NOT repeat the exact same failing query twice.\n"
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

    def plan(self, query: str, agent_descriptions: str, valid_targets: list[str], chat_history: str = "", scratchpad: str = "", workspace_rules: str = "") -> PlannerStep:
        """Decide the next step to take."""
        logger.info(f"Planning next step for query: {query[:80]}...")

        # Deterministic Direct Execution Override for Sheet / Calendar / Lesson creation tasks
        q_lower = query.lower()
        if not scratchpad or scratchpad == "No steps taken yet.":
            if any(k in q_lower for k in ["paper check", "check paper", "grade paper", "evaluat", "rubric", "quiz", "fun activity"]):
                if "document_exam_scanner" in valid_targets:
                    logger.info("Deterministic override: Routing paper checking / quiz query directly to 'document_exam_scanner'.")
                    return PlannerStep(
                        action="run_agent",
                        target="document_exam_scanner",
                        query=query,
                        thought="Directly executing paper checking and quiz generation via 'document_exam_scanner'."
                    )
            elif any(k in q_lower for k in ["diagram", "illustration", "flowchart", "blackboard art"]):
                target_agent = "image_gen" if "image_gen" in valid_targets else "visualization"
                if target_agent in valid_targets:
                    logger.info(f"Deterministic override: Routing diagram query directly to '{target_agent}'.")
                    return PlannerStep(
                        action="run_agent",
                        target=target_agent,
                        query=query,
                        thought=f"Directly executing diagram creation via '{target_agent}' tool."
                    )
            elif any(k in q_lower for k in ["lecture", "lesson", "curriculum", "syllabus", "unit plan", "speech"]):
                if "ncert_lesson_architect" in valid_targets:
                    logger.info("Deterministic override: Routing lesson plan query directly to 'ncert_lesson_architect'.")
                    return PlannerStep(
                        action="run_agent",
                        target="ncert_lesson_architect",
                        query=query,
                        thought="Directly executing multi-day curriculum & lesson planning via 'ncert_lesson_architect'."
                    )
            elif any(k in q_lower for k in ["sheet", "spreadsheet", "gradebook", "mark-sheet", "marksheet", "attendance", "progress"]):
                target_agent = "sheets_gradebook_agent" if "sheets_gradebook_agent" in valid_targets else "sheets"
                if target_agent in valid_targets:
                    logger.info(f"Deterministic override: Routing sheet creation query directly to '{target_agent}'.")
                    return PlannerStep(
                        action="run_agent",
                        target=target_agent,
                        query=query,
                        thought=f"Directly executing sheet creation via '{target_agent}' tool."
                    )
            elif ("meeting" in q_lower or "schedule" in q_lower or "calendar" in q_lower or "event" in q_lower) and "calendar" in valid_targets:
                logger.info("Deterministic override: Routing calendar query directly to 'calendar'.")
                return PlannerStep(
                    action="run_agent",
                    target="calendar",
                    query=query,
                    thought="Directly executing calendar scheduling via 'calendar' tool."
                )

        try:
            # Fallback default rules if empty
            if not workspace_rules:
                workspace_rules = "No specific workspace rules defined."
                
            step = self.chain.invoke({
                "agent_descriptions": agent_descriptions,
                "query": query,
                "chat_history": chat_history,
                "scratchpad": scratchpad,
                "workspace_rules": workspace_rules
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

