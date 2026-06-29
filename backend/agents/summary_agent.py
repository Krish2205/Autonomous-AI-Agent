"""
JARVIS — Summary Agent
Document reading and summarization.
Refactored from summary.py.
"""

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
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
                "You are the Principal Communications Director & Executive Synthesis Specialist for JARVIS.\n"
                "You specialize in rapid document digestion, executive briefings, bulleted synthesis, and high-clarity technical summaries.\n\n"
                "<execution_guidelines>\n"
                "1. If a file path or document is provided, execute `read_document` to ingest its contents.\n"
                "2. Transform lengthy text into structured, punchy executive summaries (Overview, Key Takeaways, Action Items).\n"
                "3. Preserve critical metrics, dates, and names with zero ambiguity.\n"
                "</execution_guidelines>",
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
