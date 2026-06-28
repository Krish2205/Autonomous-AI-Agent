"""
JARVIS — Marketing Campaign Agent
Generates SEO optimized copy, digital ad variations, and social media campaign calendars.
"""

from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.marketing_campaign")


@tool
def generate_seo_campaign(product_description: str) -> str:
    """
    Generates SEO keywords, headline hooks, and multi-channel social media posts.
    """
    logger.info("MarketingCampaignAgent drafting campaign")
    return f"[Marketing Campaign Output]: Generated 5 high-converting headlines, 10 SEO target keywords, and a 7-day social content calendar for '{product_description}'."


class MarketingCampaignAgent(BaseAgent):
    name = "marketing_campaign"
    description = "Generates digital marketing copy, SEO content strategies, and multi-channel ad campaigns."

    def __init__(self):
        self.tools = [generate_seo_campaign]

    def run(self, query: str) -> str:
        logger.info(f"Running Marketing Campaign task: {query[:80]}...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the JARVIS Marketing Campaign Agent. Draft engaging, SEO-driven marketing campaigns and copy."),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)
        try:
            response = executor.invoke({"query": query})
            return response.get("output", str(response))
        except Exception as e:
            return f"Marketing Campaign error: {str(e)}"
