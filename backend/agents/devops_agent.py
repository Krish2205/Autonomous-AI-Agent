"""
JARVIS — DevOps Agent
Handles automatic Docker builds, GitHub workflow status checks, and local application log monitoring.
"""

import os
import sys
import subprocess
import requests
from typing import Optional

from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import PROJECT_ROOT, llm
from backend.logger import get_logger

logger = get_logger("agents.devops")


def validate_path(target_path: str) -> str:
    """
    Validates that target_path resides within the permitted workspace boundaries.
    Returns the resolved absolute path if valid, raises ValueError otherwise.
    """
    abs_path = os.path.normcase(os.path.abspath(target_path))
    allowed_roots = [
        os.path.normcase(os.path.abspath(PROJECT_ROOT)),
        os.path.normcase(os.path.abspath(os.path.join(PROJECT_ROOT, "..")))
    ]
    
    is_allowed = False
    for root in allowed_roots:
        if abs_path == root or abs_path.startswith(root + os.sep):
            is_allowed = True
            break
            
    if not is_allowed:
        raise ValueError(f"Path '{target_path}' is outside the authorized workspace boundaries.")
    return os.path.abspath(target_path)


@tool
def build_docker_image(tag: str, dockerfile_path: str = "Dockerfile", context_path: str = ".") -> str:
    """
    Builds a Docker image using local command line.
    
    Parameters:
    - tag: The tag/name to assign to the built image (e.g. 'my-app:latest').
    - dockerfile_path: Path to the Dockerfile (relative to workspace).
    - context_path: Build context directory path (relative to workspace).
    """
    logger.info(f"DevOpsAgent triggering docker build: tag={tag}, file={dockerfile_path}, context={context_path}")
    try:
        # Resolve and validate paths
        # Dockerfile path is relative to context or workspace
        abs_context = validate_path(context_path)
        abs_dockerfile = validate_path(os.path.join(abs_context, dockerfile_path))
        
        if not os.path.exists(abs_dockerfile):
            return f"Error: Dockerfile does not exist at '{dockerfile_path}'"
            
        cmd = ["docker", "build", "-t", tag, "-f", abs_dockerfile, abs_context]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Execute build command
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        output = f"Docker Build Results for tag '{tag}':\n"
        if res.stdout:
            output += f"Stdout:\n{res.stdout}\n"
        if res.stderr:
            output += f"Stderr:\n{res.stderr}\n"
        output += f"Exit Code: {res.returncode}\n"
        return output
        
    except ValueError as ve:
        return f"Security Error: {str(ve)}"
    except Exception as e:
        logger.error(f"Docker build command failed: {e}")
        return f"Failed to run docker build command: {str(e)}"


@tool
def check_github_workflow_runs(repo_owner: str, repo_name: str, limit: int = 5) -> str:
    """
    Checks recent GitHub Actions workflow run statuses for a specified repository.
    
    Parameters:
    - repo_owner: The GitHub user or organization name (e.g. 'Krish2205').
    - repo_name: The repository name (e.g. 'Autonomous-AI-Agent').
    - limit: Maximum number of recent runs to return (default 5).
    """
    logger.info(f"DevOpsAgent fetching GitHub Action runs: {repo_owner}/{repo_name}")
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "JARVIS-DevOps-Agent"
    }
    
    # Authenticate if GITHUB_TOKEN is available
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Failed to retrieve GitHub Actions. GitHub API responded with status {response.status_code}: {response.text}"
            
        data = response.json()
        runs = data.get("workflow_runs", [])
        if not runs:
            return f"No GitHub Actions workflow runs found for '{repo_owner}/{repo_name}'."
            
        result = [f"### Recent GitHub Workflow Runs for {repo_owner}/{repo_name}:"]
        for run in runs[:limit]:
            name = run.get("name", "Unknown Workflow")
            status = run.get("status", "unknown")
            conclusion = run.get("conclusion", "pending")
            event = run.get("event", "push")
            branch = run.get("head_branch", "main")
            html_url = run.get("html_url", "")
            run_number = run.get("run_number", 0)
            
            result.append(
                f"- **Run #{run_number}** - *{name}* ({event} on `{branch}`)\n"
                f"  - **Status**: {status} | **Conclusion**: {conclusion}\n"
                f"  - [View Run Details]({html_url})"
            )
            
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"GitHub Action API call failed: {e}")
        return f"Error querying GitHub API: {str(e)}"


@tool
def monitor_server_logs(lines: int = 50) -> str:
    """
    Retrieves the last N lines of the JARVIS server application log file.
    
    Parameters:
    - lines: The number of lines to tail from the log file (default 50).
    """
    logger.info(f"DevOpsAgent monitoring server logs: lines={lines}")
    try:
        log_file = os.path.abspath(os.path.join(PROJECT_ROOT, "data", "jarvis_app.log"))
        
        if not os.path.exists(log_file):
            return f"Log file '{log_file}' does not exist yet. No application logs recorded."
            
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            # Read all lines
            all_lines = f.readlines()
            
        tail_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        clean_lines = [line.strip() for line in tail_lines]
        
        return f"Last {len(clean_lines)} log entries from '{os.path.basename(log_file)}':\n\n" + "\n".join(clean_lines)
        
    except Exception as e:
        logger.error(f"Failed to read application logs: {e}")
        return f"Error reading application logs: {str(e)}"


class DevOpsAgent(BaseAgent):
    name = "devops"
    description = (
        "Handles DevOps operations including building Docker images locally, "
        "monitoring local server logs, and checking GitHub deployment/workflow runs."
    )

    def __init__(self):
        self.tools = [build_docker_image, check_github_workflow_runs, monitor_server_logs]

    def run(self, query: str) -> str:
        logger.info(f"Running DevOps task: {query[:80]}...")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the JARVIS DevOps Agent.\n"
                "You have tools to build Docker images, monitor local application logs, and query GitHub Actions workflow runs.\n\n"
                "Instructions:\n"
                "1. If asked to inspect server logs, call the `monitor_server_logs` tool.\n"
                "2. If asked to run or build a Docker container/image, call `build_docker_image` with the proper tag and context.\n"
                "3. If asked to inspect GitHub Actions or check build/deployment status, call `check_github_workflow_runs`.\n"
                "4. Be professional and output results in a clean, structured format (e.g. lists, markdown headers).\n"
                "5. CRITICAL: Always repeat, summarize, or copy-paste the relevant logs, docker command outputs, or workflow status details directly into your final response text. Do not just refer to previous lines or say 'shown above', as the user only sees your final response text."
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("DevOps task completed successfully.")
            return result
        except Exception as e:
            logger.error(f"DevOps agent failed: {e}", exc_info=True)
            return f"DevOps error: {str(e)}"
