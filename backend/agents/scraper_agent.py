"""
JARVIS — Web Scraper Agent
Extracts clean, formatted body text from any given URL.
"""

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.scraper")


@tool
def scrape_url(url: str) -> str:
    """
    Scrape and extract the text content from a web URL.
    This strips HTML tags, headers, footers, and scripts, returning the core body content.
    """
    logger.info(f"Scraping web page: {url}")
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Decompose elements that don't contain core content
        for element in soup(["script", "style", "head", "header", "footer", "nav", "aside"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean up whitespaces
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase for phrase in lines if phrase)
        clean_text = "\n".join(chunks)

        # Truncate content to avoid token context overflow
        max_chars = 12000
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + f"\n\n... [Content truncated, total length: {len(clean_text)} characters] ..."

        logger.info("Scraping completed successfully.")
        return clean_text

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return f"Error scraping URL '{url}': {str(e)}"


class ScraperAgent(BaseAgent):
    name = "scraper"
    description = (
        "Scrape and extract clean text content from a specific web URL. "
        "Allows direct context gathering from online documentation, articles, or sites."
    )

    def __init__(self):
        self.tools = [scrape_url]

    def run(self, query: str) -> str:
        logger.info(f"Running scraper task: {query[:80]}...")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert web scraper assistant.\n"
                "Your goal is to extract the clean text content from the target URL requested by the user.\n\n"
                "Instructions:\n"
                "1. Identify the URL from the user prompt.\n"
                "2. Call the `scrape_url` tool with that URL.\n"
                "3. Retrieve the clean content, summarize it or return the requested section, and present it clearly to the user."
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("Scraper task completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Scraper agent failed: {e}")
            return f"Scraper error: {str(e)}"
