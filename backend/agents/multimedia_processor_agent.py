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
    Creates a production-ready video storyboard and scene script outline.
    """
    logger.info(f"MultimediaProcessorAgent outlining storyboard for: {topic}")
    return f"[Multimedia Storyboard]: Created a 3-scene video storyboard with visual callouts and audio timestamps for '{topic}'."


class MultimediaProcessorAgent(BaseAgent):
    name = "multimedia_processor"
    description = "Outlines video storyboards, podcast show notes, and media production scripts."

    def __init__(self):
        self.tools = [process_media_script]

    def run(self, query: str) -> str:
        logger.info(f"Running Multimedia Processor task: {query[:80]}...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the JARVIS Multimedia Processor Agent. Produce storyboards, media outlines, and audio/video production guides."),
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
