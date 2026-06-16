"""
JARVIS — CLI Entry Point
Interactive command-line interface for the multi-agent system.
"""

from backend.core.registry import AgentRegistry
from backend.core.orchestrator import Orchestrator
from backend.core.memory import ConversationMemory
from backend.agents import ALL_AGENTS
from backend.logger import get_logger

logger = get_logger("jarvis")

# ── Banner ──────────────────────────────────────────────────────────
BANNER = """
\033[96m╔══════════════════════════════════════════════════════════╗
║                                                          ║
║        ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗           ║
║        ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝           ║
║        ██║███████║██████╔╝██║   ██║██║███████╗           ║
║   ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║           ║
║   ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║           ║
║    ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝           ║
║                                                          ║
║         \033[93mAutonomous AI Operating System\033[96m                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝\033[0m
"""


def main():
    print(BANNER)

    # ── Initialize Registry ─────────────────────────────────────
    registry = AgentRegistry()
    for AgentClass in ALL_AGENTS:
        registry.register(AgentClass())

    logger.info(f"JARVIS initialized with {len(registry)} agents.")
    print(f"\n\033[92m  ✓ {len(registry)} agents online\033[0m")

    # Show registered agents
    print("\n\033[90m  Available agents:\033[0m")
    for agent_info in registry.list_agents():
        print(f"    \033[96m• {agent_info['name']}\033[0m — {agent_info['description']}")

    print(f"\n\033[90m  Type 'quit' to exit | 'agents' to list agents | 'history' for log | 'clear' to reset\033[0m\n")

    # ── Initialize Orchestrator ─────────────────────────────────
    orchestrator = Orchestrator(registry)
    session_id = "cli_session"
    memory = ConversationMemory(session_id)

    # ── Interactive Loop ────────────────────────────────────────
    while True:
        try:
            user_input = input("\033[95m  You → \033[0m").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print("\n\033[93m  JARVIS shutting down. Goodbye! 👋\033[0m\n")
                break

            if user_input.lower() == "agents":
                print("\n\033[90m  Registered agents:\033[0m")
                for agent_info in registry.list_agents():
                    print(f"    \033[96m• {agent_info['name']}\033[0m — {agent_info['description']}")
                print()
                continue

            if user_input.lower() == "history":
                print("\n\033[90m  Conversation History:\033[0m")
                history = memory.get_history()
                if not history:
                    print("    (Empty)")
                for msg in history:
                    role_color = "\033[95m" if msg["role"] == "user" else "\033[92m"
                    role_name = "You" if msg["role"] == "user" else "JARVIS"
                    print(f"    {role_color}{role_name}:\033[0m {msg['content']}")
                print()
                continue

            if user_input.lower() == "clear":
                memory.clear()
                print("\n\033[93m  Conversation history cleared! \033[0m\n")
                continue

            # Run the orchestrator
            print()
            result = orchestrator.run(user_input, session_id=session_id)
            response = result["response"]
            agents_used = result["agents_used"]
            if agents_used:
                print(f"\033[90m  [Agents used: {', '.join(agents_used)}]\033[0m")
            print(f"\n\033[92m  JARVIS →\033[0m {response}\n")

        except KeyboardInterrupt:
            print("\n\n\033[93m  JARVIS interrupted. Goodbye! 👋\033[0m\n")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\n\033[91m  Error: {e}\033[0m\n")


if __name__ == "__main__":
    main()
