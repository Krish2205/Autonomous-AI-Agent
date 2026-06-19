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
            
        result.append("\nReference structure of a standard agent (e.g. GreetingAgent):")
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
            "logger = get_logger(\"agents.greeting\")\n\n"
            "@tool\n"
            "def get_personalized_greeting(name: str) -> str:\n"
            "    \"\"\"Generates a custom greeting for the given name.\"\"\"\n"
            "    return f\"Hello, {name}! Welcome to JARVIS dynamic operating system.\"\n\n"
            "class GreetingAgent(BaseAgent):\n"
            "    name = \"greeting\"\n"
            "    description = \"Greets users and provides customized welcome messages.\"\n\n"
            "    def __init__(self):\n"
            "        self.tools = [get_personalized_greeting]\n\n"
            "    def run(self, query: str) -> str:\n"
            "        logger.info(f\"Greeting: {query[:80]}...\")\n"
            "        prompt = ChatPromptTemplate.from_messages([\n"
            "            (\n"
            "                \"system\",\n"
            "                \"You are a friendly greeting assistant. Use get_personalized_greeting to greet the user.\"\n"
            "            ),\n"
            "            (\"human\", \"{query}\"),\n"
            "            (\"placeholder\", \"{agent_scratchpad}\")\n"
            "        ])\n"
            "        agent = create_tool_calling_agent(llm, self.tools, prompt)\n"
            "        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)\n"
            "        try:\n"
            "            response = executor.invoke({\"query\": query})\n"
            "            return response.get(\"output\", str(response))\n"
            "        except Exception as e:\n"
            "            logger.error(f\"Greeting failed: {e}\")\n"
            "            return f\"Greeting error: {str(e)}\"\n"
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
                "You are the JARVIS Agent Builder Agent, a meta-agent designed to extend the system.\n"
                "You write custom Python agents and register them dynamically in the system.\n\n"
                "Guidelines:\n"
                "1. If asked to write a new agent, write a clean Python module subclassing BaseAgent.\n"
                "2. Ensure the class inherits from BaseAgent, has class variables name (lowercase string) "
                "and description (string), and implements run(self, query: str) -> str.\n"
                "3. Ensure the module defines LangChain tools with @tool decorator and sets up create_tool_calling_agent.\n"
                "4. Use the `create_agent_file` tool to save your written code.\n"
                "5. Use `list_existing_agent_codes` to look up existing agents and structures for reference.\n"
                "6. CRITICAL IMPORT RULE: You MUST import BaseAgent exactly as: `from backend.agents.base import BaseAgent`. Never import it from any other module like langchain.chains.base. If you import it incorrectly, registration will fail."
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
