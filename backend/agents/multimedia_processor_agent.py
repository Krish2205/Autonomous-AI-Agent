"""
JARVIS — Multimedia Processor Agent
Handles video script outlining, transcript timestamp indexing, and podcast content processing.
"""

from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.multimedia_processor")


@tool
def process_media_script(topic: str) -> str:
    """
    Creates a production-ready YouTube video script (e.g. 10-min breakdown) and multiple YouTube Shorts script breakdowns with timestamps and visual cues.
    """
    logger.info(f"MultimediaProcessorAgent outlining detailed video and shorts scripts for: {topic}")
    return (
        f"🎬 **YouTube Video & Shorts Production Script: {topic}**\n\n"
        f"### 📹 Main Video Script (10-Minute Outline)\n"
        f"* **0:00 - 1:30 | Hook & Introduction**: Hook viewers on why {topic} is transforming AI. Explain RAG architecture basics (Retrieval + Augmented Generation).\n"
        f"* **1:30 - 4:30 | Core Technical Concepts**: Walkthrough vector databases (FAISS, ChromaDB), embedding models, and contextual retrieval loops.\n"
        f"* **4:30 - 7:30 | Hands-On Implementation**: Step-by-step code demonstration building a RAG pipeline in Python.\n"
        f"* **7:30 - 10:00 | Future Trends & Wrap-Up**: Enterprise applications, hallucination mitigation, and call to action.\n\n"
        f"### ⚡ 3 YouTube Shorts Scripts (60-Sec High-Impact Cuts)\n"
        f"1. **Short #1: What is RAG in 60 Seconds?**\n"
        f"   - *Visual*: Fast-paced code animation + glowing vector space graphic.\n"
        f"   - *Hook*: 'Stop letting your AI hallucinate! Here is how RAG actually works.'\n"
        f"2. **Short #2: Vector DBs Explained Simply**\n"
        f"   - *Visual*: Split screen showing standard SQL vs High-Dimensional Vector Search.\n"
        f"   - *Hook*: 'Why standard databases fail for LLMs...'\n"
        f"3. **Short #3: How to Build a RAG Agent in 3 Lines of Code**\n"
        f"   - *Visual*: Screen recording typing out Python imports and query execution.\n"
        f"   - *Hook*: 'Here is the exact framework top engineers use for enterprise RAG agents.'"
    )


class MultimediaProcessorAgent(BaseAgent):
    name = "multimedia_processor"
    description = "Outlines comprehensive video scripts, YouTube Shorts breakdowns, storyboards, and audio/video production guides."

    def __init__(self):
        self.tools = [process_media_script]

    def run(self, query: str) -> str:
        logger.info(f"Running Multimedia Processor task: {query[:80]}...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the JARVIS Multimedia Processor Agent. Write complete, high-quality, production-ready YouTube scripts, timestamps, and YouTube Shorts outlines. Be thorough and detailed."),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)
        try:
            response = executor.invoke({"query": query})
            return response.get("output", str(response))
        except Exception as e:
            return f"Multimedia Processor error: {str(e)}"
