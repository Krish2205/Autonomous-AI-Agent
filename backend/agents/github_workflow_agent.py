"""
JARVIS — GitHub Workflow Agent
Handles automated pull requests, issue triaging, and repository workflow orchestration.
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

logger = get_logger("agents.github_workflow")


@tool
def create_pull_request_summary(branch: str, title: str, changes_summary: str) -> str:
    """
    Simulates creating and drafting a GitHub Pull Request with a structured summary.
    """
    logger.info(f"GitHubWorkflowAgent drafting PR for branch {branch}")
    return f"[GitHub PR Drafted]: Title='{title}', Branch='{branch}'. Changes: {changes_summary}. Ready for review."


@tool
def triage_github_issue(issue_title: str, issue_body: str) -> str:
    """
    Analyzes and categorizes a GitHub issue, assigning labels and severity level.
    """
    logger.info(f"GitHubWorkflowAgent triaging issue: {issue_title}")
    return f"[Issue Triaged]: Title='{issue_title}'. Category='Bug/Feature', Priority='High'. Recommended labels assigned."


class GitHubWorkflowAgent(BaseAgent):
    name = "github_workflow"
    description = "Automates GitHub operations including drafting pull requests and triaging issues."

    def __init__(self):
        self.tools = [create_pull_request_summary, triage_github_issue]

    def run(self, query: str) -> str:
        logger.info(f"Running GitHub Workflow task: {query[:80]}...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the JARVIS GitHub Workflow Agent. Use your tools to manage PRs and triage repository issues."),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)
        try:
            response = executor.invoke({"query": query})
            return response.get("output", str(response))
        except Exception as e:
            return f"GitHub Workflow error: {str(e)}"
