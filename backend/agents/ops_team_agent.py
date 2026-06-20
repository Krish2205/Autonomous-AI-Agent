"""
JARVIS — Operations Team Agent
Orchestrates Calendar, Email, Notification, and Summary agents.
"""

from backend.agents.team_base import BaseTeamAgent

class OpsTeamAgent(BaseTeamAgent):
    name = "ops_team"
    description = (
        "Specialized Administrative Operations sub-team consisting of Calendar, Email, "
        "Notification, and Summary agents. Use this for scheduling events on Google Calendar, "
        "fetching or drafting Gmail emails, summarizing text or logs, and triggering push/Slack notifications."
    )
    team_agents = ["calendar", "email", "notification", "summary"]
