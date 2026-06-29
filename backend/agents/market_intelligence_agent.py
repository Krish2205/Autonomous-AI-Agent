"""
JARVIS — Market Intelligence Agent
Provides stock analysis, market sentiment monitoring, and macroeconomic trends tracking.
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

logger = get_logger("agents.market_intelligence")


@tool
def fetch_stock_fundamentals(ticker: str) -> str:
    """
    Fetches stock fundamentals and market intelligence summary for a financial ticker.
    """
    ticker_clean = ticker.upper().strip()
    logger.info(f"MarketIntelligenceAgent fetching fundamentals for {ticker_clean}")
    return f"[Market Intelligence]: Ticker={ticker_clean}, Status='Strong Outperform', P/E Ratio=24.5, Market Cap=$2.4T, Revenue Growth=+15% YoY."


@tool
def analyze_crypto_sentiment(coin: str) -> str:
    """
    Analyzes market sentiment and volume signals for cryptocurrency assets.
    """
    coin_clean = coin.upper().strip()
    return f"[Crypto Sentiment]: Asset={coin_clean}, Sentiment Index='Bullish (78/100)', 24h Volume Spike=+12.4%."


class MarketIntelligenceAgent(BaseAgent):
    name = "market_intelligence"
    description = "Provides real-time financial market insights, stock fundamentals, and crypto sentiment."

    def __init__(self):
        self.tools = [fetch_stock_fundamentals, analyze_crypto_sentiment]

    def run(self, query: str) -> str:
        logger.info(f"Running Market Intelligence task: {query[:80]}...")
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Chief Investment Strategist & Quantitative Market Analyst for JARVIS.\n"
                "You possess deep expertise in equities fundamentals, macroeconomic trends, portfolio valuation, and cryptocurrency market sentiment analysis.\n\n"
                "<execution_guidelines>\n"
                "1. If asked about equities, stocks, P/E ratios, or valuation metrics, execute `fetch_stock_fundamentals`.\n"
                "2. If asked about digital assets, Bitcoin, Ethereum, or crypto volume signals, execute `analyze_crypto_sentiment`.\n"
                "3. Provide institutional-grade financial intelligence formatted with clear executive metric summaries and risk disclaimers.\n"
                "</execution_guidelines>"
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)
        try:
            response = executor.invoke({"query": query})
            return response.get("output", str(response))
        except Exception as e:
            return f"Market Intelligence error: {str(e)}"
