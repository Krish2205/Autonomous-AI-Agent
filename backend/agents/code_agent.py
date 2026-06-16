"""
JARVIS — Code Agent
File system operations in a sandboxed workspace.
Refactored from coder.py.
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.agent_toolkits import FileManagementToolkit

from backend.agents.base import BaseAgent
from backend.config import llm, WORKSPACE_DIR
from backend.logger import get_logger

logger = get_logger("agents.code")


class CodeAgent(BaseAgent):
    name = "code"
    description = "Write, read, modify, or execute code files. Handle programming tasks, file management, and software engineering work."

    def __init__(self):
        file_toolkit = FileManagementToolkit(
            root_dir=WORKSPACE_DIR,
            selected_tools=[
                "read_file", "write_file", "list_directory",
                "file_delete", "copy_file", "move_file", "file_search",
            ],
        )
        self.tools = file_toolkit.get_tools()

    def run(self, query: str) -> str:
        logger.info(f"Running code task: {query[:80]}...")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a brilliant software engineer. Use the file system tools to read, write, "
                "and list files to complete your coding tasks. Always use relative paths "
                "(e.g. 'filename.py') because the toolkit is already rooted in the workspace directory. "
                "Do not prepend '/workspace/' or absolute paths.",
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("Code task completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Code agent failed: {e}")
            return f"Code error: {str(e)}"
