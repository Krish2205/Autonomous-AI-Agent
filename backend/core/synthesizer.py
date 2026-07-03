"""
JARVIS — Response Synthesizer
Merges results from multiple agents into a cohesive final response.
Extracted from router.py.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.config import llm
from backend.logger import get_logger

logger = get_logger("core.synthesizer")


class Synthesizer:
    """Combines agent results into a single, professional response."""

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Super Manager. You are given a user's original query, and the outputs from "
                "various specialized agents (Search, Code, Analyse, Summary, Email, Image Generation, etc.) that worked on sub-tasks. "
                "Combine their findings into a single, professional, and cohesive final response for the user. "
                "Do not mention the internal agents by name; present the answer naturally. "
                "If code was generated, include it nicely formatted in markdown. "
                "If data was analyzed, present the insights clearly. "
                "If emails were involved, summarize the actions taken. "
                "STRICT HUMAN-LIKE ACCURACY RULE:\n"
                "1. Answer ONLY what the user explicitly requested. Do not add unrequested bonus actions or unasked topics.\n"
                "2. PRESERVE PDF DOWNLOAD LINKS & MEDIA LINKS EXACTLY: If any agent returned a downloadable PDF link (e.g. `[📥 Click Here to Download...]`) or media links, YOU MUST PRESERVE THOSE EXACT LINKS IN YOUR FINAL RESPONSE. NEVER claim or hallucinate that you cannot generate direct PDFs.\n"
                "3. PRESERVE EXHAUSTIVE CONTENT: If an agent generated a comprehensive, detailed day-by-day lesson plan, timeline, or examination paper, preserve the full detailed markdown without summarizing, condensing, or truncating it.\n\n"
                "Conversation History for context:\n"
                "{chat_history}",
            ),
            ("human", "Original Query: {query}\n\nAgent Results:\n{agent_results}"),
        ])
        self.chain = self.prompt | llm | StrOutputParser()

    def synthesize(self, query: str, agent_results: str, chat_history: str = "") -> str:
        """Combine all agent results and conversation history into a final response."""
        logger.info("Synthesizing final response...")
        try:
            result = self.chain.invoke({
                "query": query,
                "agent_results": agent_results,
                "chat_history": chat_history,
            })
            logger.info("Synthesis complete.")
            return result
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return f"Error synthesizing response: {str(e)}"
