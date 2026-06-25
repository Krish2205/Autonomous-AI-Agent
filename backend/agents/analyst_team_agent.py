"""
JARVIS — Analyst Team Agent
Orchestrates Analyse, Visualization, Finance, and Database agents.
"""

from backend.agents.team_base import BaseTeamAgent

class AnalystTeamAgent(BaseTeamAgent):
    name = "analyst_team"
    description = (
        "Specialized Business Analyst sub-team consisting of Analyse (RAG/FAISS), Visualization, "
        "Finance, and Database agents. Use this for analyzing local uploaded documents, querying SQL databases, "
        "fetching historical stock/crypto financial charts, and generating visual plots or charts."
    )
    team_agents = ["analyse", "visualization", "finance", "database"]
