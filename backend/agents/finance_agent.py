"""
JARVIS — Finance Agent
Provides stock prices, cryptocurrency data, company financial info, and historical trends.
"""

import json
import yfinance as yf
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.finance")


class FinanceQuery(BaseModel):
    ticker: str = Field(description="The ticker symbol to query (e.g. 'AAPL', 'MSFT', 'BTC-USD', 'EURUSD=X')")
    query_type: str = Field(description="Type of query: 'price' (current stats), 'history' (historical chart data), or 'info' (company profile)")
    period: str = Field(default="5y", description="Time period for history (e.g. '5y', '1y', '6mo', '1mo', '5d')")


class FinanceAgent(BaseAgent):
    name = "finance"
    description = (
        "Retrieve stock prices, cryptocurrency values, currency exchange rates, company financial metrics, "
        "and historical price charts. Input stock tickers (e.g. AAPL, TSLA) or crypto symbols (e.g. BTC-USD)."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Finance Agent with query: {query[:80]}...")

        # Step 1: Parse the query parameters using the LLM
        parser = JsonOutputParser(pydantic_object=FinanceQuery)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Senior Wall Street Equity Research Analyst & Financial Modeling Specialist for JARVIS.\n"
                "You specialize in equity fundamental analysis, SEC ticker parsing, valuation metric extraction, and market sentiment modeling.\n\n"
                "<execution_guidelines>\n"
                "1. Analyze the input query to extract the exact equity or crypto ticker symbol and intended query scope.\n"
                "2. Structure the exact JSON output matching this schema:\n{format_instructions}\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ]).partial(format_instructions=parser.get_format_instructions())

        try:
            chain = prompt | llm | parser
            parsed = chain.invoke({"query": query})
        except Exception as e:
            logger.error(f"Failed to parse finance query: {e}")
            return f"Error: Finance Agent failed to parse input parameters. Details: {str(e)}"

        ticker_symbol = parsed.get("ticker", "").strip().upper()
        query_type = parsed.get("query_type", "price").lower()
        period = parsed.get("period", "5y").lower()

        if not ticker_symbol:
            return "Error: Could not determine ticker symbol. Please specify a symbol like AAPL, GOOG, or BTC-USD."

        logger.info(f"Querying yfinance for {ticker_symbol} (Type: {query_type}, Period: {period})")

        try:
            from backend.config import get_user_integration
            av_integ = get_user_integration("alpha_vantage")
            av_banner = ""
            if av_integ.get("connected"):
                av_acc = av_integ.get("account")
                av_banner = f"\n\n---\n💵 *Synced with connected Alpha Vantage API account:* `{av_acc}`"

            ticker = yf.Ticker(ticker_symbol)
            
            # Step 2: Handle 'info' (company profile)
            if query_type == "info":
                info = ticker.info
                name = info.get("longName", ticker_symbol)
                summary = info.get("longBusinessSummary", "No business summary available.")
                sector = info.get("sector", "N/A")
                industry = info.get("industry", "N/A")
                website = info.get("website", "N/A")
                market_cap = info.get("marketCap", 0)
                pe_ratio = info.get("trailingPE", "N/A")

                report = (
                    f"🏢 **{name} ({ticker_symbol}) Profile**\n\n"
                    f"* **Sector:** {sector}\n"
                    f"* **Industry:** {industry}\n"
                    f"* **Market Capitalization:** ${market_cap:,} USD\n"
                    f"* **P/E Ratio:** {pe_ratio}\n"
                    f"* **Website:** [{website}]({website})\n\n"
                    f"**Business Description:**\n{summary}"
                )
                return report + av_banner

            # Step 3: Handle 'history' (historical chart data - fetches 5 years by default)
            elif query_type == "history" or "chart" in query.lower() or "plot" in query.lower() or "visualize" in query.lower():
                hist = ticker.history(period="5y")  # Fetch 5 years daily data
                if hist.empty:
                    return f"Error: No historical data found for symbol '{ticker_symbol}'."

                # Convert dataframe to a JSON serializable list of dicts
                hist.reset_index(inplace=True)
                data_list = []
                for _, row in hist.iterrows():
                    date_str = row['Date'].strftime('%Y-%m-%d')
                    data_list.append({
                        "date": date_str,
                        "Close": round(float(row['Close']), 2)
                    })

                name = ticker.info.get("longName", ticker_symbol) if hasattr(ticker, "info") else ticker_symbol

                # Format the Recharts spec block
                chart_spec = {
                    "type": "line",
                    "title": f"{name} ({ticker_symbol}) Price History",
                    "xLabel": "Date",
                    "yLabel": "USD ($)",
                    "xKey": "date",
                    "yKeys": ["Close"],
                    "data": data_list
                }

                # We mark this JSON block with a chart type for the frontend to render it
                result_message = (
                    f"📊 **{name} ({ticker_symbol}) Price History**\n\n"
                    f"Here is the daily close history dataset (up to 5 years). "
                    f"Use the buttons on the chart to adjust the timeline range (1W, 1M, 6M, 1Y, 5Y) "
                    f"or change the visualization representation:\n\n"
                    f"```chart\n{json.dumps(chart_spec, indent=2)}\n```"
                )
                return result_message + av_banner

            # Step 4: Handle 'price' (current price metrics)
            else:
                # Get recent data to extract current stats
                today_data = ticker.history(period="5d")
                if today_data.empty:
                    return f"Error: No current price data found for symbol '{ticker_symbol}'."
                
                # Fetch ticker info safely
                info = {}
                try:
                    info = ticker.info
                except Exception:
                    pass

                last_row = today_data.iloc[-1]
                close_price = round(float(last_row['Close']), 2)
                open_price = round(float(last_row['Open']), 2)
                high_price = round(float(last_row['High']), 2)
                low_price = round(float(last_row['Low']), 2)
                volume = int(last_row['Volume'])

                prev_close = today_data.iloc[-2]['Close'] if len(today_data) > 1 else open_price
                price_change = round(close_price - prev_close, 2)
                percent_change = round((price_change / prev_close) * 100, 2)

                change_emoji = "🟢" if price_change >= 0 else "🔴"
                change_sign = "+" if price_change >= 0 else ""

                name = info.get("longName", ticker_symbol) if info else ticker_symbol
                currency = info.get("currency", "USD") if info else "USD"

                report = (
                    f"📈 **{name} ({ticker_symbol}) Current Price Details**\n\n"
                    f"## **{change_emoji} {close_price} {currency}** ({change_sign}{price_change} / {change_sign}{percent_change}%)\n\n"
                    f"* **Daily Open:** {open_price} {currency}\n"
                    f"* **Daily High:** {high_price} {currency}\n"
                    f"* **Daily Low:** {low_price} {currency}\n"
                    f"* **Trading Volume:** {volume:,}\n"
                )
                
                if info.get("marketCap"):
                    report += f"* **Market Capitalization:** ${info.get('marketCap'):,} USD\n"
                if info.get("fiftyTwoWeekHigh"):
                    report += f"* **52-Week Range:** {info.get('fiftyTwoWeekLow')} - {info.get('fiftyTwoWeekHigh')} {currency}\n"

                return report + av_banner

        except Exception as e:
            logger.error(f"Failed to query yfinance data: {e}")
            return f"Error: Finance Agent failed to retrieve data for '{ticker_symbol}'. Details: {str(e)}"
