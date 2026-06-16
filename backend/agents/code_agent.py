"""
JARVIS — Code Agent
File system operations in a sandboxed workspace.
Refactored from coder.py.
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from e2b_code_interpreter import Sandbox

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.code")


class CodeAgent(BaseAgent):
    name = "code"
    description = "Write, read, modify, or execute code. Handle programming tasks, file management, data analysis, and software engineering in a secure sandbox."

    def __init__(self):
        # Tools will be bound dynamically per session to ensure sandbox isolation
        self.tools = []

    def run(self, query: str) -> str:
        logger.info(f"Running sandboxed code task: {query[:80]}...")

        # Initialize the sandbox context manager for this execution session
        try:
            with Sandbox.create() as sandbox:
                logger.info("E2B Sandbox created successfully.")

                # Define tools dynamically bound to this specific sandbox instance
                @tool
                def execute_python(code: str) -> str:
                    """Executes arbitrary Python code in the sandbox notebook/cell. Returns stdout, stderr, or execution errors."""
                    logger.info("Executing Python code in sandbox...")
                    execution = sandbox.run_code(code)
                    if execution.error:
                        return f"Error: {execution.error.name}\n{execution.error.value}\n{execution.error.traceback}"
                    
                    output = ""
                    if execution.text:
                        output += f"Result:\n{execution.text}\n"
                    if execution.stdout:
                        output += f"Stdout:\n{execution.stdout}\n"
                    if execution.stderr:
                        output += f"Stderr:\n{execution.stderr}\n"
                    return output if output else "Code executed successfully with no output."

                @tool
                def write_file_sandbox(path: str, content: str) -> str:
                    """Writes content to a file at the specified path in the sandbox environment."""
                    try:
                        sandbox.files.write(path, content)
                        return f"Successfully wrote to file '{path}' in sandbox."
                    except Exception as e:
                        return f"Failed to write file: {str(e)}"

                @tool
                def read_file_sandbox(path: str) -> str:
                    """Reads the contents of a file at the specified path from the sandbox environment."""
                    try:
                        content = sandbox.files.read(path)
                        return content
                    except Exception as e:
                        return f"Failed to read file: {str(e)}"

                @tool
                def list_dir_sandbox(path: str = ".") -> str:
                    """Lists the files and directories inside the sandbox at the specified path."""
                    try:
                        files = sandbox.files.list(path)
                        result = []
                        for file in files:
                            type_str = "DIR" if file.is_dir else "FILE"
                            result.append(f"- [{type_str}] {file.name}")
                        return "\n".join(result) if result else "Directory is empty."
                    except Exception as e:
                        return f"Failed to list directory: {str(e)}"

                session_tools = [execute_python, write_file_sandbox, read_file_sandbox, list_dir_sandbox]

                prompt = ChatPromptTemplate.from_messages([
                    (
                        "system",
                        "You are a brilliant software engineer. Use the secure sandbox tools to write, read, "
                        "list files, or execute Python code to complete your programming and analysis tasks. "
                        "All operations and code execution run in an isolated remote microVM sandbox.",
                    ),
                    ("human", "{query}"),
                    ("placeholder", "{agent_scratchpad}"),
                ])

                agent = create_tool_calling_agent(llm=llm, tools=session_tools, prompt=prompt)
                executor = AgentExecutor(agent=agent, tools=session_tools, verbose=False)

                response = executor.invoke({"query": query})
                result = response.get("output", str(response))
                logger.info("Code task completed successfully in sandbox.")
                return result

        except Exception as e:
            logger.error(f"Code agent failed: {e}")
            return f"Code error: {str(e)}"

