"""
JARVIS — Agents Package
Import and register all agents dynamically.
"""

import os
import sys
import importlib
import pkgutil
import inspect

from backend.agents.base import BaseAgent

# All available agent classes (dynamically populated)
ALL_AGENTS = []
__all__ = ["ALL_AGENTS"]

# Dynamically discover and register all BaseAgent classes in this directory
package_dir = os.path.dirname(os.path.abspath(__file__))

for _, module_name, _ in pkgutil.iter_modules([package_dir]):
    if module_name in ("base", "__init__"):
        continue
    try:
        # Import the module
        module = importlib.import_module(f"backend.agents.{module_name}")
        # Search for subclasses of BaseAgent
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseAgent) and obj is not BaseAgent:
                if obj not in ALL_AGENTS:
                    ALL_AGENTS.append(obj)
                    # Add to globals and export so it can be imported as "from backend.agents import SearchAgent"
                    globals()[name] = obj
                    if name not in __all__:
                        __all__.append(name)
    except Exception as e:
        # Print to stderr but don't crash so other agents still load
        print(f"Error loading agent module '{module_name}': {e}", file=sys.stderr)
