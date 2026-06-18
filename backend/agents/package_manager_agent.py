"""
JARVIS — Package Manager Agent
Manages dependencies and environments (pip, npm) using secure containerized Docker sandboxes.
"""

import os
import re
import sys
import subprocess
from typing import Literal

from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import PROJECT_ROOT, llm, current_user_id
from backend.core.sandbox import DockerSandboxManager
from backend.logger import get_logger

logger = get_logger("agents.package_manager")

# ── Validation Regexes ────────────────────────────────────────────────
PYTHON_PKG_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.\[\]]+(?:[<=>!~]+[a-zA-Z0-9_\-\.\*]+)?$")
NODE_PKG_REGEX = re.compile(r"^(?:@[a-zA-Z0-9_\-\.]+\/)?[a-zA-Z0-9_\-\.]+(?:@[a-zA-Z0-9_\-\.\*^~]+)?$")

def validate_path(project_path: str) -> str:
    """
    Validates that the project_path resides within the permitted workspace or project root.
    Returns the resolved absolute path if valid, raises ValueError otherwise.
    """
    abs_path = os.path.abspath(project_path)
    allowed_roots = [
        os.path.abspath(PROJECT_ROOT),
        os.path.abspath(os.path.join(PROJECT_ROOT, ".."))
    ]
    
    is_allowed = False
    for root in allowed_roots:
        if abs_path == root or abs_path.startswith(root + os.sep):
            is_allowed = True
            break
            
    if not is_allowed:
        raise ValueError(f"Path '{project_path}' is outside the authorized workspace boundaries.")
    return abs_path

@tool
def detect_ecosystem(project_path: str) -> str:
    """
    Scans the project_path to discover package files (requirements.txt, package.json, Cargo.toml).
    Returns the detected ecosystems.
    """
    try:
        abs_path = validate_path(project_path)
    except ValueError as e:
        return str(e)

    ecosystems = []
    if os.path.exists(os.path.join(abs_path, "requirements.txt")) or os.path.exists(os.path.join(abs_path, "pyproject.toml")):
        ecosystems.append("python")
    if os.path.exists(os.path.join(abs_path, "package.json")):
        ecosystems.append("node")
    if os.path.exists(os.path.join(abs_path, "Cargo.toml")):
        ecosystems.append("rust")

    if not ecosystems:
        return f"No active ecosystems detected in '{project_path}'. Available files: {os.listdir(abs_path)}"
    return f"Detected ecosystems: {', '.join(ecosystems)}"

@tool
def list_dependencies(ecosystem: Literal["python", "node"], project_path: str) -> str:
    """
    Lists current dependencies. For python, reads requirements.txt or queries installed packages inside the container.
    For node, reads package.json dependencies.
    """
    try:
        abs_path = validate_path(project_path)
    except ValueError as e:
        return str(e)

    if ecosystem == "python":
        req_file = os.path.join(abs_path, "requirements.txt")
        if os.path.exists(req_file):
            with open(req_file, "r", encoding="utf-8") as f:
                content = f.read()
            return f"Dependencies from requirements.txt:\n{content}"
        else:
            try:
                user_id = current_user_id.get() or "default"
                sandbox = DockerSandboxManager(user_id)
                res = sandbox.execute(["pip", "list"])
                output = f"Installed python packages:\n{res['stdout']}"
                if res["stderr"]:
                    output += f"\nStderr:\n{res['stderr']}"
                if not res["sandboxed"]:
                    output += "\n[Note: Executed in host fallback environment]"
                return output
            except Exception as ex:
                return f"Failed to list python packages: {str(ex)}"

    elif ecosystem == "node":
        pkg_file = os.path.join(abs_path, "package.json")
        if os.path.exists(pkg_file):
            import json
            try:
                with open(pkg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                return json.dumps({"dependencies": deps, "devDependencies": dev_deps}, indent=2)
            except Exception as ex:
                return f"Error parsing package.json: {str(ex)}"
        else:
            return "package.json not found in the project path."

    return f"Unsupported ecosystem '{ecosystem}' for listing dependencies."

@tool
def install_dependency(ecosystem: Literal["python", "node"], package_name: str, project_path: str) -> str:
    """
    Installs a single dependency safely inside the sandbox container environment.
    """
    try:
        abs_path = validate_path(project_path)
    except ValueError as e:
        return str(e)

    package_name = package_name.strip()
    if ecosystem == "python":
        if not PYTHON_PKG_REGEX.match(package_name):
            return f"Validation Error: Package name '{package_name}' is invalid/unsafe for Python pip."
        cmd = ["pip", "install", package_name]
    elif ecosystem == "node":
        if not NODE_PKG_REGEX.match(package_name):
            return f"Validation Error: Package name '{package_name}' is invalid/unsafe for Node npm."
        cmd = ["npm", "install", package_name]
    else:
        return f"Unsupported ecosystem '{ecosystem}' for package installation."

    logger.info(f"Executing package installation: {cmd}")
    try:
        user_id = current_user_id.get() or "default"
        sandbox = DockerSandboxManager(user_id)
        res = sandbox.execute(cmd)
        
        output = f"Package '{package_name}' installation completed.\n"
        if res["stdout"]:
            output += f"Stdout:\n{res['stdout']}\n"
        if res["stderr"]:
            output += f"Stderr:\n{res['stderr']}\n"
        output += f"Exit Code: {res['exit_code']}\n"
        if not res["sandboxed"]:
            output += "[Note: Executed in host fallback environment]\n"
            
        return output
    except Exception as ex:
        return f"Error executing installation: {str(ex)}"

@tool
def uninstall_dependency(ecosystem: Literal["python", "node"], package_name: str, project_path: str) -> str:
    """
    Uninstalls a single dependency safely from the sandbox container environment.
    """
    try:
        abs_path = validate_path(project_path)
    except ValueError as e:
        return str(e)

    package_name = package_name.strip()
    if ecosystem == "python":
        if not PYTHON_PKG_REGEX.match(package_name):
            return f"Validation Error: Package name '{package_name}' is invalid/unsafe for Python pip."
        cmd = ["pip", "uninstall", "-y", package_name]
    elif ecosystem == "node":
        if not NODE_PKG_REGEX.match(package_name):
            return f"Validation Error: Package name '{package_name}' is invalid/unsafe for Node npm."
        cmd = ["npm", "uninstall", package_name]
    else:
        return f"Unsupported ecosystem '{ecosystem}' for package uninstallation."

    logger.info(f"Executing package uninstallation: {cmd}")
    try:
        user_id = current_user_id.get() or "default"
        sandbox = DockerSandboxManager(user_id)
        res = sandbox.execute(cmd)
        
        output = f"Package '{package_name}' uninstallation completed.\n"
        if res["stdout"]:
            output += f"Stdout:\n{res['stdout']}\n"
        if res["stderr"]:
            output += f"Stderr:\n{res['stderr']}\n"
        output += f"Exit Code: {res['exit_code']}\n"
        if not res["sandboxed"]:
            output += "[Note: Executed in host fallback environment]\n"
            
        return output
    except Exception as ex:
        return f"Error executing uninstallation: {str(ex)}"

class PackageManagerAgent(BaseAgent):
    name = "package_manager"
    description = (
        "Enables ecosystem detection, dependency listing, installation, and uninstallation "
        "of verified packages (pip for Python, npm for Node.js) within approved workspace directories."
    )

    def __init__(self):
        self.tools = [
            detect_ecosystem,
            list_dependencies,
            install_dependency,
            uninstall_dependency
        ]

    def run(self, query: str) -> str:
        logger.info(f"Running package manager task: '{query[:80]}...'")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the JARVIS Package Manager Agent.\n"
                "Your goal is to assist the system/user by inspecting dependencies, detecting ecosystems, "
                "or running validated installations/uninstallations of environment dependencies.\n\n"
                "Important Rules:\n"
                "- Always verify which ecosystem (python/node) is required before taking actions.\n"
                "- Do not assume paths. If not specified, default to the current project directory or check folders using workspace tools.\n"
                "- If a tool indicates validation errors, report the exact security check failure message."
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("package manager task completed.")
            return result
        except Exception as e:
            logger.error(f"Package manager execution error: {e}")
            return f"Error: {str(e)}"
