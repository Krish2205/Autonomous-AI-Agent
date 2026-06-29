"""
JARVIS — Search Agent
Web search via Tavily API.
Refactored from tavily.py.
"""

from langchain_community.tools.tavily_search import TavilySearchResults as TavilySearch
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.search")


class SearchAgent(BaseAgent):
    name = "search"
    description = "Search the web for real-time information, current events, facts, and external/public data."

    def __init__(self):
        self.search_tool = TavilySearch(max_results=3)
        self.search_tool.description = "Search the web for current news and real-time facts."
        self.tools = [self.search_tool]

    def run(self, query: str) -> str:
        logger.info(f"Searching the web for: {query[:80]}...")

        system_prompt = self.get_system_prompt(
            "You are the Principal Global Intelligence & Open-Source Research Specialist for JARVIS.\n"
            "Your domain expertise lies in real-time information retrieval, fact verification, OSINT intelligence gathering, and synthesising live web findings into concise, verified intelligence summaries.\n\n"
            "<execution_guidelines>\n"
            "1. Execute web search tools to retrieve verified, real-time factual information and news.\n"
            "2. Distill key facts, dates, figures, and source links into structured markdown bullet points.\n"
            "3. Maintain absolute objective accuracy and zero speculation.\n"
            "</execution_guidelines>"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=self.get_llm(), tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("Search completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search error: {str(e)}"
