"""
JARVIS — Agent Registry
The heart of the plugin system. Agents register themselves here,
and the planner auto-discovers available targets.
"""

from backend.logger import get_logger
from backend.agents.base import BaseAgent
import os
import sys
import importlib
import pkgutil
import inspect
from backend.config import PROJECT_ROOT

logger = get_logger("registry")


class AgentRegistry:
    """
    Central registry for all JARVIS agents.

    Usage:
        registry = AgentRegistry()
        registry.register(SearchAgent())
        registry.register(CodeAgent())

        # Auto-generate planner targets
        targets = registry.get_target_descriptions()

        # Execute a specific agent
        result = registry.run("search", "latest AI news")
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        if not agent.name:
            raise ValueError(f"Agent {agent.__class__.__name__} must have a 'name' attribute.")
        if agent.name in self._agents:
            logger.warning(f"Agent '{agent.name}' is already registered. Overwriting.")
        self._agents[agent.name] = agent
        agent.registry = self
        logger.info(f"Registered agent: {agent.name} -- {agent.description}")

    def get(self, name: str) -> BaseAgent | None:
        """Get an agent by name (checks registered agents, then custom agents)."""
        if name in self._agents:
            return self._agents[name]
            
        # Check custom agent configurations dynamically
        from backend.config import current_user_id, load_profile_config
        user_id = current_user_id.get()
        if user_id:
            config = load_profile_config(user_id)
            custom_agents = config.get("custom_agents", [])
            for ca in custom_agents:
                if ca["name"] == name:
                    return CustomAgentWrapper(
                        name=ca["name"],
                        description=ca["description"],
                        system_prompt=ca["system_prompt"],
                        model=ca["model"],
                        temp=ca["temperature"],
                        base_agent_name=ca.get("base_agent"),
                        registry=self
                    )
        return None

    def run(self, name: str, query: str) -> str:
        """Run a specific agent by name."""
        agent = self.get(name)
        if not agent:
            return f"Error: No agent registered with name '{name}'"
        return agent.run(query)

    def list_agents(self) -> list[dict]:
        """Return a list of all registered agents with their metadata."""
        return [
            {"name": a.name, "description": a.description}
            for a in self._agents.values()
        ]

    def get_target_names(self) -> list[str]:
        """Return all registered and custom agent names (for planner target validation)."""
        names = list(self._agents.keys())
        from backend.config import current_user_id, load_profile_config
        user_id = current_user_id.get()
        if user_id:
            config = load_profile_config(user_id)
            custom_agents = config.get("custom_agents", [])
            for ca in custom_agents:
                if ca["name"] not in names:
                    names.append(ca["name"])
        return names

    def get_target_descriptions(self) -> str:
        """
        Auto-generate the planner prompt section describing available agents.
        This is injected into the planner's system prompt dynamically.
        """
        lines = []
        for name, agent in self._agents.items():
            lines.append(f"- '{name}': {agent.description}")
            
        # Add custom agents
        from backend.config import current_user_id, load_profile_config
        user_id = current_user_id.get()
        if user_id:
            config = load_profile_config(user_id)
            custom_agents = config.get("custom_agents", [])
            for ca in custom_agents:
                lines.append(f"- '{ca['name']}': {ca['description']}")
        return "\n".join(lines)

    def scan_and_register_agents(self) -> None:
        """
        Dynamically scan the backend.agents directory and register any new subclasses of BaseAgent.
        """
        logger.info("Scanning for new agents in backend.agents...")
        agents_dir = os.path.join(PROJECT_ROOT, "backend", "agents")
        
        # We need to ensure we can reload if it's already in sys.modules, but for newly created ones, 
        # importlib.import_module is sufficient.
        for _, module_name, _ in pkgutil.iter_modules([agents_dir]):
            if module_name in ("base", "__init__", "team_base"):
                continue
            try:
                full_module_name = f"backend.agents.{module_name}"
                # If it's already loaded, we might want to reload it, but `pkgutil` finds it.
                # Just import or get the module.
                if full_module_name in sys.modules:
                    module = sys.modules[full_module_name]
                    importlib.reload(module)
                else:
                    module = importlib.import_module(full_module_name)
                    
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseAgent) and obj is not BaseAgent and obj.__module__ == module.__name__:
                        # Instantiate and register if not already registered (or overwrite if changed)
                        agent_instance = obj()
                        if agent_instance.name not in self._agents:
                            self.register(agent_instance)
                            
            except Exception as e:
                logger.error(f"Error scanning/registering module {module_name}: {e}")

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        return name in self._agents


class CustomAgentWrapper(BaseAgent):
    """
    Wrapper for dynamically configured custom agents.
    Inherits tools from a base agent or runs direct LLM queries.
    """
    def __init__(self, name: str, description: str, system_prompt: str, model: str, temp: float, base_agent_name: str | None = None, registry: AgentRegistry | None = None):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.model = model
        self.temp = float(temp)
        self.base_agent_name = base_agent_name
        self.registry = registry

    def run(self, query: str) -> str:
        # Load custom LLM and system prompt dynamically to support overrides
        llm_instance = self.get_llm(default_model=self.model, default_temp=self.temp)
        sys_prompt = self.get_system_prompt(self.system_prompt)

        tools = []
        if self.base_agent_name:
            if self.base_agent_name == "code":
                # Set up dynamic sandbox tools exactly like CodeAgent
                from backend.core.sandbox import DockerSandboxManager
                from backend.config import current_user_id
                from langchain_core.tools import tool
                import os

                user_id = current_user_id.get() or "default"
                sandbox = DockerSandboxManager(user_id)

                @tool
                def execute_python(code: str) -> str:
                    """Executes arbitrary Python code in the sandbox environment. Returns stdout, stderr, or execution errors."""
                    import uuid
                    from backend.config import get_user_documents_dir
                    
                    run_filename = f"_run_{uuid.uuid4().hex[:8]}.py"
                    workspace_dir = get_user_documents_dir()
                    temp_run_path = os.path.join(workspace_dir, run_filename)
                    
                    try:
                        with open(temp_run_path, "w", encoding="utf-8") as f:
                            f.write(code)
                        res = sandbox.execute(["python", run_filename])
                        if os.path.exists(temp_run_path):
                            os.remove(temp_run_path)
                        output = ""
                        if res["stdout"]:
                            output += f"Stdout:\n{res['stdout']}\n"
                        if res["stderr"]:
                            output += f"Stderr:\n{res['stderr']}\n"
                        if res["exit_code"] != 0:
                            output += f"Exit Code: {res['exit_code']}\n"
                        if not res["sandboxed"]:
                            output += "\n[Note: Executed in host fallback environment]"
                        return output if output else "Code executed successfully with no output."
                    except Exception as e:
                        if os.path.exists(temp_run_path):
                            os.remove(temp_run_path)
                        return f"Error executing python code: {str(e)}"

                @tool
                def write_file_sandbox(path: str, content: str) -> str:
                    """Writes content to a file at the specified path in the sandbox workspace."""
                    from backend.config import get_user_documents_dir
                    workspace_dir = get_user_documents_dir()
                    target_path = os.path.abspath(os.path.join(workspace_dir, path))
                    if not target_path.startswith(os.path.abspath(workspace_dir)):
                        return "Failed: Path is outside the sandbox workspace."
                    try:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        return f"Successfully wrote to file '{path}' in sandbox."
                    except Exception as e:
                        return f"Failed to write file: {str(e)}"

                @tool
                def read_file_sandbox(path: str) -> str:
                    """Reads the contents of a file at the specified path from the sandbox workspace."""
                    from backend.config import get_user_documents_dir
                    workspace_dir = get_user_documents_dir()
                    target_path = os.path.abspath(os.path.join(workspace_dir, path))
                    if not target_path.startswith(os.path.abspath(workspace_dir)):
                        return "Failed: Path is outside the sandbox workspace."
                    try:
                        if not os.path.exists(target_path):
                            return f"Failed: File '{path}' does not exist."
                        with open(target_path, "r", encoding="utf-8") as f:
                            return f.read()
                    except Exception as e:
                        return f"Failed to read file: {str(e)}"

                @tool
                def list_dir_sandbox(path: str = ".") -> str:
                    """Lists the files and directories inside the sandbox workspace at the specified path."""
                    from backend.config import get_user_documents_dir
                    workspace_dir = get_user_documents_dir()
                    target_path = os.path.abspath(os.path.join(workspace_dir, path))
                    if not target_path.startswith(os.path.abspath(workspace_dir)):
                        return "Failed: Path is outside the sandbox workspace."
                    try:
                        if not os.path.exists(target_path):
                            return f"Failed: Directory '{path}' does not exist."
                        files = os.listdir(target_path)
                        result = []
                        for file in files:
                            full_f = os.path.join(target_path, file)
                            type_str = "DIR" if os.path.isdir(full_f) else "FILE"
                            result.append(f"- [{type_str}] {file}")
                        return "\n".join(result) if result else "Directory is empty."
                    except Exception as e:
                        return f"Failed to list directory: {str(e)}"

                tools = [execute_python, write_file_sandbox, read_file_sandbox, list_dir_sandbox]
            else:
                base_agent = None
                if self.registry and hasattr(self.registry, "_agents"):
                    base_agent = self.registry._agents.get(self.base_agent_name)
                if base_agent and hasattr(base_agent, "tools"):
                    tools = base_agent.tools

        if tools:
            # Run with tool-calling agent executor
            try:
                from langchain.agents import AgentExecutor, create_tool_calling_agent
            except ImportError:
                from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
            from langchain_core.prompts import ChatPromptTemplate
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", sys_prompt),
                ("human", "{query}"),
                ("placeholder", "{agent_scratchpad}"),
            ])
            
            agent = create_tool_calling_agent(llm=llm_instance, tools=tools, prompt=prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=5,
                handle_parsing_errors=True
            )
            try:
                response = executor.invoke({"query": query})
                return response.get("output", str(response))
            except Exception as e:
                return f"Agent execution error: {str(e)}"
        else:
            # Run direct ChatGroq query
            from langchain_core.messages import SystemMessage, HumanMessage
            try:
                messages = [
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content=query)
                ]
                response = llm_instance.invoke(messages)
                return response.content
            except Exception as e:
                return f"LLM error: {str(e)}"

