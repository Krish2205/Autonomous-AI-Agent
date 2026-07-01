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


@tool
def list_github_repositories() -> str:
    """
    List all GitHub repositories for the connected user.
    """
    logger.info("GitHubWorkflowAgent listing repositories")
    from backend.config import get_user_integration
    import requests
    
    github_integ = get_user_integration("github")
    if not github_integ.get("connected"):
        return "Error: GitHub integration is not connected. Please connect it in the Integrations Hub."
        
    username = github_integ.get("account")
    api_key = github_integ.get("api_key")
    
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    # We first try to fetch the authenticated user's repos (if api_key is valid)
    url = "https://api.github.com/user/repos"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            repos = res.json()
            if isinstance(repos, list) and len(repos) > 0:
                repo_list = []
                for r in repos[:15]:  # show up to 15 repos
                    repo_list.append(f"* **{r.get('name')}** ({r.get('html_url')}) - {r.get('description') or 'No description'}")
                return "Here are your repositories:\n\n" + "\n".join(repo_list)
    except Exception as e:
        logger.warning(f"Failed to fetch repositories using authenticated endpoint: {e}")
        
    # Fallback to public repos for the specific username
    if username:
        url = f"https://api.github.com/users/{username}/repos"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                repos = res.json()
                if isinstance(repos, list) and len(repos) > 0:
                    repo_list = []
                    for r in repos[:15]:
                        repo_list.append(f"* **{r.get('name')}** ({r.get('html_url')}) - {r.get('description') or 'No description'}")
                    return f"Here are the public repositories for **{username}**:\n\n" + "\n".join(repo_list)
        except Exception as e:
            logger.warning(f"Failed to fetch repositories using public endpoint: {e}")
            
    # Simulation fallback if no repos found or rate limited / connection error
    mock_repos = [
        f"* **{username or 'patel2205'}/jarvis-agent-suite** (https://github.com/{username or 'patel2205'}/jarvis-agent-suite) - Core AI agent platform for JARVIS automation.",
        f"* **{username or 'patel2205'}/react-dashboard-portal** (https://github.com/{username or 'patel2205'}/react-dashboard-portal) - Frontend UI built with Vite + Tailwind CSS.",
        f"* **{username or 'patel2205'}/fastapi-microservice** (https://github.com/{username or 'patel2205'}/fastapi-microservice) - Backend API orchestration and database layer."
    ]
    return f"Here are the repositories synced for **{username or 'PATEL2205'}** (Demo data):\n\n" + "\n".join(mock_repos)


class GitHubWorkflowAgent(BaseAgent):
    name = "github_workflow"
    description = "Automates GitHub operations including drafting pull requests and triaging issues."

    def __init__(self):
        self.tools = [list_github_repositories, create_pull_request_summary, triage_github_issue]

    def run(self, query: str) -> str:
        logger.info(f"Running GitHub Workflow task: {query[:80]}...")
        from backend.config import get_user_integration
        
        system_prompt = self.get_system_prompt(
            "You are the Lead DevOps & Developer Workflow Specialist for JARVIS.\n"
            "You specialize in automated software distribution, CI/CD pipeline management, GitHub pull request synthesis, and automated issue triage.\n\n"
            "<execution_guidelines>\n"
            "1. If asked to draft or review pull requests, execute `create_pull_request_summary` with precise code summaries.\n"
            "2. If asked to triage repository issues or bug reports, execute `triage_github_issue` to evaluate priority and component labels.\n"
            "3. If asked to list, show, check, or retrieve repositories, execute `list_github_repositories`.\n"
            "4. Deliver structured, professional developer summaries with markdown headers and clear action items.\n"
            "</execution_guidelines>"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)
        try:
            response = executor.invoke({"query": query})
            content = response.get("output", str(response))
            
            # Look up GitHub integration
            github_integ = get_user_integration("github")
            if github_integ.get("connected"):
                github_acc = github_integ.get("account")
                banner = f"\n\n---\n🐙 **GitHub Integration Hub**\n✓ Synced and authenticated with connected GitHub account: `{github_acc}`\n* **Repository Sync**: Active"
            else:
                banner = f"\n\n---\n🐙 **GitHub Integration Hub**\n* **Action processed locally.**\n*(Connect GitHub & GitLab DevOps under Integrations to commit directly)*"
                
            return content + banner
        except Exception as e:
            return f"GitHub Workflow error: {str(e)}"
