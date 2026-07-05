"""
JARVIS — Voice Agent
STT: openai/whisper-large-v3    (HuggingFace Inference API)
TTS: hexgrad/Kokoro-82M         (HuggingFace Inference API)

Provides backend processing for speech recognition and synthesis.
The agent registers capabilities and orchestrates HuggingFace voice model calls.
"""

import os
import base64
import requests
from typing import Optional

from backend.agents.base import BaseAgent
from backend.config import (
    HF_STT_MODEL, HF_TTS_MODEL,
    HF_TOKEN_AVAILABLE, HUGGINGFACE_API_TOKEN, HF_INFERENCE_URL,
)
from backend.logger import get_logger

logger = get_logger("agents.voice")


def transcribe_audio_whisper(audio_bytes: bytes, language: Optional[str] = None) -> Optional[str]:
    """
    Transcribe audio using openai/whisper-large-v3 via HuggingFace Inference API.

    Args:
        audio_bytes: Raw audio bytes (WAV, MP3, FLAC, OGG, etc.)
        language:    Optional ISO 639-1 language code (e.g. 'en', 'hi', 'fr').
                     If None, Whisper auto-detects.

    Returns:
        Transcribed text string, or None if failed.
    """
    if not HF_TOKEN_AVAILABLE:
        logger.warning("[Whisper] HF token not set — cannot transcribe.")
        return None

    url = f"{HF_INFERENCE_URL}/{HF_STT_MODEL}"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "audio/wav",   # HF Inference accepts raw audio bytes
    }

    params = {}
    if language:
        params["language"] = language

    try:
        logger.info(f"[Whisper] Transcribing audio ({len(audio_bytes)} bytes)...")
        resp = requests.post(url, data=audio_bytes, headers=headers, params=params, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            text = result.get("text", "").strip()
            logger.info(f"[Whisper] Transcription: '{text[:80]}...'")
            return text
        elif resp.status_code == 503:
            logger.warning("[Whisper] Model loading (503). Try again shortly.")
        else:
            logger.error(f"[Whisper] Error {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"[Whisper] Request failed: {e}")
        return None


def synthesize_speech_kokoro(text: str, voice: str = "af_heart", speed: float = 1.0) -> Optional[bytes]:
    """
    Synthesize speech using hexgrad/Kokoro-82M via HuggingFace Inference API.

    Args:
        text:  Text to convert to speech (max ~500 chars for best quality).
        voice: Voice ID (e.g. 'af_heart', 'af_bella', 'bf_emma', 'am_adam').
        speed: Speech rate multiplier (0.5–2.0).

    Returns:
        Audio bytes (WAV format), or None if failed.
    """
    if not HF_TOKEN_AVAILABLE:
        logger.warning("[Kokoro] HF token not set — cannot synthesize speech.")
        return None

    url = f"{HF_INFERENCE_URL}/{HF_TTS_MODEL}"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": text,
        "parameters": {
            "voice": voice,
            "speed": speed,
        },
    }

    try:
        logger.info(f"[Kokoro] Synthesizing '{text[:60]}...' with voice='{voice}'")
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            logger.info(f"[Kokoro] Synthesized {len(resp.content)} bytes of audio.")
            return resp.content
        elif resp.status_code == 503:
            logger.warning("[Kokoro] Model loading (503). Try again shortly.")
        else:
            logger.error(f"[Kokoro] Error {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"[Kokoro] Request failed: {e}")
        return None


# Available Kokoro voices with descriptions
KOKORO_VOICES = {
    "af_heart":  {"lang": "en-US (Female)", "style": "Warm, expressive"},
    "af_bella":  {"lang": "en-US (Female)", "style": "Bright, energetic"},
    "af_sarah":  {"lang": "en-US (Female)", "style": "Professional, clear"},
    "af_nicole": {"lang": "en-US (Female)", "style": "Soft, conversational"},
    "bf_emma":   {"lang": "en-GB (Female)", "style": "British, articulate"},
    "bf_isabella": {"lang": "en-GB (Female)", "style": "British, warm"},
    "am_adam":   {"lang": "en-US (Male)",   "style": "Deep, authoritative"},
    "am_michael": {"lang": "en-US (Male)",  "style": "Friendly, clear"},
    "bm_george": {"lang": "en-GB (Male)",   "style": "British, refined"},
    "bm_lewis":  {"lang": "en-GB (Male)",   "style": "British, casual"},
}


class VoiceAgent(BaseAgent):
    name = "voice"
    description = (
        "Speak responses aloud or transcribe voice input. "
        "Uses openai/whisper-large-v3 (STT) and hexgrad/Kokoro-82M (TTS) via HuggingFace. "
        "Trigger when the user asks to read an answer, speak a message, or transcribe audio."
    )

    def run(self, query: str) -> str:
        logger.info(f"[VoiceAgent] Query: {query[:80]}...")

        if HF_TOKEN_AVAILABLE:
            model_info = (
                f"🎙️ **Voice Models Active (HuggingFace)**\n"
                f"* **STT**: `openai/whisper-large-v3` — Multilingual transcription\n"
                f"* **TTS**: `hexgrad/Kokoro-82M` — Natural speech synthesis\n\n"
                f"Voice APIs available at `/api/voice/transcribe` and `/api/voice/synthesize`.\n"
            )
        else:
            model_info = (
                "⚠️ **Voice models require HUGGINGFACE_API_TOKEN.** "
                "Set it in `.env` to enable Whisper STT and Kokoro TTS.\n\n"
            )

        return f"🔊 **Speaking response aloud.**\n\n{model_info}"
