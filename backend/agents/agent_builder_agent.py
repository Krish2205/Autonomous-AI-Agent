"""
JARVIS — Agent Builder Agent
A meta-agent capable of writing new agent code and saving it to the agents package directory.
"""

import os
import re
import sys
from typing import List

from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import PROJECT_ROOT, llm
from backend.logger import get_logger

logger = get_logger("agents.agent_builder")

AGENT_NAME_REGEX = re.compile(r"^[a-z0-9_]+$")


@tool
def list_existing_agent_codes() -> str:
    """
    Lists all Python files inside the backend/agents directory to inspect existing structures.
    Useful for seeing which agent names are taken and referencing templates.
    """
    logger.info("AgentBuilderAgent listing existing agents...")
    try:
        agents_dir = os.path.join(PROJECT_ROOT, "backend", "agents")
        if not os.path.exists(agents_dir):
            return f"Error: Agents directory not found at '{agents_dir}'"
            
        files = os.listdir(agents_dir)
        agent_modules = [f for f in files if f.endswith(".py") and f != "__init__.py" and f != "base.py"]
        
        result = ["Available Agent Files in 'backend/agents/':"]
        for mod in agent_modules:
            result.append(f"- {mod}")
            
        result.append("\nReference structure of an Expert System Agent:")
        result.append(
            "```python\n"
            "try:\n"
            "    from langchain.agents import AgentExecutor, create_tool_calling_agent\n"
            "except ImportError:\n"
            "    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent\n"
            "from langchain_core.prompts import ChatPromptTemplate\n"
            "from langchain_core.tools import tool\n"
            "from backend.agents.base import BaseAgent\n"
            "from backend.config import llm\n"
            "from backend.logger import get_logger\n\n"
            "logger = get_logger(\"agents.expert_domain\")\n\n"
            "@tool\n"
            "def perform_domain_analysis(query_input: str) -> str:\n"
            "    \"\"\"Performs automated domain analysis using free open-source tools.\"\"\"\n"
            "    return f\"[Analysis Output]: Successfully processed '{query_input}'.\"\n\n"
            "class ExpertDomainAgent(BaseAgent):\n"
            "    name = \"expert_domain\"\n"
            "    description = \"Executes domain-specific analysis using open-source tools.\"\n\n"
            "    def __init__(self):\n"
            "        self.tools = [perform_domain_analysis]\n\n"
            "    def run(self, query: str) -> str:\n"
            "        logger.info(f\"Running Expert Domain task: {query[:80]}...\")\n"
            "        prompt = ChatPromptTemplate.from_messages([\n"
            "            (\n"
            "                \"system\",\n"
            "                \"You are the Chief Domain Architect for JARVIS.\\n\"\n"
            "                \"You possess deep domain expertise and execute tasks with rigorous precision.\\n\\n\"\n"
            "                \"<execution_guidelines>\\n\"\n"
            "                \"1. Analyze the input request and invoke domain tools (`perform_domain_analysis`).\\n\"\n"
            "                \"2. Deliver institutional-grade structured markdown reports with clear executive summaries.\\n\"\n"
            "                \"</execution_guidelines>\"\n"
            "            ),\n"
            "            (\"human\", \"{query}\"),\n"
            "            (\"placeholder\", \"{agent_scratchpad}\")\n"
            "        ])\n"
            "        agent = create_tool_calling_agent(llm, self.tools, prompt)\n"
            "        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)\n"
            "        try:\n"
            "            response = executor.invoke({\"query\": query})\n"
            "            return response.get(\"output\", str(response))\n"
            "        except Exception as e:\n"
            "            return f\"Domain error: {str(e)}\"\n"
            "```"
        )
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Failed to list agent files: {e}")
        return f"Error listing agent files: {str(e)}"


@tool
def create_agent_file(agent_name: str, code: str) -> str:
    """
    Writes a new Python agent source code file in the backend/agents directory.
    Validates syntax and schema before saving it.
    
    Parameters:
    - agent_name: The base name of the agent in lowercase, alphanumeric and underscores (e.g. 'greeting', 'math_solver').
                  The written file will be named '{agent_name}_agent.py'.
    - code: The full source code of the agent module, including import statements, tools, and the class itself.
    """
    import subprocess
    logger.info(f"AgentBuilderAgent creating new agent file: {agent_name}_agent.py")
    
    # Clean up name and validate
    agent_name = agent_name.strip().lower()
    if not AGENT_NAME_REGEX.match(agent_name):
        return f"Validation Error: Agent name '{agent_name}' must be alphanumeric and underscores only."
        
    filename = f"{agent_name}_agent.py"
    agents_dir = os.path.join(PROJECT_ROOT, "backend", "agents")
    target_path = os.path.join(agents_dir, filename)
    
    # 1. Syntax Check
    try:
        compile(code, filename, "exec")
    except SyntaxError as se:
        logger.error(f"Syntax validation failed for {filename}: {se}")
        return f"Syntax Error: The generated python code is invalid:\n{str(se)}"
        
    # 2. Write to File
    try:
        os.makedirs(agents_dir, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # 3. Dynamic Import/Execution check in a subprocess
        cmd = [sys.executable, "-c", f"import sys; sys.path.insert(0, {repr(PROJECT_ROOT)}); import backend.agents.{agent_name}_agent"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if res.returncode != 0:
            # Cleanup target path so we don't break subsequent package loads
            if os.path.exists(target_path):
                os.remove(target_path)
            logger.error(f"Import check failed for {filename}:\n{res.stderr}")
            return (
                f"Import/Execution Error: The written agent code is syntactically correct, "
                f"but failed to import or execute during package initialization. Traceback:\n{res.stderr}\n"
                f"Please fix the imports (reference correct templates using list_existing_agent_codes) and try again."
            )
            
        logger.info(f"Agent file {filename} written and validated successfully to: {target_path}")
        return (
            f"Success: Dynamic agent file '{filename}' was created and validated successfully.\n"
            "The dynamic package scanner will auto-detect and register this class "
            "upon the next query, system load, or server reload."
        )
    except Exception as e:
        # Final cleanup safety guard
        if os.path.exists(target_path):
            os.remove(target_path)
        logger.error(f"Failed to write agent file: {e}")
        return f"Error writing agent file: {str(e)}"


class AgentBuilderAgent(BaseAgent):
    name = "agent_builder"
    description = (
        "Writes new Python agent modules dynamically. Use this meta-agent to "
        "extend the operating system's capabilities with new tools and models."
    )

    def __init__(self):
        self.tools = [list_existing_agent_codes, create_agent_file]

    def run(self, query: str) -> str:
        logger.info(f"Running agent builder task: {query[:80]}...")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Chief Meta-Architect & AI Agent Systems Designer for JARVIS.\n"
                "Your role is to autonomously design, construct, validate, and dynamically register world-class, domain-expert AI agents.\n\n"
                "<agent_construction_rules>\n"
                "1. EXPERT SYSTEM PROMPTING: Every agent you construct MUST be assigned an authoritative executive persona (e.g., Chief Architect, Lead Specialist, Director) with explicit `<execution_guidelines>` and structured chain-of-thought rules crafted in the style of Claude system prompts.\n"
                "2. FREE & OPEN-SOURCE TOOL STACK: Equip new agents with clean `@tool` functions leveraging standard Python libraries or free open-source tools (`requests`, `urllib`, `sqlite3`, `beautifulsoup4`, `scikit-learn`, `math`, `json`). Avoid proprietary paid APIs unless standard.\n"
                "3. CLASS & SCHEMA CONSTRAINTS: The module MUST inherit from `BaseAgent`, set `name` (lowercase alphanumeric/underscore), set `description` (clear task summary), and implement `run(self, query: str) -> str` using `create_tool_calling_agent` and `AgentExecutor`.\n"
                "4. CRITICAL IMPORT MANDATE: Always import `BaseAgent` exactly as: `from backend.agents.base import BaseAgent`. Never import it from any chain package.\n"
                "5. EXECUTION: Use `create_agent_file` to save and auto-validate your generated code module.\n"
                "</agent_construction_rules>"
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
            logger.info("Agent builder task completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Agent builder agent failed: {e}", exc_info=True)
            return f"Agent builder error: {str(e)}"
