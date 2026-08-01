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
import yaml
import os

# Load agent expertise prompts from YAML configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "agent_expertise.yaml")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        AGENT_EXPERTISE = yaml.safe_load(f) or {}
else:
    AGENT_EXPERTISE = {}

def get_expertise(agent_name: str) -> str:
    """Retrieve the expertise system prompt for a given agent name.
    Returns an empty string if no specific prompt is defined.
    """
    return AGENT_EXPERTISE.get(agent_name, "")
from backend.core.memory import ConversationMemory
from backend.core.analytics import current_session_id, current_query_id, current_step_name
from backend.core.notifications import notification_manager
from backend.logger import get_logger

logger = get_logger("core.orchestrator")

def load_workspace_rules() -> str:
    """Retrieve Project-Scoped Workspace Rules from .agents/AGENTS.md if they exist."""
    import os
    try:
        paths = [
            os.path.join(os.getcwd(), ".agents", "AGENTS.md"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".agents", "AGENTS.md")
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
    except Exception as e:
        logger.warning(f"Failed to read workspace rules: {e}")
    return "No custom workspace rules defined."


def save_checkpoint(session_id: str, step_num: int, query: str, steps_taken: list, agents_used: set):
    """Saves the current orchestrator state and snapshots the workspace directory."""
    import json
    import shutil
    from backend.config import DATA_DIR, get_user_documents_dir

    checkpoint_base = os.path.join(DATA_DIR, "checkpoints", session_id)
    os.makedirs(checkpoint_base, exist_ok=True)

    # Save state metadata JSON
    metadata = {
        "query": query,
        "step_num": step_num,
        "steps_taken": steps_taken,
        "agents_used": list(agents_used)
    }
    meta_path = os.path.join(checkpoint_base, f"step_{step_num}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Snapshot workspace files
    workspace_src = get_user_documents_dir()
    workspace_dst = os.path.join(checkpoint_base, f"step_{step_num}_workspace")
    if os.path.exists(workspace_dst):
        shutil.rmtree(workspace_dst)
    if os.path.exists(workspace_src):
        try:
            shutil.copytree(workspace_src, workspace_dst, dirs_exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to fully snapshot workspace: {e}")

    logger.info(f"Saved checkpoint for session '{session_id}' at step {step_num}")


def load_checkpoint(session_id: str, step_num: int) -> dict:
    """Loads orchestrator state from metadata and restores workspace directory."""
    import json
    import shutil
    from backend.config import DATA_DIR, get_user_documents_dir

    checkpoint_base = os.path.join(DATA_DIR, "checkpoints", session_id)
    meta_path = os.path.join(checkpoint_base, f"step_{step_num}.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Checkpoint for session '{session_id}' at step {step_num} not found.")

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Restore workspace files
    workspace_src = os.path.join(checkpoint_base, f"step_{step_num}_workspace")
    workspace_dst = get_user_documents_dir()
    if os.path.exists(workspace_src):
        if os.path.exists(workspace_dst):
            try:
                shutil.rmtree(workspace_dst)
            except Exception as e:
                logger.warning(f"Could not clear workspace before restore: {e}")
        try:
            shutil.copytree(workspace_src, workspace_dst, dirs_exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to fully restore workspace: {e}")

    logger.info(f"Loaded checkpoint for session '{session_id}' at step {step_num}")
    return metadata


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

    def _execute_task(self, agent_name: str, query: str, chat_history: str = "") -> str:
        """Execute a single agent task. Preserves conversation context if available."""
        user_id = current_user_id.get()
        enabled_agents = load_enabled_agents(user_id) if user_id else self.registry.get_target_names()
        if agent_name not in enabled_agents:
            return f"Error: Agent '{agent_name}' is not enabled in this workspace profile."

        logger.info(f"Running [{agent_name.upper()}] agent: '{query[:60]}...'")

        # Inject conversation history context so individual agents never lose context
        contextual_query = query
        if chat_history and len(chat_history.strip()) > 0:
            # Take recent history turns to keep context tight
            history_lines = chat_history.strip().split("\n")
            recent_history = "\n".join(history_lines[-10:])
            contextual_query = f"[Relevant Conversation History Context]:\n{recent_history}\n\n[Current Agent Task Query]:\n{query}"

        try:
            result = self.registry.run(agent_name, contextual_query)

            # Analyse → Search fallback (non-blocking, no input() in threads)
            if agent_name == "analyse" and result == "INFORMATION_NOT_AVAILABLE":
                if "search" in self.registry and "search" in enabled_agents:
                    logger.info("Analyse found nothing. Falling back to Search agent...")
                    fallback_result = self.registry.run("search", contextual_query)
                    return f"[SEARCH RESULT (FALLBACK)]:\n{fallback_result}"
                else:
                    return "Information not available in local documents and no search agent is registered or enabled."

            return result

        except Exception as e:
            error_msg = f"Error in {agent_name} agent: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def run(self, query: str, session_id: str = "default_session", max_steps: int = 5, confirm_build: bool | None = None, resume_step: int | None = None, save_checkpoints: bool = True) -> dict:
        """
        Main entry point. Takes a user query, runs a sequential planning loop,
        executes agents step-by-step, synthesizes, and returns the result.
        """
        logger.info(f"Processing query: {query} (session: {session_id}, confirm_build: {confirm_build}, resume_step: {resume_step})")

        # Set usage analytics context parameters
        current_session_id.set(session_id)
        current_query_id.set(query)

        # Load conversation memory
        memory = ConversationMemory(session_id)
        chat_history = memory.get_context_string()

        steps_taken = []
        agents_used = set()
        start_step = 1

        # Hydrate state from checkpoint if resume_step is specified
        if resume_step is not None:
            try:
                checkpoint = load_checkpoint(session_id, resume_step)
                steps_taken = checkpoint["steps_taken"]
                agents_used = set(checkpoint["agents_used"])
                start_step = resume_step + 1
                logger.info(f"Successfully loaded checkpoint. Resuming execution from step {start_step}.")
            except Exception as e:
                logger.error(f"Failed to load checkpoint for resume: {e}. Starting from step 1.")

        for step_num in range(start_step, max_steps + 1):
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
            workspace_rules = load_workspace_rules()
            plan_step = self.planner.plan(
                query=query, 
                agent_descriptions=agent_descriptions,
                valid_targets=valid_targets,
                chat_history=chat_history, 
                scratchpad=scratchpad,
                workspace_rules=workspace_rules
            )

            if plan_step.action == "finish":
                logger.info("Planner decided to finish.")
                break

            # Step 2: Execute agents (potentially in parallel)
            actions = plan_step.actions
            if not actions:
                logger.warning("Planner action was run_agents but actions list was empty. Finishing.")
                break

            # Intercept agent_builder to check for confirmation
            builder_action = next((act for act in actions if act.target == "agent_builder"), None)
            if builder_action:
                agent_query = builder_action.query
                if confirm_build is None:
                    logger.info("Builder Agent execution detected. Pausing for user confirmation.")
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

            # Broadcast execution events
            for act in actions:
                agents_used.add(act.target)
                try:
                    notification_manager.broadcast({
                        "event": "step_progress",
                        "agent": act.target,
                        "query": act.query,
                        "thought": plan_step.thought,
                        "step": step_num,
                        "status": "running"
                    })
                except Exception as e:
                    logger.warning(f"Failed to broadcast step notification: {e}")

            # Execute actions in parallel using ThreadPoolExecutor
            # Ensure ContextVar values are captured and set in the worker threads
            user_id = current_user_id.get()
            session_id = current_session_id.get()
            query_id = current_query_id.get()

            def _worker(act):
                current_user_id.set(user_id)
                current_session_id.set(session_id)
                current_query_id.set(query_id)
                current_step_name.set(f"agent:{act.target}")
                res = self._execute_task(act.target, act.query, chat_history=chat_history)
                return act.target, act.query, res

            results = []
            with ThreadPoolExecutor(max_workers=max(1, len(actions))) as executor:
                futures = [executor.submit(_worker, act) for act in actions]
                for future in futures:
                    try:
                        results.append(future.result())
                    except Exception as e:
                        logger.error(f"Error in parallel worker task: {e}")

            # Zero-Touch dynamically reload registry if agent_builder was used
            if any(target == "agent_builder" for target, _, _ in results):
                logger.info("Agent Builder ran. Scanning for new agents to register...")
                self.registry.scan_and_register_agents()

            # Record steps taken
            for target, act_query, res in results:
                steps_taken.append({
                    "step": step_num,
                    "thought": plan_step.thought,
                    "agent": target,
                    "query": act_query,
                    "result": res
                })
            
            # Save checkpoint
            if save_checkpoints:
                try:
                    save_checkpoint(session_id, step_num, query, steps_taken, agents_used)
                except Exception as e:
                    logger.error(f"Failed to save checkpoint: {e}")

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
        sheets_or_doc_step = next((s for s in steps_taken if "Google Sheets App" in s["result"] or "google_sheets" in s["result"] or "/exports/" in s["result"] or "Click Here to Download" in s["result"]), None)
        if sheets_or_doc_step:
            logger.info(f"Direct document/sheet creation detected in step '{sheets_or_doc_step['agent']}'. Delivering output directly.")
            final_response = sheets_or_doc_step["result"]
        else:
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

