"""
JARVIS — Base Team Agent
Base class for sub-orchestrator agent teams.
"""

from backend.agents.base import BaseAgent
from backend.core.planner import Planner
from backend.core.synthesizer import Synthesizer
from backend.logger import get_logger

class BaseTeamAgent(BaseAgent):
    """
    Abstract/Base class for team agents. A team agent coordinates 
    several member agents in a local sequential planning loop.
    """
    team_agents: list[str] = []

    def __init__(self):
        self.planner = Planner()
        self.synthesizer = Synthesizer()
        self.logger = get_logger(f"agents.team.{self.name}")

    def run(self, query: str) -> str:
        if not hasattr(self, 'registry') or not self.registry:
            return f"Error: Team agent '{self.name}' does not have access to the registry."

        self.logger.info(f"Team '{self.name}' starting loop for query: '{query[:60]}...'")

        steps_taken = []
        chat_history = ""
        max_steps = 4

        for step_num in range(1, max_steps + 1):
            # Format sub-scratchpad for the sub-planner
            scratchpad_lines = []
            for s in steps_taken:
                scratchpad_lines.append(
                    f"Step {s['step']}:\n"
                    f"- Thought: {s['thought']}\n"
                    f"- Action: Called agent '{s['agent']}' with query '{s['query']}'\n"
                    f"- Result: {s['result']}\n"
                )
            scratchpad = "\n".join(scratchpad_lines) if scratchpad_lines else "No steps taken yet."

            # Construct descriptions of only the team members that are registered and enabled
            descriptions_lines = []
            valid_targets = []
            for name in self.team_agents:
                if name in self.registry:
                    agent = self.registry.get(name)
                    if agent:
                        descriptions_lines.append(f"- '{name}': {agent.description}")
                        valid_targets.append(name)

            if not valid_targets:
                return f"Error: No member agents of team '{self.name}' are currently registered or enabled."

            agent_descriptions = "\n".join(descriptions_lines)

            # Step 1: Sub-planner decides action
            plan_step = self.planner.plan(
                query=query,
                agent_descriptions=agent_descriptions,
                valid_targets=valid_targets,
                chat_history=chat_history,
                scratchpad=scratchpad
            )

            if plan_step.action == "finish":
                self.logger.info(f"Team '{self.name}' sub-planner decided to finish.")
                break

            agent_name = plan_step.target
            agent_query = plan_step.query

            if not agent_name or not agent_query:
                break

            # Step 2: Execute member agent
            self.logger.info(f"Team '{self.name}' step {step_num}: calling [{agent_name}] with '{agent_query[:50]}...'")
            try:
                result = self.registry.run(agent_name, agent_query)
            except Exception as e:
                result = f"Error executing {agent_name}: {str(e)}"

            # Record step
            steps_taken.append({
                "step": step_num,
                "thought": plan_step.thought,
                "agent": agent_name,
                "query": agent_query,
                "result": result
            })

        # Step 3: Synthesize sub-team results
        if steps_taken:
            combined_results_list = []
            for s in steps_taken:
                combined_results_list.append(
                    f"--- Team Step {s['step']}: Agent '{s['agent']}' ---\n"
                    f"Query: {s['query']}\n"
                    f"Result:\n{s['result']}"
                )
            combined_results = "\n\n".join(combined_results_list)
        else:
            combined_results = "No action steps were taken by the team."

        final_response = self.synthesizer.synthesize(query, combined_results, chat_history="")
        self.logger.info(f"Team '{self.name}' completed work. Synthesized response generated.")
        return final_response
