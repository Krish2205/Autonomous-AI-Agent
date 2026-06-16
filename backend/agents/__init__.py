"""
JARVIS — Agents Package
Import and register all agents here.
"""

from backend.agents.search_agent import SearchAgent
from backend.agents.code_agent import CodeAgent
from backend.agents.analyse_agent import AnalyseAgent
from backend.agents.summary_agent import SummaryAgent
from backend.agents.email_agent import EmailAgent
from backend.agents.database_agent import DatabaseAgent
from backend.agents.scraper_agent import ScraperAgent

# All available agent classes
ALL_AGENTS = [
    SearchAgent,
    CodeAgent,
    AnalyseAgent,
    SummaryAgent,
    EmailAgent,
    DatabaseAgent,
    ScraperAgent,
]

__all__ = [
    "SearchAgent",
    "CodeAgent",
    "AnalyseAgent",
    "SummaryAgent",
    "EmailAgent",
    "DatabaseAgent",
    "ScraperAgent",
    "ALL_AGENTS",
]
