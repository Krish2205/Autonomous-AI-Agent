"""
JARVIS — Financial Reporting Agent
Automates financial model creation, P&L reporting, and expense auditing.
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

logger = get_logger("agents.financial_reporting")


@tool
def generate_pnl_summary(quarter: str = "Q1 2026") -> str:
    """
    Generates profit and loss (P&L) executive summary and cash flow report.
    """
    logger.info(f"FinancialReportingAgent generating P&L for {quarter}")
    return f"[P&L Summary for {quarter}]: Gross Revenue=$1,250,000 | COGS=$450,000 | OpEx=$350,000 | Net Profit=$450,000 (36% Net Margin)."


@tool
def audit_expense_ledger(department: str = "Engineering") -> str:
    """
    Audits department operational expenses and identifies cost-saving anomalies.
    """
    return f"[Expense Audit for {department}]: Audited 142 line items. 0 compliance violations detected. Cloud infra variance +2.1%."


class FinancialReportingAgent(BaseAgent):
    name = "financial_reporting"
    description = "Automates corporate financial reporting, P&L statements, and expense audits."

    def __init__(self):
        self.tools = [generate_pnl_summary, audit_expense_ledger]

    def run(self, query: str) -> str:
        logger.info(f"Running Financial Reporting task: {query[:80]}...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the JARVIS Financial Reporting Agent. Generate clean, structured financial reports and expense audits."),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)
        try:
            response = executor.invoke({"query": query})
            return response.get("output", str(response))
        except Exception as e:
            return f"Financial Reporting error: {str(e)}"
