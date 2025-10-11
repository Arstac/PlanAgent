"""
Main orchestrator - coordinates planner, executor, and tools.
"""
from .models import TaskRequest, ExecutionState
from .planner import Planner
from .executor import Executor
from .agent_runtime import AgentRuntime
from .tools.registry import get_registry
from .storage.artifacts import ArtifactStore
from ..config.settings import settings
from rich.console import Console


class Orchestrator:
    """
    Main orchestrator that coordinates the entire Plan-and-Spawn system.
    
    Workflow:
    1. Receive TaskRequest
    2. Generate Plan using Planner
    3. Execute Plan using Executor
    4. Return ExecutionState
    """
    
    def __init__(self):
        self.console = Console()
        
        # Initialize components
        self.artifact_store = ArtifactStore(str(settings.ARTIFACTS_PATH))
        self.tool_registry = get_registry()
        self._register_all_tools()
        
        self.planner = Planner()
        self.agent_runtime = AgentRuntime(
            tool_registry=self.tool_registry,
            artifact_store=self.artifact_store
        )
        self.executor = Executor(self.agent_runtime)
    
    def _register_all_tools(self):
        """Register all available tools."""
        # Import tool modules to trigger @register_tool decorators
        from .tools import web_tools, file_tools, llm_tools
        
        # Tools are auto-registered via decorators
        self.console.print(f"[dim]Registered {len(self.tool_registry.list_all())} tools[/dim]")
    
    async def run(self, objective: str, **kwargs) -> ExecutionState:
        """
        Run the complete orchestration for an objective.
        
        Args:
            objective: Main task objective
            **kwargs: Additional task parameters (constraints, context, etc.)
            
        Returns:
            ExecutionState with execution results
        """
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]PLAN-AND-SPAWN ORCHESTRATOR[/bold cyan]")
        self.console.print("="*60)
        
        # Create task request
        task = TaskRequest(
            objective=objective,
            constraints=kwargs.get("constraints", {}),
            context=kwargs.get("context", {}),
            available_tools=kwargs.get("available_tools", [
                "web_search", "web_fetch", "llm_call",
                "write_artifact", "read_artifact", "list_artifacts",
                "quality_check", "fact_verify"
            ]),
            policies=kwargs.get("policies", {})
        )
        
        self.console.print(f"\n[bold]Objective:[/bold] {objective}\n")
        
        # Step 1: Generate plan
        self.console.print("[bold yellow]📋 Phase 1: Planning[/bold yellow]")
        self.console.print("[dim]Generating execution plan...[/dim]\n")
        
        try:
            plan = await self.planner.create_plan(task)
            
            # Validate plan
            is_valid, issues = self.planner.validate_plan(plan)
            if not is_valid:
                self.console.print("[bold red]Plan validation failed:[/bold red]")
                for issue in issues:
                    self.console.print(f"  • {issue}")
                raise ValueError("Invalid plan generated")
            
            self.console.print(f"[green]✓[/green] Plan generated: {len(plan.steps)} steps")
            
            # Display plan
            self.console.print("\n[bold]Execution Plan:[/bold]")
            for step in plan.steps:
                deps = f" (depends on: {', '.join(step.depends_on)})" if step.depends_on else ""
                self.console.print(f"  {step.id}. {step.title}{deps}")
                self.console.print(f"     [dim]→ {step.agent_spec.role} | tools: {', '.join(step.agent_spec.tools[:3])}{'...' if len(step.agent_spec.tools) > 3 else ''}[/dim]")
        
        except Exception as e:
            self.console.print(f"[bold red]✗ Planning failed: {str(e)}[/bold red]")
            raise
        
        # Step 2: Execute plan
        self.console.print("\n[bold yellow]⚡ Phase 2: Execution[/bold yellow]")
        
        try:
            state = await self.executor.execute_plan(plan)
            return state
        
        except Exception as e:
            self.console.print(f"[bold red]✗ Execution failed: {str(e)}[/bold red]")
            raise
    
    def get_artifact_content(self, uri: str) -> str:
        """
        Retrieve content of an artifact.
        
        Args:
            uri: Artifact URI
            
        Returns:
            Artifact content as string
        """
        return self.artifact_store.load(uri)
    
    def list_artifacts(self, step_id: str = None) -> list[str]:
        """
        List artifacts for a step or all artifacts.
        
        Args:
            step_id: Optional step ID filter
            
        Returns:
            List of artifact URIs
        """
        if step_id:
            return self.artifact_store.list_artifacts(step_id)
        else:
            # List all artifacts
            all_artifacts = []
            for step_dir in self.artifact_store.base_path.iterdir():
                if step_dir.is_dir() and not step_dir.name.startswith("_"):
                    all_artifacts.extend(self.artifact_store.list_artifacts(step_dir.name))
            return all_artifacts
    
    def get_tool_stats(self) -> dict:
        """Get tool usage statistics."""
        return self.tool_registry.get_usage_stats()
