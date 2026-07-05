"""
JARVIS — Image Generation Agent
Primary  : black-forest-labs/FLUX.1-dev (HuggingFace Inference API)
Fallback : Pollinations.ai (free, no API key needed)

Prompt enhancement via Qwen3-32B-Instruct.
"""

import os
import re
import time
import urllib.parse
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.config import (
    llm,
    GENERATED_IMAGES_DIR, get_user_image_filename, get_user_image_path,
    HF_IMAGE_MODEL, HF_TOKEN_AVAILABLE, hf_inference_post_binary,
)
from backend.logger import get_logger

logger = get_logger("agents.image_gen")


class ImageGenParams(BaseModel):
    expanded_prompt: str = Field(
        description="Highly descriptive and detailed prompt for FLUX.1-dev — under 200 words, optimised for photorealistic and artistic rendering."
    )
    width:  int = Field(default=1024, description="Image width in pixels (e.g. 1024, 1280, 768)")
    height: int = Field(default=1024, description="Image height in pixels (e.g. 1024, 720, 1280)")
    num_inference_steps: int = Field(default=30, description="FLUX inference steps (20-50 for quality)")
    guidance_scale: float = Field(default=3.5, description="FLUX guidance scale (2.0-7.0, higher = more prompt adherent)")


class ImageGenAgent(BaseAgent):
    name = "image_gen"
    description = (
        "Generate high-quality images, digital art, illustrations, and graphics from natural language descriptions. "
        "Powered by black-forest-labs/FLUX.1-dev (HuggingFace) — state-of-the-art open-source image generator."
    )

    def _enhance_prompt(self, query: str) -> dict:
        """Use Qwen3-32B-Instruct to expand the user prompt into a rich FLUX.1-dev prompt."""
        parser = JsonOutputParser(pydantic_object=ImageGenParams)
        prompt_enhancer = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert prompt engineer specialised in FLUX.1-dev image generation. "
                "Transform the user's request into a highly descriptive, cinematic prompt. "
                "Include: lighting style, color palette, art style, camera angle, mood, texture details. "
                "FLUX.1-dev responds best to structured, detailed descriptions. "
                "Also infer the best dimensions and inference parameters.\n"
                "Output JSON matching this schema:\n{format_instructions}",
            ),
            ("human", "{query}"),
        ]).partial(format_instructions=parser.get_format_instructions())

        try:
            chain = prompt_enhancer | llm | parser
            params = chain.invoke({"query": query})
            return {
                "expanded_prompt":       params.get("expanded_prompt", query),
                "width":                 int(params.get("width", 1024)),
                "height":                int(params.get("height", 1024)),
                "num_inference_steps":   int(params.get("num_inference_steps", 30)),
                "guidance_scale":        float(params.get("guidance_scale", 3.5)),
            }
        except Exception as e:
            logger.warning(f"[ImageGen] Prompt enhancement failed: {e}. Using original query.")
            return {
                "expanded_prompt": query,
                "width": 1024, "height": 1024,
                "num_inference_steps": 30, "guidance_scale": 3.5,
            }

    def _generate_flux(self, params: dict) -> bytes | None:
        """Call FLUX.1-dev via HuggingFace Inference API. Returns raw image bytes."""
        payload = {
            "inputs": params["expanded_prompt"],
            "parameters": {
                "width":               params["width"],
                "height":              params["height"],
                "num_inference_steps": params["num_inference_steps"],
                "guidance_scale":      params["guidance_scale"],
            },
        }
        logger.info(f"[ImageGen] Calling FLUX.1-dev ({params['width']}x{params['height']}, {params['num_inference_steps']} steps)...")
        return hf_inference_post_binary(HF_IMAGE_MODEL, payload, timeout=180)

    def _generate_pollinations(self, params: dict) -> bytes | None:
        """Fallback: Pollinations.ai free FLUX endpoint."""
        encoded = urllib.parse.quote(params["expanded_prompt"])
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={params['width']}&height={params['height']}&model=flux&nologo=true&private=true"
        )
        try:
            logger.info(f"[ImageGen] Fallback → Pollinations.ai FLUX...")
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                return resp.content
            logger.error(f"[ImageGen] Pollinations returned {resp.status_code}")
        except Exception as e:
            logger.error(f"[ImageGen] Pollinations failed: {e}")
        return None

    def run(self, query: str) -> str:
        logger.info(f"[ImageGen] Generating image for: {query[:80]}...")

        # Parse aspect ratio parameter overrides from query string (e.g. --ar 16:9)
        ar_width, ar_height = 1024, 1024
        ar_match = re.search(r"--ar\s+(\d+:\d+)", query)
        
        # Clean query parameter block for the LLM prompt expander
        clean_query = query
        if ar_match:
            ar_value = ar_match.group(1)
            clean_query = re.sub(r"--ar\s+\d+:\d+", "", query).strip()
            # Dimensions mapping presets (maintaining ~1 megapixel constraint for FLUX generation speed)
            if ar_value == "16:9":
                ar_width, ar_height = 1344, 768
            elif ar_value == "9:16":
                ar_width, ar_height = 768, 1344
            elif ar_value == "4:3":
                ar_width, ar_height = 1152, 864
            elif ar_value == "3:4":
                ar_width, ar_height = 864, 1152

        # Step 1: Enhance the prompt with Qwen3-32B
        params = self._enhance_prompt(clean_query)
        
        # Apply aspect ratio override dimensions if specified
        if ar_match:
            params["width"] = ar_width
            params["height"] = ar_height
            
        logger.info(f"[ImageGen] Enhanced prompt: {params['expanded_prompt'][:100]}... Dimensions: {params['width']}x{params['height']}")

        # Step 2: Try FLUX.1-dev via HuggingFace
        image_bytes = None
        provider = None

        if HF_TOKEN_AVAILABLE:
            image_bytes = self._generate_flux(params)
            if image_bytes:
                provider = f"FLUX.1-dev (HuggingFace)"

        # Step 3: Fallback to Pollinations.ai
        if not image_bytes:
            logger.info("[ImageGen] FLUX.1-dev unavailable — using Pollinations fallback.")
            image_bytes = self._generate_pollinations(params)
            provider = "FLUX via Pollinations.ai (free fallback)"

        if not image_bytes:
            return (
                "❌ **Image generation failed.** Both FLUX.1-dev (HuggingFace) and Pollinations.ai "
                "are unavailable. Please check your HUGGINGFACE_API_TOKEN and internet connection."
            )

        # Step 4: Save image
        filename = f"gen_{int(time.time())}.jpg"
        user_filename = get_user_image_filename(filename)
        save_path = get_user_image_path(filename)

        try:
            with open(save_path, "wb") as f:
                f.write(image_bytes)
            logger.info(f"[ImageGen] Saved to {save_path}")
        except Exception as e:
            logger.error(f"[ImageGen] Failed to save image: {e}")
            return f"Error: Image generated but failed to save: {str(e)}"

        relative_url = f"/images/{user_filename}"
        return (
            f"🎨 **Image Generated Successfully!**\n\n"
            f"* **Model**: `{provider}`\n"
            f"* **Enhanced Prompt**: *{params['expanded_prompt']}*\n"
            f"* **Dimensions**: {params['width']}×{params['height']} px\n"
            f"* **Inference Steps**: {params['num_inference_steps']}\n"
            f"* **Guidance Scale**: {params['guidance_scale']}\n\n"
            f"![Generated Image]({relative_url})"
        )
