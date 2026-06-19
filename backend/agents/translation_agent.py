"""
JARVIS — Translation Agent
Provides translation and language detection capabilities.
"""

from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.agents.base import BaseAgent
from backend.config import llm
from backend.logger import get_logger

logger = get_logger("agents.translation")


@tool
def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """
    Translates the provided text into the target language.
    Strictly preserves formatting such as markdown links, code blocks, html tags, and variable placeholders.
    """
    logger.info(f"Translating text to {target_lang}...")
    
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a professional, high-fidelity translator.\n"
            "Your task is to translate the provided text from source language '{source_lang}' to target language '{target_lang}'.\n\n"
            "CRITICAL RULES:\n"
            "- Preserve all Markdown elements (links like [text](url), headers, lists, bold/italic syntax).\n"
            "- Preserve all HTML elements and brackets (e.g. <div>, <span>).\n"
            "- Preserve all code blocks (e.g. ```python ... ```).\n"
            "- Do not translate variables or programming symbols (e.g. {{user_name}}, $VAR, value_index).\n"
            "- Output ONLY the final translated text. Do not add any introductory or explanatory text (do not say 'Here is the translation:')."
        ),
        ("human", "{text}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    try:
        translated = chain.invoke({
            "text": text,
            "target_lang": target_lang,
            "source_lang": source_lang
        })
        return translated.strip()
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return f"Translation Error: {str(e)}"


@tool
def detect_language(text: str) -> str:
    """
    Detects the language of the provided text.
    Returns the language name (e.g. 'English', 'French', 'Hindi', 'Chinese').
    """
    logger.info("Detecting language...")
    
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert linguist and language detector.\n"
            "Analyze the text provided by the user and respond with ONLY the name of the language (e.g. 'Spanish', 'French', 'German', 'Hindi').\n"
            "Do not include any punctuation, quotes, or additional words in the response."
        ),
        ("human", "{text}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    try:
        detected = chain.invoke({"text": text})
        return detected.strip()
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return f"Detection Error: {str(e)}"


class TranslationAgent(BaseAgent):
    name = "translation"
    description = (
        "Enables text translation across multiple languages and language detection. "
        "Preserves markdown syntax, code formatting, and tags intact."
    )

    def __init__(self):
        self.tools = [
            translate_text,
            detect_language
        ]

    def run(self, query: str) -> str:
        logger.info(f"Running translation task: '{query[:80]}...'")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the JARVIS Translation Agent.\n"
                "Your goal is to assist the user or system in translating text, documents, "
                "or detecting the language of a text block.\n\n"
                "Guidelines:\n"
                "- If the user query is simply text in another language and a request to translate, "
                "extract the target language and invoke translate_text.\n"
                "- Ensure that formatting in the original text is preserved in your final answer."
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("Translation task completed.")
            return result
        except Exception as e:
            logger.error(f"Translation execution error: {e}")
            return f"Error: {str(e)}"
