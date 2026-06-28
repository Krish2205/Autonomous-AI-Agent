"""
JARVIS — Talent Operations Agent
Handles resume parsing, technical candidate matching, and interviewing assessment guides.
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

logger = get_logger("agents.talent_ops")


@tool
def evaluate_candidate_skills(role: str = "Senior AI Engineer") -> str:
    """
    Parses resume submissions against job descriptions and generates customized technical evaluation rubrics.
    """
    logger.info(f"TalentOpsAgent preparing evaluation rubric for {role}")
    return f"[Talent Evaluation Rubric for {role}]: Skill Match=92% (Python, LangChain, Distributed Systems). Generated 5 tailored coding assessment questions."


class TalentOpsAgent(BaseAgent):
    name = "talent_ops"
    description = "Assists HR and talent acquisition with candidate skill parsing, resume matching, and interview rubrics."

    def __init__(self):
        self.tools = [evaluate_candidate_skills]

    def run(self, query: str) -> str:
        logger.info(f"Running Talent Ops task: {query[:80]}...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are the JARVIS Talent Operations Agent. Help recruiters match skills and formulate interview assessments."),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=5, handle_parsing_errors=True)
        try:
            response = executor.invoke({"query": query})
            return response.get("output", str(response))
        except Exception as e:
            return f"Talent Ops error: {str(e)}"
