"""
JARVIS — Summary Agent
Document reading and summarization.
Refactored from summary.py.
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.summary")


# ── Tool (module-level for LangChain compatibility) ─────────────────
@tool
def read_document(file_path: str) -> str:
    """Reads a .txt or .pdf document from the local file system and returns its text content. Ensure file_path is an absolute path or relative to the current directory."""
    try:
        if file_path.lower().endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            return "\n".join([doc.page_content for doc in docs])
        elif file_path.lower().endswith(".txt"):
            loader = TextLoader(file_path)
            docs = loader.load()
            return "\n".join([doc.page_content for doc in docs])
        else:
            return "Unsupported file type. Please provide a .txt or .pdf file."
    except Exception as e:
        return f"Error reading file: {str(e)}"


class SummaryAgent(BaseAgent):
    name = "summary"
    description = "Summarize text, documents, or general content. Handle general knowledge questions and text generation tasks."

    def __init__(self):
        self.tools = [read_document]

    def run(self, query: str) -> str:
        logger.info(f"Summarizing: {query[:80]}...")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a brilliant summarizer. Use the read_document tool to read the contents "
                "of files if the user provides a file path. Then summarize the text clearly and concisely.",
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm, self.tools, prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            result = executor.invoke({"query": query})
            logger.info("Summary completed.")
            return result.get("output", str(result))
        except Exception as e:
            logger.error(f"Summary failed: {e}")
            return f"Summary error: {str(e)}"
