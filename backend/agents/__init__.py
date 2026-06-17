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
from backend.agents.image_gen_agent import ImageGenAgent
from backend.agents.calendar_agent import CalendarAgent
from backend.agents.visualization_agent import VisualizationAgent
from backend.agents.notification_agent import NotificationAgent
from backend.agents.voice_agent import VoiceAgent
from backend.agents.finance_agent import FinanceAgent
from backend.agents.package_manager_agent import PackageManagerAgent
from backend.agents.translation_agent import TranslationAgent

# All available agent classes
ALL_AGENTS = [
    SearchAgent,
    CodeAgent,
    AnalyseAgent,
    SummaryAgent,
    EmailAgent,
    DatabaseAgent,
    ScraperAgent,
    ImageGenAgent,
    CalendarAgent,
    VisualizationAgent,
    NotificationAgent,
    VoiceAgent,
    FinanceAgent,
    PackageManagerAgent,
    TranslationAgent,
]

__all__ = [
    "SearchAgent",
    "CodeAgent",
    "AnalyseAgent",
    "SummaryAgent",
    "EmailAgent",
    "DatabaseAgent",
    "ScraperAgent",
    "ImageGenAgent",
    "CalendarAgent",
    "VisualizationAgent",
    "NotificationAgent",
    "VoiceAgent",
    "FinanceAgent",
    "PackageManagerAgent",
    "TranslationAgent",
    "ALL_AGENTS",
]

