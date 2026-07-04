"""
JARVIS — Code Agent
File system operations and code execution in the multi-tier containerized sandbox workspace.
Supports E2B Cloud Sandbox → Local Docker Container → Host Subprocess, in order of preference.
"""

import os
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from backend.agents.base import BaseAgent
from backend.config import llm, current_user_id
from backend.core.sandbox import ExecutionSandbox
from backend.logger import get_logger

logger = get_logger("agents.code")

class CodeAgent(BaseAgent):
    name = "code"
    description = "Write, read, modify, or execute code. Handle programming tasks, file management, data analysis, and software engineering in a secure sandbox."

    def __init__(self):
        self.tools = []

    def run(self, query: str) -> str:
        logger.info(f"Running sandboxed code task: {query[:80]}...")

        user_id = current_user_id.get() or "default"
        sandbox = ExecutionSandbox(user_id)

        logger.info(f"Code Agent execution tier: {sandbox.get_tier_info()}")

        try:
            @tool
            def execute_python(code: str) -> str:
                """Executes arbitrary Python code in the sandbox. Returns stdout, stderr, and exit codes. Use this to run any Python script."""
                logger.info(f"[Code Agent] execute_python called — tier: {sandbox.get_tier_info()}")
                try:
                    res = sandbox.execute_python(code)
                    output = ""
                    if res["stdout"]:
                        output += f"Stdout:\n{res['stdout']}\n"
                    if res["stderr"]:
                        output += f"Stderr:\n{res['stderr']}\n"
                    if res["exit_code"] != 0:
                        output += f"Exit Code: {res['exit_code']}\n"
                    if not res["sandboxed"]:
                        output += f"\n[Note: Executed via {res['tier']} — no isolation active]"
                    return output if output else "Code executed successfully with no output."
                except Exception as e:
                    return f"Error executing Python code: {str(e)}"

            @tool
            def write_file_sandbox(path: str, content: str) -> str:
                """Writes content to a file at the specified path inside the sandbox workspace."""
                logger.info(f"[Code Agent] write_file_sandbox: {path}")
                return sandbox.write_file(path, content)

            @tool
            def read_file_sandbox(path: str) -> str:
                """Reads and returns the contents of a file from the sandbox workspace."""
                logger.info(f"[Code Agent] read_file_sandbox: {path}")
                return sandbox.read_file(path)

            @tool
            def list_dir_sandbox(path: str = ".") -> str:
                """Lists the files and directories inside the sandbox workspace at the specified path."""
                logger.info(f"[Code Agent] list_dir_sandbox: {path}")
                return sandbox.list_dir(path)

            @tool
            def install_pip_package(package_name: str) -> str:
                """Installs a Python package using pip in the sandbox environment. Use this to fix ModuleNotFoundError."""
                logger.info(f"[Code Agent] install_pip_package: {package_name}")
                try:
                    res = sandbox.execute_command(["pip", "install", package_name])
                    output = ""
                    if res["stdout"]:
                        output += f"Stdout:\n{res['stdout']}\n"
                    if res["stderr"]:
                        output += f"Stderr:\n{res['stderr']}\n"
                    if res["exit_code"] != 0:
                        output += f"Exit Code: {res['exit_code']}\n"
                    return output if output else f"Successfully installed '{package_name}'."
                except Exception as e:
                    return f"Failed to install package '{package_name}': {str(e)}"

            session_tools = [execute_python, write_file_sandbox, read_file_sandbox, list_dir_sandbox, install_pip_package]

            tier_note = f"Execution environment: {sandbox.get_tier_info()}"
            system_prompt = self.get_system_prompt(
                "You are the Principal Software Architect & Lead Systems Polyglot Developer for JARVIS.\n"
                "Your expertise covers production-grade algorithm design, file system architecture, automated refactoring, and resilient execution in isolated sandboxes.\n\n"
                f"<execution_environment>\n{tier_note}\n</execution_environment>\n\n"
                "<execution_guidelines>\n"
                "1. Use sandbox file system tools (`write_file_sandbox`, `read_file_sandbox`, `list_dir_sandbox`) and Python runtime (`execute_python`) to execute your work.\n"
                "2. Write robust, clean, modular code following PEP8 standards with proper exception handling.\n"
                "3. SELF-CORRECTION MANDATE: If script execution yields Stderr errors or exceptions (SyntaxError, NameError, ModuleNotFoundError), analyze the stack trace, patch the code, and re-execute until 100% success is achieved. Never report unhandled execution errors.\n"
                "4. If a ModuleNotFoundError occurs, use `install_pip_package` to install the missing dependency, then re-execute.\n"
                "5. Always present well-formatted markdown code blocks with clear explanations.\n"
                "</execution_guidelines>"
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{query}"),
                ("placeholder", "{agent_scratchpad}"),
            ])

            agent = create_tool_calling_agent(llm=self.get_llm(), tools=session_tools, prompt=prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=session_tools,
                verbose=True,
                max_iterations=5,
                handle_parsing_errors=True
            )

            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info(f"Code task completed successfully via {sandbox.get_tier_info()}.")
            return result

        except Exception as e:
            logger.error(f"Code agent failed: {e}")
            return f"Code error: {str(e)}"
        finally:
            # Release E2B session if one was opened for this request
            sandbox.cleanup()
