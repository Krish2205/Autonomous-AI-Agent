"""
JARVIS — Multi-Tier Execution Sandbox Manager
Orchestrates three execution tiers:
  1. E2B Cloud Sandbox  (requires E2B_API_KEY)
  2. Local Docker Container  (requires Docker daemon)
  3. Host Subprocess Fallback  (always available, no isolation)
"""

import os
import shutil
import tempfile
import subprocess
from typing import Optional
from backend.logger import get_logger
from backend.config import get_user_documents_dir

logger = get_logger("core.sandbox")

# ── Result Schema ────────────────────────────────────────────────────
def _result(stdout="", stderr="", exit_code=0, tier="unknown", error=None):
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "sandboxed": tier in ("e2b", "docker"),
        "tier": tier,
        "error": error,
    }


# ── Tier 1: E2B Cloud Sandbox ────────────────────────────────────────
class E2BSandbox:
    """Wraps the E2B Code Interpreter cloud sandbox for a single request lifecycle."""

    _e2b_available: Optional[bool] = None  # None = not yet probed

    def __init__(self):
        self._sandbox = None

    @classmethod
    def is_available(cls) -> bool:
        """Returns True only if the E2B_API_KEY env var is configured."""
        if cls._e2b_available is None:
            cls._e2b_available = bool(os.environ.get("E2B_API_KEY"))
        return cls._e2b_available

    def _get_sandbox(self):
        if self._sandbox is None:
            from e2b_code_interpreter import Sandbox
            self._sandbox = Sandbox.create()
            logger.info("E2B cloud sandbox session started.")
        return self._sandbox

    def execute_code(self, code: str) -> dict:
        """Execute a Python code snippet and return structured output."""
        try:
            sb = self._get_sandbox()
            res = sb.run_code(code)
            stdout = "".join(res.logs.stdout)
            stderr = "".join(res.logs.stderr)
            exit_code = 1 if (res.error or (stderr and not stdout)) else 0
            return _result(stdout=stdout, stderr=stderr, exit_code=exit_code, tier="e2b")
        except Exception as e:
            logger.error(f"E2B code execution error: {e}")
            self.cleanup()
            raise

    def run_command(self, cmd: list[str]) -> dict:
        """Run an arbitrary shell command inside the E2B sandbox."""
        try:
            sb = self._get_sandbox()
            res = sb.commands.run(" ".join(cmd), timeout=60)
            return _result(
                stdout=res.stdout or "",
                stderr=res.stderr or "",
                exit_code=res.exit_code,
                tier="e2b",
            )
        except Exception as e:
            logger.error(f"E2B command execution error: {e}")
            self.cleanup()
            raise

    def write_file(self, path: str, content: str) -> None:
        sb = self._get_sandbox()
        sb.files.write(path, content)

    def read_file(self, path: str) -> str:
        sb = self._get_sandbox()
        return sb.files.read(path)

    def list_dir(self, path: str) -> list[str]:
        sb = self._get_sandbox()
        entries = sb.files.list(path)
        result = []
        for e in entries:
            entry_type = e.type.value if hasattr(e.type, "value") else str(e.type)
            label = "DIR" if entry_type == "dir" else "FILE"
            result.append(f"- [{label}] {e.name}")
        return result

    def cleanup(self):
        if self._sandbox is not None:
            try:
                self._sandbox.kill()
                logger.info("E2B cloud sandbox session killed.")
            except Exception:
                pass
            self._sandbox = None


# ── Tier 2: Local Docker Container ──────────────────────────────────
class DockerSandboxManager:
    """Manages a per-user persistent Docker container for local sandboxed execution."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")).lower()
        self.container_name = f"jarvis-sandbox-{safe_user_id}"
        self.image_name = "jarvis-sandbox"

    def is_docker_available(self) -> bool:
        try:
            res = subprocess.run(["docker", "ps"], capture_output=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def ensure_image(self) -> bool:
        try:
            res = subprocess.run(
                ["docker", "images", "-q", self.image_name],
                capture_output=True, text=True, check=True
            )
            if res.stdout.strip():
                return True

            logger.info("Docker image 'jarvis-sandbox' not found. Building it locally...")
            with tempfile.TemporaryDirectory() as tmpdir:
                dockerfile_content = (
                    "FROM python:3.11-slim\n"
                    "RUN apt-get update && apt-get install -y curl build-essential && \\\n"
                    "    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \\\n"
                    "    apt-get install -y nodejs && \\\n"
                    "    rm -rf /var/lib/apt/lists/*\n"
                    "WORKDIR /workspace\n"
                    "CMD [\"sleep\", \"infinity\"]\n"
                )
                dockerfile_path = os.path.join(tmpdir, "Dockerfile")
                with open(dockerfile_path, "w", encoding="utf-8") as f:
                    f.write(dockerfile_content)

                build_res = subprocess.run(
                    ["docker", "build", "-t", self.image_name, tmpdir],
                    capture_output=True, text=True
                )
                if build_res.returncode != 0:
                    logger.error(f"Failed to build Docker image: {build_res.stderr}")
                    return False

                logger.info("Successfully built Docker image 'jarvis-sandbox'.")
                return True
        except Exception as e:
            logger.error(f"Error ensuring Docker image: {e}")
            return False

    def start_container(self) -> bool:
        if not self.is_docker_available():
            logger.warning("Docker daemon is unreachable.")
            return False
        if not self.ensure_image():
            logger.warning("Could not build or retrieve Docker image.")
            return False

        user_dir = get_user_documents_dir()
        abs_user_dir = os.path.abspath(user_dir)
        try:
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", self.container_name],
                capture_output=True, text=True
            )
            status = res.stdout.strip()
            if status == "running":
                return True
            elif status:
                logger.info(f"Starting stopped sandbox container: {self.container_name}")
                subprocess.run(["docker", "start", self.container_name], check=True)
                return True

            logger.info(f"Creating new sandbox container: {self.container_name}")
            subprocess.run([
                "docker", "run", "-d",
                "--name", self.container_name,
                "-v", f"{abs_user_dir}:/workspace",
                "-w", "/workspace",
                self.image_name,
                "sleep", "infinity"
            ], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to manage container {self.container_name}: {e}")
            return False

    def execute(self, cmd: list[str]) -> dict:
        if self.start_container():
            docker_cmd = ["docker", "exec", "-w", "/workspace", self.container_name] + cmd
            logger.info(f"Executing in Docker sandbox: {' '.join(cmd)}")
            try:
                res = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=60)
                return _result(
                    stdout=res.stdout, stderr=res.stderr,
                    exit_code=res.returncode, tier="docker"
                )
            except subprocess.TimeoutExpired:
                return _result(stderr="Execution Timeout (60s)", exit_code=124, tier="docker", error="Timeout")
            except Exception as e:
                logger.error(f"Docker execution failed: {e}")

        # Fallback to host
        return None  # Signal caller to fall through to host fallback

    def stop_container(self) -> bool:
        try:
            subprocess.run(["docker", "stop", self.container_name], capture_output=True)
            subprocess.run(["docker", "rm", self.container_name], capture_output=True)
            logger.info(f"Stopped and removed container {self.container_name}.")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {self.container_name}: {e}")
            return False


# ── Tier 3: Host Subprocess Fallback ────────────────────────────────
def _host_execute(cmd: list[str]) -> dict:
    """Execute a command directly on the host inside the user workspace directory."""
    user_dir = get_user_documents_dir()
    abs_user_dir = os.path.abspath(user_dir)
    logger.warning(f"Falling back to host execution for: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, cwd=abs_user_dir, capture_output=True, text=True, timeout=60)
        return _result(
            stdout=res.stdout,
            stderr=res.stderr + "\n[WARNING: Executed locally on host — Docker/E2B unavailable]",
            exit_code=res.returncode,
            tier="host",
        )
    except subprocess.TimeoutExpired:
        return _result(
            stderr="Execution Timeout (60s)\n[WARNING: Executed locally on host]",
            exit_code=124, tier="host", error="Timeout"
        )
    except Exception as e:
        return _result(
            stderr=f"Host execution failed: {str(e)}", exit_code=1,
            tier="host", error=str(e)
        )


# ── Unified Facade ────────────────────────────────────────────────────
class ExecutionSandbox:
    """
    Unified execution sandbox that automatically selects the best available tier:
      Tier 1 → E2B cloud sandbox  (if E2B_API_KEY is set)
      Tier 2 → Local Docker container  (if Docker daemon is running)
      Tier 3 → Host subprocess fallback  (always available)

    Usage:
        sandbox = ExecutionSandbox(user_id="developer")
        result = sandbox.execute_python("print('hello')")
        result = sandbox.execute_command(["pip", "install", "numpy"])
        content = sandbox.read_file("output.txt")
        sandbox.write_file("script.py", "print('hi')")
        entries = sandbox.list_dir(".")
        sandbox.cleanup()
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._e2b: Optional[E2BSandbox] = None
        self._docker: Optional[DockerSandboxManager] = None
        self._active_tier: Optional[str] = None
        self._workspace = get_user_documents_dir()
        self._detect_tier()

    def _detect_tier(self):
        """Probe and select the best available execution tier on initialization."""
        if E2BSandbox.is_available():
            self._active_tier = "e2b"
            self._e2b = E2BSandbox()
            logger.info("ExecutionSandbox: Active tier -> E2B Cloud Sandbox")
        else:
            self._docker = DockerSandboxManager(self.user_id)
            if self._docker.is_docker_available():
                self._active_tier = "docker"
                logger.info("ExecutionSandbox: Active tier -> Local Docker Container")
            else:
                self._active_tier = "host"
                logger.warning("ExecutionSandbox: Active tier -> Host Subprocess (no isolation)")

    def _fallback_tier(self):
        """Demote to the next available execution tier after a failure."""
        if self._active_tier == "e2b":
            logger.warning("E2B failed. Falling back to Docker...")
            self._e2b = None
            if self._docker is None:
                self._docker = DockerSandboxManager(self.user_id)
            if self._docker.is_docker_available():
                self._active_tier = "docker"
            else:
                self._active_tier = "host"
        elif self._active_tier == "docker":
            logger.warning("Docker failed. Falling back to host subprocess...")
            self._active_tier = "host"

    def execute_python(self, code: str) -> dict:
        """Execute Python code in the best available sandbox environment."""
        return self.execute_code(code, language="python")

    def execute_code(self, code: str, language: str) -> dict:
        """Execute code in a supported programming language inside the sandbox environment."""
        import uuid
        from backend.agents.code_agent import SUPPORTED_LANGUAGES, normalize_language
        
        lang = normalize_language(language)
        lang_info = SUPPORTED_LANGUAGES.get(lang)
        if not lang_info:
            return _result(stderr=f"Unsupported language '{language}'", exit_code=1, tier=self._active_tier)

        ext = lang_info.get("ext", ".txt")
        runner = lang_info.get("runner")

        # E2B Tier: runs Python code natively, other languages via commands
        if self._active_tier == "e2b":
            try:
                if lang == "python":
                    return self._e2b.execute_code(code)
                else:
                    run_filename = f"run_{uuid.uuid4().hex[:8]}{ext}"
                    self._e2b.write_file(run_filename, code)
                    if runner:
                        result = self.execute_command(runner.split() + [run_filename])
                    else:
                        result = _result(stdout=f"Code written to {run_filename}. No runner defined.", tier="e2b")
                    return result
            except Exception as e:
                logger.error(f"E2B tier failed for execute_code: {e}")
                self._fallback_tier()

        # Docker / Host Tier: write script to workspace, then execute command
        run_filename = f"run_{uuid.uuid4().hex[:8]}{ext}"
        temp_run_path = os.path.join(self._workspace, run_filename)
        try:
            with open(temp_run_path, "w", encoding="utf-8") as f:
                f.write(code)
            if runner:
                # Handle compiler/interpreted splits
                if lang == "c":
                    binary_name = run_filename.replace(".c", "")
                    compile_cmd = ["gcc", run_filename, "-o", binary_name]
                    compile_res = self.execute_command(compile_cmd)
                    if compile_res["exit_code"] != 0:
                        return compile_res
                    result = self.execute_command([f"./{binary_name}"])
                elif lang == "cpp":
                    binary_name = run_filename.replace(".cpp", "")
                    compile_cmd = ["g++", run_filename, "-o", binary_name]
                    compile_res = self.execute_command(compile_cmd)
                    if compile_res["exit_code"] != 0:
                        return compile_res
                    result = self.execute_command([f"./{binary_name}"])
                elif lang == "rust":
                    binary_name = run_filename.replace(".rs", "")
                    compile_cmd = ["rustc", run_filename]
                    compile_res = self.execute_command(compile_cmd)
                    if compile_res["exit_code"] != 0:
                        return compile_res
                    result = self.execute_command([f"./{binary_name}"])
                elif lang == "java":
                    compile_cmd = ["javac", run_filename]
                    compile_res = self.execute_command(compile_cmd)
                    if compile_res["exit_code"] != 0:
                        return compile_res
                    class_name = run_filename.replace(".java", "")
                    result = self.execute_command(["java", class_name])
                else:
                    # Interpreted runners
                    result = self.execute_command(runner.split() + [run_filename])
            else:
                result = _result(stdout=f"Code written to {run_filename}. No runner defined.", tier=self._active_tier)
            return result
        finally:
            if os.path.exists(temp_run_path):
                try:
                    os.remove(temp_run_path)
                    # Also try to clean up compiled binaries if any
                    for ext_to_clean in ["", ".exe", ".class"]:
                        bin_path = temp_run_path.rsplit(".", 1)[0] + ext_to_clean
                        if os.path.exists(bin_path):
                            if os.path.isdir(bin_path):
                                shutil.rmtree(bin_path)
                            else:
                                os.remove(bin_path)
                except Exception:
                    pass

    def execute_command(self, cmd: list[str]) -> dict:
        """Execute a shell command in the best available sandbox environment."""
        if self._active_tier == "e2b":
            try:
                return self._e2b.run_command(cmd)
            except Exception as e:
                logger.error(f"E2B command failed: {e}")
                self._fallback_tier()

        if self._active_tier == "docker":
            result = self._docker.execute(cmd)
            if result is not None:
                return result
            self._fallback_tier()

        # Host fallback
        return _host_execute(cmd)

    def write_file(self, path: str, content: str) -> str:
        """Write content to a file in the sandbox workspace."""
        if self._active_tier == "e2b":
            try:
                # E2B uses /home/user as its root; we use a sandboxed relative path
                self._e2b.write_file(path, content)
                return f"Successfully wrote '{path}' in E2B sandbox."
            except Exception as e:
                logger.error(f"E2B write_file failed: {e}")
                self._fallback_tier()

        # Docker / Host: write to local workspace directory
        abs_path = self._safe_path(path)
        if abs_path is None:
            return "Failed: Path is outside the sandbox workspace."
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            tier = self._active_tier
            return f"Successfully wrote '{path}' [{tier} workspace]."
        except Exception as e:
            return f"Failed to write file: {str(e)}"

    def read_file(self, path: str) -> str:
        """Read content from a file in the sandbox workspace."""
        if self._active_tier == "e2b":
            try:
                return self._e2b.read_file(path)
            except Exception as e:
                logger.error(f"E2B read_file failed: {e}")
                self._fallback_tier()

        # Docker / Host: read from local workspace directory
        abs_path = self._safe_path(path)
        if abs_path is None:
            return "Failed: Path is outside the sandbox workspace."
        if not os.path.exists(abs_path):
            return f"Failed: File '{path}' does not exist."
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Failed to read file: {str(e)}"

    def list_dir(self, path: str = ".") -> str:
        """List entries in a directory of the sandbox workspace."""
        if self._active_tier == "e2b":
            try:
                entries = self._e2b.list_dir(path)
                return "\n".join(entries) if entries else "Directory is empty."
            except Exception as e:
                logger.error(f"E2B list_dir failed: {e}")
                self._fallback_tier()

        # Docker / Host: list local workspace directory
        abs_path = self._safe_path(path)
        if abs_path is None:
            return "Failed: Path is outside the sandbox workspace."
        if not os.path.exists(abs_path):
            return f"Failed: Directory '{path}' does not exist."
        try:
            files = os.listdir(abs_path)
            result = []
            for name in files:
                full = os.path.join(abs_path, name)
                label = "DIR" if os.path.isdir(full) else "FILE"
                result.append(f"- [{label}] {name}")
            return "\n".join(result) if result else "Directory is empty."
        except Exception as e:
            return f"Failed to list directory: {str(e)}"

    def _safe_path(self, path: str) -> Optional[str]:
        """Return an absolute path inside the workspace, or None if path escapes it."""
        abs_ws = os.path.abspath(self._workspace)
        candidate = os.path.abspath(os.path.join(abs_ws, path))
        if candidate.startswith(abs_ws):
            return candidate
        return None

    def get_tier_info(self) -> str:
        """Return a short string describing the currently active execution tier."""
        descriptions = {
            "e2b": "E2B Cloud Sandbox (isolated, remote)",
            "docker": "Local Docker Container (isolated, local)",
            "host": "Host Subprocess (unsandboxed, local fallback)",
        }
        return descriptions.get(self._active_tier, "Unknown")

    def cleanup(self):
        """Release any active sandbox resources."""
        if self._e2b is not None:
            self._e2b.cleanup()
        # Docker containers are persistent across requests — no cleanup needed here

    # ── Legacy compatibility shim ────────────────────────────────────
    def execute(self, cmd: list[str]) -> dict:
        """Alias to execute_command() for backward compatibility with existing code."""
        return self.execute_command(cmd)
