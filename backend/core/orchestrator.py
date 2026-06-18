"""
JARVIS — Orchestrator
Main brain that ties together: Registry → Planner → Parallel Executor → Synthesizer.
Refactored from router.py with all hardcoded logic removed.
"""

from concurrent.futures import ThreadPoolExecutor

from backend.core.registry import AgentRegistry
from backend.core.planner import Planner, PlannerStep
from backend.core.synthesizer import Synthesizer
from backend.core.memory import ConversationMemory
from backend.core.analytics import current_session_id, current_query_id, current_step_name
from backend.logger import get_logger

logger = get_logger("core.orchestrator")



class Orchestrator:
    """
    The JARVIS brain. Orchestrates the full pipeline:
        1. Plan — decompose query into sub-tasks
        2. Execute — run agent tasks in parallel
        3. Synthesize — merge results into a final answer

    Usage:
        from backend.core.orchestrator import Orchestrator
        from backend.core.registry import AgentRegistry
        from backend.agents import ALL_AGENTS

        registry = AgentRegistry()
        for AgentClass in ALL_AGENTS:
            registry.register(AgentClass())

        jarvis = Orchestrator(registry)
        response = jarvis.run("What is the latest AI news?")
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.planner = Planner(
            agent_descriptions=registry.get_target_descriptions(),
            valid_targets=registry.get_target_names(),
        )
        self.synthesizer = Synthesizer()

    def _execute_task(self, agent_name: str, query: str) -> str:
        """Execute a single agent task. Handles fallbacks if necessary."""
        logger.info(f"Running [{agent_name.upper()}] agent: '{query[:60]}...'")

        try:
            result = self.registry.run(agent_name, query)

            # Analyse → Search fallback (non-blocking, no input() in threads)
            if agent_name == "analyse" and result == "INFORMATION_NOT_AVAILABLE":
                if "search" in self.registry:
                    logger.info("Analyse found nothing. Falling back to Search agent...")
                    fallback_result = self.registry.run("search", query)
                    return f"[SEARCH RESULT (FALLBACK)]:\n{fallback_result}"
                else:
                    return "Information not available in local documents and no search agent is registered."

            return result

        except Exception as e:
            error_msg = f"Error in {agent_name} agent: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def run(self, query: str, session_id: str = "default_session", max_steps: int = 5) -> dict:
        """
        Main entry point. Takes a user query, runs a sequential planning loop,
        executes agents step-by-step, synthesizes, and returns the result.
        """
        logger.info(f"Processing query: {query} (session: {session_id})")

        # Set usage analytics context parameters
        current_session_id.set(session_id)
        current_query_id.set(query)

        # Load conversation memory
        memory = ConversationMemory(session_id)
        chat_history = memory.get_context_string()

        steps_taken = []
        agents_used = set()

        for step_num in range(1, max_steps + 1):
            # Format scratchpad
            scratchpad_lines = []
            for s in steps_taken:
                scratchpad_lines.append(
                    f"Step {s['step']}:\n"
                    f"- Thought: {s['thought']}\n"
                    f"- Action: Called agent '{s['agent']}' with query '{s['query']}'\n"
                    f"- Result: {s['result']}\n"
                )
            scratchpad = "\n".join(scratchpad_lines) if scratchpad_lines else "No steps taken yet."

            # Step 1: Ask planner what to do next
            current_step_name.set(f"planner_step_{step_num}")
            plan_step = self.planner.plan(query, chat_history=chat_history, scratchpad=scratchpad)

            if plan_step.action == "finish":
                logger.info("Planner decided to finish.")
                break

            # Step 2: Execute agent
            agent_name = plan_step.target
            agent_query = plan_step.query

            if not agent_name or not agent_query:
                logger.warning("Planner action was run_agent but target/query was missing. Finishing.")
                break

            agents_used.add(agent_name)
            current_step_name.set(f"agent:{agent_name}")
            result = self._execute_task(agent_name, agent_query)

            # Record step
            steps_taken.append({
                "step": step_num,
                "thought": plan_step.thought,
                "agent": agent_name,
                "query": agent_query,
                "result": result
            })

        # Synthesize final output based on steps taken
        if steps_taken:
            combined_results_list = []
            for s in steps_taken:
                combined_results_list.append(
                    f"--- Step {s['step']}: Agent '{s['agent']}' ---\n"
                    f"Query: {s['query']}\n"
                    f"Result:\n{s['result']}"
                )
            combined_results = "\n\n".join(combined_results_list)
        else:
            combined_results = "No action steps were required."

        # Step 3: Synthesize (with history context)
        current_step_name.set("synthesizer")
        final_response = self.synthesizer.synthesize(query, combined_results, chat_history=chat_history)

        # Step 4: Save turn to memory
        memory.add_message("user", query)
        memory.add_message("assistant", final_response)

        return {
            "response": final_response,
            "agents_used": list(agents_used)
        }

    def list_agents(self) -> list[dict]:
        """List all registered agents."""
        return self.registry.list_agents()

