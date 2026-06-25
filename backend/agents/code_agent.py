"""
JARVIS — Code Agent
File system operations in a containerized sandbox workspace.
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
from backend.core.sandbox import DockerSandboxManager
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
        sandbox = DockerSandboxManager(user_id)

        try:
            # Define tools dynamically bound to this specific sandbox instance
            @tool
            def execute_python(code: str) -> str:
                """Executes arbitrary Python code in the sandbox environment. Returns stdout, stderr, or execution errors."""
                logger.info("Executing Python code in sandbox...")
                import uuid
                from backend.config import get_user_documents_dir
                
                run_filename = f"_run_{uuid.uuid4().hex[:8]}.py"
                workspace_dir = get_user_documents_dir()
                temp_run_path = os.path.join(workspace_dir, run_filename)
                
                try:
                    with open(temp_run_path, "w", encoding="utf-8") as f:
                        f.write(code)
                        
                    # Execute using sandbox manager
                    res = sandbox.execute(["python", run_filename])
                    
                    # Cleanup script file
                    if os.path.exists(temp_run_path):
                        os.remove(temp_run_path)
                        
                    output = ""
                    if res["stdout"]:
                        output += f"Stdout:\n{res['stdout']}\n"
                    if res["stderr"]:
                        output += f"Stderr:\n{res['stderr']}\n"
                    if res["exit_code"] != 0:
                        output += f"Exit Code: {res['exit_code']}\n"
                    
                    if not res["sandboxed"]:
                        output += "\n[Note: Executed in host fallback environment]"
                        
                    return output if output else "Code executed successfully with no output."
                except Exception as e:
                    if os.path.exists(temp_run_path):
                        os.remove(temp_run_path)
                    return f"Error executing python code: {str(e)}"

            @tool
            def write_file_sandbox(path: str, content: str) -> str:
                """Writes content to a file at the specified path in the sandbox workspace."""
                from backend.config import get_user_documents_dir
                workspace_dir = get_user_documents_dir()
                target_path = os.path.abspath(os.path.join(workspace_dir, path))
                
                if not target_path.startswith(os.path.abspath(workspace_dir)):
                    return "Failed: Path is outside the sandbox workspace."
                    
                try:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    return f"Successfully wrote to file '{path}' in sandbox."
                except Exception as e:
                    return f"Failed to write file: {str(e)}"

            @tool
            def read_file_sandbox(path: str) -> str:
                """Reads the contents of a file at the specified path from the sandbox workspace."""
                from backend.config import get_user_documents_dir
                workspace_dir = get_user_documents_dir()
                target_path = os.path.abspath(os.path.join(workspace_dir, path))
                
                if not target_path.startswith(os.path.abspath(workspace_dir)):
                    return "Failed: Path is outside the sandbox workspace."
                    
                try:
                    if not os.path.exists(target_path):
                        return f"Failed: File '{path}' does not exist."
                    with open(target_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    return f"Failed to read file: {str(e)}"

            @tool
            def list_dir_sandbox(path: str = ".") -> str:
                """Lists the files and directories inside the sandbox workspace at the specified path."""
                from backend.config import get_user_documents_dir
                workspace_dir = get_user_documents_dir()
                target_path = os.path.abspath(os.path.join(workspace_dir, path))
                
                if not target_path.startswith(os.path.abspath(workspace_dir)):
                    return "Failed: Path is outside the sandbox workspace."
                    
                try:
                    if not os.path.exists(target_path):
                        return f"Failed: Directory '{path}' does not exist."
                    files = os.listdir(target_path)
                    result = []
                    for file in files:
                        full_f = os.path.join(target_path, file)
                        type_str = "DIR" if os.path.isdir(full_f) else "FILE"
                        result.append(f"- [{type_str}] {file}")
                    return "\n".join(result) if result else "Directory is empty."
                except Exception as e:
                    return f"Failed to list directory: {str(e)}"

            session_tools = [execute_python, write_file_sandbox, read_file_sandbox, list_dir_sandbox]

            system_prompt = self.get_system_prompt(
                "You are a brilliant software engineer. Use the secure sandbox tools to write, read, "
                "list files, or execute Python code to complete your programming and analysis tasks. "
                "All operations and code execution run in an isolated local container sandbox workspace.\n\n"
                "Self-Correction Guideline:\n"
                "If a script execution fails with an error (e.g. Stderr, Exit Code, or traceback exceptions), "
                "you MUST analyze the traceback details, diagnose the root cause (such as NameError, SyntaxError, "
                "ModuleNotFoundError, or IndexError), write corrected code, and execute it again using execute_python. "
                "Do not give up or report the error output to the user. Iterate and correct the code until it succeeds."
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
            logger.info("Code task completed successfully in sandbox.")
            return result

        except Exception as e:
            logger.error(f"Code agent failed: {e}")
            return f"Code error: {str(e)}"
