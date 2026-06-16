"""
JARVIS — Image Generation Agent
Free text-to-image generation using Pollinations.ai API.
"""

import os
import urllib.parse
import time
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.config import llm, GENERATED_IMAGES_DIR
from backend.logger import get_logger

logger = get_logger("agents.image_gen")


class ImageGenParams(BaseModel):
    expanded_prompt: str = Field(description="Highly descriptive and detailed prompt expanded for optimal artistic rendering (under 200 words)")
    width: int = Field(default=1024, description="Width of the image in pixels (e.g. 1024, 1280, 768)")
    height: int = Field(default=1024, description="Height of the image in pixels (e.g. 1024, 720, 1024)")


class ImageGenAgent(BaseAgent):
    name = "image_gen"
    description = "Generate new images, digital art, illustrations, or graphics from natural language text descriptions (completely free)."

    def run(self, query: str) -> str:
        logger.info(f"Running Image Gen Agent with query: {query[:80]}...")

        # Step 1: Use LLM to expand the prompt and extract parameters
        parser = JsonOutputParser(pydantic_object=ImageGenParams)
        
        prompt_enhancer = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert prompt engineer for AI image generators like Flux and Midjourney. "
                "Analyze the user query. Expand the simple prompt into a highly descriptive, vivid, "
                "and detailed artistic prompt. Include specifications for lighting, art style, mood, and camera shots. "
                "Also check if the user specified aspect ratios or dimensions (like landscape, portrait, 16:9, etc.). "
                "Format the output as a JSON object matching this schema:\n{format_instructions}",
            ),
            ("human", "{query}"),
        ]).partial(format_instructions=parser.get_format_instructions())

        try:
            chain = prompt_enhancer | llm | parser
            params = chain.invoke({"query": query})
            expanded_prompt = params.get("expanded_prompt", query)
            width = params.get("width", 1024)
            height = params.get("height", 1024)
        except Exception as e:
            logger.warning(f"Failed to expand prompt via LLM: {e}. Using original query.")
            expanded_prompt = query
            width = 1024
            height = 1024

        logger.info(f"Expanded Prompt: {expanded_prompt}")
        logger.info(f"Dimensions: {width}x{height}")

        # Step 2: Query Pollinations API
        encoded_prompt = urllib.parse.quote(expanded_prompt)
        pollinations_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&nologo=true&private=true"
        )

        filename = f"gen_{int(time.time())}.jpg"
        save_path = os.path.join(GENERATED_IMAGES_DIR, filename)

        try:
            logger.info(f"Fetching image from Pollinations API...")
            response = requests.get(pollinations_url, timeout=30)
            if response.status_code != 200:
                raise RuntimeError(f"Pollinations API returned status code {response.status_code}")

            with open(save_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Successfully saved generated image to: {save_path}")

            # Return markdown-compatible image URL pointing to the FastAPI server mount
            relative_url = f"/images/{filename}"
            result_message = (
                f"🎨 **Image Generated Successfully!**\n\n"
                f"* **Enhanced Prompt**: *{expanded_prompt}*\n"
                f"* **Dimensions**: {width}x{height}\n"
                f"* **Local File Path**: `{save_path}`\n\n"
                f"![Generated Image]({relative_url})"
            )
            return result_message

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return f"Error: Image generation failed due to: {str(e)}"
