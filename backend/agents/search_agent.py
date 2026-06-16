"""
JARVIS — Search Agent
Web search via Tavily API.
Refactored from tavily.py.
"""

from langchain_community.tools.tavily_search import TavilySearchResults as TavilySearch
from langchain.agents import AgentExecutor, create_tool_calling_agent
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

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI research assistant. Use tools to find current, accurate information from the web. Provide well-organized answers with key facts."),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("Search completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"Search error: {str(e)}"
