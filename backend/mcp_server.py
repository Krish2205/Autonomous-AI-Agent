import os
import sys

# Ensure backend modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp.server.fastmcp import FastMCP
from backend.core.registry import AgentRegistry
from backend.core.orchestrator import Orchestrator
from backend.agents import ALL_AGENTS

# Initialize FastMCP Server named "JARVIS"
mcp = FastMCP("JARVIS")

# Initialize registry and register all agents
registry = AgentRegistry()
for AgentClass in ALL_AGENTS:
    registry.register(AgentClass())
orchestrator = Orchestrator(registry)


@mcp.tool()
def query_jarvis(query: str, session_id: str = "mcp_session") -> str:
    """
    Sends a general task/request to JARVIS. JARVIS will coordinate
    its specialized agents (e.g., SQL database, search, RAG) to solve it.
    """
    try:
        res = orchestrator.run(query, session_id=session_id)
        return res.get("response", str(res))
    except Exception as e:
        return f"Error executing task through JARVIS Orchestrator: {str(e)}"


@mcp.tool()
def run_db_query(sql_query: str) -> str:
    """
    Runs a SQL query against the user SQLite database.
    Destructive statements and system tables are blocked by the AST firewall.
    """
    try:
        return registry.run("database", sql_query)
    except Exception as e:
        return f"Error executing database query: {str(e)}"


@mcp.tool()
def search_web(query: str) -> str:
    """
    Performs a real-time web search for information.
    """
    try:
        return registry.run("search", query)
    except Exception as e:
        return f"Error performing web search: {str(e)}"


if __name__ == "__main__":
    mcp.run()
