"""
JARVIS — Containerized Docker Sandbox Manager
Manages user-scoped Docker containers for secure Code and Package execution.
Provides seamless fallback to local subprocess execution if Docker is unavailable.
"""

import os
import shutil
import tempfile
import subprocess
from backend.logger import get_logger
from backend.config import get_user_documents_dir

logger = get_logger("core.sandbox")

class DockerSandboxManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        # Sanitize user_id to form a valid docker container name
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")).lower()
        self.container_name = f"jarvis-sandbox-{safe_user_id}"
        self.image_name = "jarvis-sandbox"

    def is_docker_available(self) -> bool:
        """Check if the Docker daemon is running and reachable."""
        try:
            res = subprocess.run(["docker", "ps"], capture_output=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def ensure_image(self) -> bool:
        """Verify that the jarvis-sandbox image is built. If not, builds it."""
        try:
            # Check if image exists
            res = subprocess.run(
                ["docker", "images", "-q", self.image_name],
                capture_output=True,
                text=True,
                check=True
            )
            if res.stdout.strip():
                return True

            # Image does not exist, build it from inline Dockerfile
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
                    capture_output=True,
                    text=True
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
        """Ensure the user's container is active and running."""
        if not self.is_docker_available():
            logger.warning("Docker daemon is unreachable. Falling back to local execution.")
            return False

        if not self.ensure_image():
            logger.warning("Could not build or retrieve Docker image. Falling back to local execution.")
            return False

        # Get user's document workspace dir
        user_dir = get_user_documents_dir()
        abs_user_dir = os.path.abspath(user_dir)

        try:
            # Check container status
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", self.container_name],
                capture_output=True,
                text=True
            )
            status = res.stdout.strip()

            if status == "running":
                return True
            elif status:
                # Container exists but stopped. Start it.
                logger.info(f"Starting stopped sandbox container: {self.container_name}")
                subprocess.run(["docker", "start", self.container_name], check=True)
                return True

            # Container doesn't exist. Run a new one.
            logger.info(f"Creating new sandbox container: {self.container_name} mounting {abs_user_dir}")
            run_cmd = [
                "docker", "run", "-d",
                "--name", self.container_name,
                "-v", f"{abs_user_dir}:/workspace",
                "-w", "/workspace",
                self.image_name,
                "sleep", "infinity"
            ]
            subprocess.run(run_cmd, check=True)
            return True

        except Exception as e:
            logger.error(f"Failed to manage container {self.container_name}: {e}")
            return False

    def stop_container(self) -> bool:
        """Stop and remove the user's container."""
        try:
            subprocess.run(["docker", "stop", self.container_name], capture_output=True)
            subprocess.run(["docker", "rm", self.container_name], capture_output=True)
            logger.info(f"Stopped and removed sandbox container {self.container_name}.")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {self.container_name}: {e}")
            return False

    def execute(self, cmd: list[str]) -> dict:
        """
        Executes a command. Runs inside the Docker container if available,
        otherwise falls back to local subprocess execution inside user's directory.
        """
        user_dir = get_user_documents_dir()
        abs_user_dir = os.path.abspath(user_dir)

        # Attempt to run inside Docker
        if self.start_container():
            docker_cmd = ["docker", "exec", "-w", "/workspace", self.container_name] + cmd
            logger.info(f"Executing command in Docker sandbox: {' '.join(cmd)}")
            try:
                res = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=60)
                return {
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "exit_code": res.returncode,
                    "sandboxed": True,
                    "error": None
                }
            except subprocess.TimeoutExpired:
                logger.error("Command timed out inside Docker sandbox.")
                return {
                    "stdout": "",
                    "stderr": "Execution Timeout (60s exceeded)",
                    "exit_code": 124,
                    "sandboxed": True,
                    "error": "Timeout"
                }
            except Exception as e:
                logger.error(f"Docker execution failed: {e}")
                # Fallback to local
                pass

        # Local Fallback execution
        logger.warning(f"Falling back to local execution for command: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, cwd=abs_user_dir, capture_output=True, text=True, timeout=60)
            return {
                "stdout": res.stdout,
                "stderr": res.stderr + "\n[WARNING: Executed locally outside sandbox (Docker unavailable)]",
                "exit_code": res.returncode,
                "sandboxed": False,
                "error": None
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Execution Timeout (60s exceeded)\n[WARNING: Executed locally outside sandbox (Docker unavailable)]",
                "exit_code": 124,
                "sandboxed": False,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Local execution failed: {str(e)}",
                "exit_code": 1,
                "sandboxed": False,
                "error": str(e)
            }
