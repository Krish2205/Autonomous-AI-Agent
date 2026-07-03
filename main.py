"""
JARVIS — Entry Point
Thin wrapper that calls the backend CLI or exposes the API app.
"""

from backend.main import main
from backend.api.server import app

if __name__ == "__main__":
    main()

