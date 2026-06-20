"""
JARVIS — Developer Team Agent
Orchestrates Code, Package Manager, and DevOps agents.
"""

from backend.agents.team_base import BaseTeamAgent

class DevTeamAgent(BaseTeamAgent):
    name = "dev_team"
    description = (
        "Specialized Developer sub-team consisting of Code, Package Manager, and DevOps agents. "
        "Use this for complex programming, writing scripts, managing/installing python or node packages, "
        "executing sandboxed code, and verifying DevOps deployment outputs."
    )
    team_agents = ["code", "package_manager", "devops"]
