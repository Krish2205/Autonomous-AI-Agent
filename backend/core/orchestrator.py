"""
JARVIS — Orchestrator
Main brain that ties together: Registry → Planner → Parallel Executor → Synthesizer.
Refactored from router.py with all hardcoded logic removed.
"""

from concurrent.futures import ThreadPoolExecutor

from backend.config import current_user_id, load_enabled_agents
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
        self.planner = Planner()
        self.synthesizer = Synthesizer()

    def _execute_task(self, agent_name: str, query: str) -> str:
        """Execute a single agent task. Handles fallbacks if necessary."""
        user_id = current_user_id.get()
        enabled_agents = load_enabled_agents(user_id) if user_id else self.registry.get_target_names()
        if agent_name not in enabled_agents:
            return f"Error: Agent '{agent_name}' is not enabled in this workspace profile."

        logger.info(f"Running [{agent_name.upper()}] agent: '{query[:60]}...'")

        try:
            result = self.registry.run(agent_name, query)

            # Analyse → Search fallback (non-blocking, no input() in threads)
            if agent_name == "analyse" and result == "INFORMATION_NOT_AVAILABLE":
                if "search" in self.registry and "search" in enabled_agents:
                    logger.info("Analyse found nothing. Falling back to Search agent...")
                    fallback_result = self.registry.run("search", query)
                    return f"[SEARCH RESULT (FALLBACK)]:\n{fallback_result}"
                else:
                    return "Information not available in local documents and no search agent is registered or enabled."

            return result

        except Exception as e:
            error_msg = f"Error in {agent_name} agent: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def run(self, query: str, session_id: str = "default_session", max_steps: int = 5, confirm_build: bool | None = None) -> dict:
        """
        Main entry point. Takes a user query, runs a sequential planning loop,
        executes agents step-by-step, synthesizes, and returns the result.
        """
        logger.info(f"Processing query: {query} (session: {session_id}, confirm_build: {confirm_build})")

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

            # Get enabled agents list
            user_id = current_user_id.get()
            enabled_agents = load_enabled_agents(user_id) if user_id else self.registry.get_target_names()

            # Filter valid targets and create dynamic descriptions
            valid_targets = [name for name in self.registry.get_target_names() if name in enabled_agents]
            
            descriptions_lines = []
            for name in valid_targets:
                agent = self.registry.get(name)
                if agent:
                    descriptions_lines.append(f"- '{name}': {agent.description}")
            agent_descriptions = "\n".join(descriptions_lines)

            # Step 1: Ask planner what to do next
            current_step_name.set(f"planner_step_{step_num}")
            plan_step = self.planner.plan(
                query=query, 
                agent_descriptions=agent_descriptions,
                valid_targets=valid_targets,
                chat_history=chat_history, 
                scratchpad=scratchpad
            )

            if plan_step.action == "finish":
                logger.info("Planner decided to finish.")
                break

            # Step 2: Execute agent
            agent_name = plan_step.target
            agent_query = plan_step.query

            if not agent_name or not agent_query:
                logger.warning("Planner action was run_agent but target/query was missing. Finishing.")
                break

            # Intercept agent_builder to check for confirmation
            if agent_name == "agent_builder":
                if confirm_build is None:
                    logger.info("Builder Agent execution detected. Pausing for user confirmation.")
                    # Return immediate confirmation request response
                    return {
                        "response": f"I need to create a new custom agent with capabilities: **{agent_query}**. Since this is a new agent, it will take about 15-30 seconds to compile, import, and test. Would you like to continue or abort?",
                        "agents_used": list(agents_used),
                        "needs_builder_confirmation": True,
                        "pending_builder_query": agent_query
                    }
                elif confirm_build is False:
                    logger.info("User aborted Builder Agent execution.")
                    return {
                        "response": "Agent creation was aborted by the user.",
                        "agents_used": list(agents_used),
                        "needs_builder_confirmation": False
                    }
                else:
                    logger.info("User confirmed Builder Agent execution. Proceeding...")

            agents_used.add(agent_name)
            current_step_name.set(f"agent:{agent_name}")
            result = self._execute_task(agent_name, agent_query)

            # Zero-Touch dynamically reload registry if agent_builder was used
            if agent_name == "agent_builder":
                logger.info("Agent Builder ran. Scanning for new agents to register...")
                self.registry.scan_and_register_agents()

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

