"""
JARVIS — Code Agent (HuggingFace Edition)
Primary model  : Qwen/Qwen3-Coder-480B-A35B-Instruct  (HuggingFace)
Secondary model: sakmkmk2/Vibe-Coding-Claude-Fable-5   (HuggingFace — fast fallback)
Execution tier : E2B Cloud → Local Docker → Host Subprocess

Supports 30+ programming languages.
"""

import os
import json
import requests
from typing import Optional

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from backend.agents.base import BaseAgent
from backend.config import (
    current_user_id,
    HUGGINGFACE_API_TOKEN, HF_TOKEN_AVAILABLE,
    HF_CODER_MODEL, HF_BASE_URL,
    VIBE_CODING_MODEL_ID, VIBE_CODING_HF_API_URL,
    hf_inference_post,
)
from backend.core.sandbox import ExecutionSandbox
from backend.logger import get_logger

logger = get_logger("agents.code")

# ── Supported Languages ──────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    # Interpreted
    "python":     {"ext": ".py",          "runner": "python3",        "category": "interpreted"},
    "javascript": {"ext": ".js",          "runner": "node",           "category": "interpreted"},
    "typescript": {"ext": ".ts",          "runner": "ts-node",        "category": "interpreted"},
    "ruby":       {"ext": ".rb",          "runner": "ruby",           "category": "interpreted"},
    "php":        {"ext": ".php",         "runner": "php",            "category": "interpreted"},
    "go":         {"ext": ".go",          "runner": "go run",         "category": "interpreted"},
    "dart":       {"ext": ".dart",        "runner": "dart",           "category": "interpreted"},
    "lua":        {"ext": ".lua",         "runner": "lua",            "category": "interpreted"},
    "r":          {"ext": ".r",           "runner": "Rscript",        "category": "interpreted"},
    "julia":      {"ext": ".jl",          "runner": "julia",          "category": "interpreted"},
    # Compiled
    "c":          {"ext": ".c",           "runner": "gcc",            "category": "compiled"},
    "cpp":        {"ext": ".cpp",         "runner": "g++",            "category": "compiled"},
    "rust":       {"ext": ".rs",          "runner": "rustc",          "category": "compiled"},
    "java":       {"ext": ".java",        "runner": "javac",          "category": "compiled"},
    "kotlin":     {"ext": ".kt",          "runner": "kotlinc",        "category": "compiled"},
    "swift":      {"ext": ".swift",       "runner": "swift",          "category": "compiled"},
    "scala":      {"ext": ".scala",       "runner": "scala",          "category": "compiled"},
    "csharp":     {"ext": ".cs",          "runner": "dotnet script",  "category": "compiled"},
    "haskell":    {"ext": ".hs",          "runner": "runhaskell",     "category": "compiled"},
    # Scripting
    "bash":       {"ext": ".sh",          "runner": "bash",           "category": "scripting"},
    "powershell": {"ext": ".ps1",         "runner": "pwsh",           "category": "scripting"},
    "perl":       {"ext": ".pl",          "runner": "perl",           "category": "scripting"},
    "elixir":     {"ext": ".ex",          "runner": "elixir",         "category": "scripting"},
    "erlang":     {"ext": ".erl",         "runner": "escript",        "category": "scripting"},
    # Data / Config / Markup
    "sql":        {"ext": ".sql",         "runner": "sqlite3",        "category": "data"},
    "dockerfile": {"ext": ".dockerfile",  "runner": None,             "category": "config"},
    "terraform":  {"ext": ".tf",          "runner": None,             "category": "config"},
    "yaml":       {"ext": ".yml",         "runner": None,             "category": "config"},
    "html":       {"ext": ".html",        "runner": None,             "category": "markup"},
    "css":        {"ext": ".css",         "runner": None,             "category": "markup"},
    "markdown":   {"ext": ".md",          "runner": None,             "category": "markup"},
    "matlab":     {"ext": ".m",           "runner": "matlab",         "category": "data"},
}

LANGUAGE_ALIASES = {
    "js": "javascript", "ts": "typescript", "c++": "cpp", "c#": "csharp",
    "cs": "csharp", "sh": "bash", "shell": "bash", "ps1": "powershell",
    "py": "python", "rb": "ruby", "rs": "rust", "tf": "terraform",
    "yml": "yaml", "md": "markdown",
}


def normalize_language(lang: str) -> str:
    lang = lang.strip().lower()
    return LANGUAGE_ALIASES.get(lang, lang)


# ── Qwen3-Coder via HuggingFace OpenAI-compatible endpoint ──────────────────
def call_qwen3_coder(prompt: str, language: str = "python", max_tokens: int = 8192) -> Optional[str]:
    """
    Generate code using Qwen/Qwen3-Coder-480B-A35B-Instruct via HuggingFace
    OpenAI-compatible /v1/chat/completions endpoint.
    Returns generated code or None if unavailable.
    """
    if not HF_TOKEN_AVAILABLE:
        logger.warning("[Qwen3-Coder] HF token not set — skipping.")
        return None

    system_msg = (
        f"You are Qwen3-Coder, an elite AI coding model built for expert {language.upper()} development. "
        "Generate clean, complete, production-ready code with proper error handling, "
        "type annotations, and concise inline comments. "
        "Output ONLY the code block, no markdown fences unless part of the language."
    )
    user_msg = (
        f"Generate {language.upper()} code for the following request:\n\n{prompt}\n\n"
        "Requirements:\n"
        "- Complete, immediately runnable code\n"
        "- Proper error handling and edge cases\n"
        "- Best practices for this language\n"
        "- Clear inline comments on key logic\n"
    )

    # Delegate to the central hf_inference_post helper for exponential backoffs on 503 errors
    # Note: Qwen3-Coder uses OpenAI-compatible format if called directly, but we can call it as a text-generation task payload
    # or handle `/chat/completions` formats
    payload_post = {
        "inputs": f"<|im_start|>system\n{system_msg}<|im_end|>\n<|im_start|>user\n{user_msg}<|im_end|>\n<|im_start|>assistant\n",
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": 0.05,
            "top_p": 0.95,
            "return_full_text": False,
            "stop": ["<|im_end|>", "<|im_start|>"]
        }
    }

    try:
        logger.info(f"[Qwen3-Coder] Generating {language} code via HF helper...")
        timeout = 180
        result = hf_inference_post(HF_CODER_MODEL, payload_post, timeout=timeout)
        if isinstance(result, list) and result:
            content = result[0].get("generated_text", "")
            logger.info(f"[Qwen3-Coder] Generated {len(content)} chars of {language} code.")
            return content.strip() or None
        elif isinstance(result, dict) and "generated_text" in result:
            return result["generated_text"].strip() or None
        return None
    except Exception as e:
        logger.error(f"[Qwen3-Coder] Failed: {e}")
        return None


# ── Vibe-Coding secondary fallback ───────────────────────────────────────────
def call_vibe_coding_model(prompt: str, language: str = "python", max_tokens: int = 2048) -> Optional[str]:
    """
    Call sakmkmk2/Vibe-Coding-Claude-Fable-5 as fast secondary fallback.
    Uses Qwen chat template format.
    """
    if not HF_TOKEN_AVAILABLE:
        return None

    system_msg = (
        f"You are Vibe-Coding-Claude-Fable-5, an expert {language.upper()} coding assistant. "
        "Generate clean, production-ready code with error handling and comments."
    )
    formatted_prompt = (
        f"<|im_start|>system\n{system_msg}<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    result = hf_inference_post(VIBE_CODING_MODEL_ID, {
        "inputs": formatted_prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": 0.1,
            "do_sample": True,
            "top_p": 0.95,
            "return_full_text": False,
            "stop": ["<|im_end|>", "<|im_start|>"],
        }
    }, timeout=120)

    if isinstance(result, list) and result:
        return result[0].get("generated_text", "").strip() or None
    return None


class CodeAgent(BaseAgent):
    name = "code"
    description = (
        "Write, read, modify, or execute code in 30+ languages. "
        "Powered by Qwen3-Coder-480B-A35B-Instruct (HuggingFace) — the world's most capable open-source coding model. "
        "Handles programming tasks, file management, data analysis, and software engineering "
        "in a secure multi-tier sandbox environment."
    )

    def __init__(self):
        self.tools = []

    def _detect_language(self, query: str) -> str:
        query_lower = query.lower()
        for lang in SUPPORTED_LANGUAGES:
            if lang in query_lower:
                return lang
        for alias, canonical in LANGUAGE_ALIASES.items():
            if alias in query_lower:
                return canonical
        return "python"

    def run(self, query: str) -> str:
        logger.info(f"[CodeAgent] Task: {query[:100]}...")
        user_id = current_user_id.get() or "default"
        sandbox = ExecutionSandbox(user_id)
        lang = self._detect_language(query)
        lang_info = SUPPORTED_LANGUAGES.get(lang, {})

        logger.info(f"[CodeAgent] language={lang} tier={sandbox.get_tier_info()}")

        # ── Step 1: Try Qwen3-Coder-480B (primary) ──────────────────────────
        model_code = call_qwen3_coder(query, language=lang)
        model_used = HF_CODER_MODEL if model_code else None

        # ── Step 2: Fallback to Vibe-Coding-Claude-Fable-5 ─────────────────
        if not model_code:
            logger.info("[CodeAgent] Qwen3-Coder unavailable — trying Vibe-Coding-Claude-Fable-5...")
            model_code = call_vibe_coding_model(query, language=lang)
            model_used = VIBE_CODING_MODEL_ID if model_code else None

        try:
            @tool
            def execute_python(code: str) -> str:
                """Executes Python code in the sandbox. Returns stdout/stderr/exit codes."""
                try:
                    res = sandbox.execute_python(code)
                    output = ""
                    if res["stdout"]:  output += f"Stdout:\n{res['stdout']}\n"
                    if res["stderr"]:  output += f"Stderr:\n{res['stderr']}\n"
                    if res["exit_code"] != 0: output += f"Exit Code: {res['exit_code']}\n"
                    if not res["sandboxed"]: output += f"\n[Note: Executed via {res['tier']}]"
                    return output or "Code executed successfully with no output."
                except Exception as e:
                    return f"Error: {str(e)}"

            @tool
            def execute_code(code: str, language: str) -> str:
                """Executes source code of any supported language (python, javascript, typescript, rust, go, c, cpp, java, bash, powershell, ruby, php, etc.) in the sandbox. Returns stdout/stderr/exit codes."""
                try:
                    res = sandbox.execute_code(code, language=language)
                    output = ""
                    if res["stdout"]:  output += f"Stdout:\n{res['stdout']}\n"
                    if res["stderr"]:  output += f"Stderr:\n{res['stderr']}\n"
                    if res["exit_code"] != 0: output += f"Exit Code: {res['exit_code']}\n"
                    if not res["sandboxed"]: output += f"\n[Note: Executed via {res['tier']}]"
                    return output or "Code executed successfully with no output."
                except Exception as e:
                    return f"Error: {str(e)}"

            @tool
            def write_file_sandbox(path: str, content: str) -> str:
                """Writes content to a file inside the sandbox workspace."""
                return sandbox.write_file(path, content)

            @tool
            def read_file_sandbox(path: str) -> str:
                """Reads a file from the sandbox workspace."""
                return sandbox.read_file(path)

            @tool
            def list_dir_sandbox(path: str = ".") -> str:
                """Lists files and directories in the sandbox workspace."""
                return sandbox.list_dir(path)

            @tool
            def install_pip_package(package_name: str) -> str:
                """Installs a Python package via pip in the sandbox."""
                try:
                    res = sandbox.execute_command(["pip", "install", package_name])
                    output = ""
                    if res["stdout"]: output += f"Stdout:\n{res['stdout']}\n"
                    if res["stderr"]: output += f"Stderr:\n{res['stderr']}\n"
                    if res["exit_code"] != 0: output += f"Exit Code: {res['exit_code']}\n"
                    return output or f"Successfully installed '{package_name}'."
                except Exception as e:
                    return f"Failed to install '{package_name}': {str(e)}"

            session_tools = [execute_python, execute_code, write_file_sandbox, read_file_sandbox, list_dir_sandbox, install_pip_package]

            # Build system prompt with HF-generated code injected as context
            hf_context = ""
            if model_code:
                short_name = (model_used or "").split("/")[-1]
                hf_context = (
                    f"\n\n<hf_generated_code model=\"{short_name}\">\n"
                    f"HuggingFace model already generated this {lang.upper()} implementation. "
                    f"Use it as your primary implementation — review, refine, test, and execute:\n\n"
                    f"```{lang}\n{model_code}\n```\n"
                    f"</hf_generated_code>\n"
                )

            lang_support_str = ", ".join(sorted(SUPPORTED_LANGUAGES.keys()))
            tier_note = f"Execution environment: {sandbox.get_tier_info()}"
            model_note = (
                f"Primary Model  : {HF_CODER_MODEL} (HuggingFace)\n"
                f"Fallback Model : {VIBE_CODING_MODEL_ID} (HuggingFace)\n"
                f"Detected Language: {lang.upper()} | Category: {lang_info.get('category', 'general')}\n"
                f"Supported Languages: {lang_support_str}"
            )

            system_prompt = self.get_system_prompt(
                "You are the Principal Software Architect & Lead Systems Polyglot Developer for JARVIS.\n"
                f"Primary engine: Qwen3-Coder-480B-A35B-Instruct — the world's most capable open-source coder.\n"
                f"You support all programming languages: {lang_support_str}.\n\n"
                f"<model_info>\n{model_note}\n</model_info>\n\n"
                f"<execution_environment>\n{tier_note}\n</execution_environment>\n"
                f"{hf_context}\n"
                "<execution_guidelines>\n"
                "1. Use sandbox tools (write_file_sandbox, read_file_sandbox, execute_python, execute_code) for work.\n"
                "2. Write robust, modular code with proper error handling and documentation.\n"
                "3. SELF-CORRECTION: If execution yields errors, fix and re-run until success.\n"
                "4. For missing packages, use install_pip_package first.\n"
                "5. For non-Python languages (like rust, go, javascript, typescript, c, cpp, java, bash, powershell), compile and/or run the code inside the sandbox using the execute_code tool specifying the code and target language parameter.\n"
                "6. Always use markdown code blocks with proper language tags.\n"
                "</execution_guidelines>"
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{query}"),
                ("placeholder", "{agent_scratchpad}"),
            ])

            # Use the dedicated code LLM (Qwen3-Coder via HF, or fallback)
            agent = create_tool_calling_agent(llm=self.get_code_llm(), tools=session_tools, prompt=prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=session_tools,
                verbose=True,
                max_iterations=7,
                handle_parsing_errors=True,
            )

            response = executor.invoke({"query": query})
            result = response.get("output", str(response))

            # Attribution header
            if model_used:
                short_name = model_used.split("/")[-1]
                result = (
                    f"> 🤖 **Powered by [{short_name}](https://huggingface.co/{model_used})** "
                    f"via HuggingFace · Language: `{lang.upper()}`\n\n"
                    + result
                )

            logger.info(f"[CodeAgent] Completed via {sandbox.get_tier_info()}.")
            return result

        except Exception as e:
            logger.error(f"[CodeAgent] Failed: {e}")
            return f"Code error: {str(e)}"
        finally:
            sandbox.cleanup()
