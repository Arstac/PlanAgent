"""
Plan executor - orchestrates step execution with dependency management.
"""
from typing import Dict, List, Optional
from .models import Plan, Step, StepResult, ExecutionState
from .agent_runtime import AgentRuntime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn


class Executor:
    """
    Executes plans by running steps in dependency order.
    Manages execution state and handles failures.
    """
    
    def __init__(self, agent_runtime: AgentRuntime):
        self.runtime = agent_runtime
        self.console = Console()
    
    async def execute_plan(self, plan: Plan) -> ExecutionState:
        """
        Execute a complete plan.
        
        Args:
            plan: Plan to execute
            
        Returns:
            ExecutionState with execution results
        """
        state = ExecutionState(plan_id=plan.plan_id)
        
        self.console.print(f"\n[bold cyan]🚀 Starting execution: {plan.objective}[/bold cyan]")
        self.console.print(f"[dim]Plan ID: {plan.plan_id}[/dim]")
        self.console.print(f"[dim]Total steps: {len(plan.steps)}[/dim]\n")
        
        # Execute steps in dependency order
        execution_order = self._compute_execution_order(plan)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task(
                f"Executing {len(execution_order)} steps...",
                total=len(execution_order)
            )
            
            for step_id in execution_order:
                step = self._get_step(plan, step_id)
                if not step:
                    continue
                
                state.current_step = step_id
                progress.update(task, description=f"Step {step_id}: {step.title}")
                
                # Build context for step
                context = self._build_step_context(plan, step, state)
                
                # Execute step
                self.console.print(f"\n[bold]→ Executing {step_id}: {step.title}[/bold]")
                self.console.print(f"  [dim]Agent: {step.agent_spec.role}[/dim]")
                
                try:
                    result = await self.runtime.execute_step(step, context)
                    
                    # Validate acceptance
                    if result.acceptance_check.passed:
                        state.completed_steps.append(step_id)
                        state.artifacts[step_id] = result.artifacts
                        step.status = "done"
                        
                        self.console.print(f"  [green]✓[/green] Completed in {result.duration_s:.1f}s")
                        self.console.print(f"  [dim]{result.summary}[/dim]")
                        
                        if result.artifacts:
                            self.console.print(f"  [dim]Artifacts: {', '.join(result.artifacts)}[/dim]")
                    else:
                        state.failed_steps.append(step_id)
                        step.status = "error"

                        self.console.print(f"  [red]✗[/red] Failed: {result.summary}")
                        self.console.print(f"  [red]Evidence: {result.acceptance_check.evidence}[/red]")

                        # Print execution log for debugging
                        if result.log:
                            self.console.print(f"  [yellow]Execution log:[/yellow]")
                            for log_entry in result.log[-10:]:  # Last 10 entries
                                self.console.print(f"    [dim]{log_entry}[/dim]")

                        # Stop on critical failure
                        state.status = "failed"
                        break
                
                except Exception as e:
                    state.failed_steps.append(step_id)
                    step.status = "error"
                    self.console.print(f"  [red]✗[/red] Error: {str(e)}")
                    
                    state.status = "failed"
                    break
                
                progress.update(task, advance=1)
        
        # Finalize state
        if state.status == "running" and len(state.completed_steps) == len(plan.steps):
            state.status = "completed"
        
        import datetime
        state.end_time = datetime.datetime.now()
        
        self._print_summary(state, plan)
        
        return state
    
    def _compute_execution_order(self, plan: Plan) -> List[str]:
        """
        Compute execution order respecting dependencies.
        Uses topological sort.
        
        Args:
            plan: Plan with steps
            
        Returns:
            List of step IDs in execution order
        """
        # Build dependency graph
        in_degree = {step.id: len(step.depends_on) for step in plan.steps}
        adjacency = {step.id: [] for step in plan.steps}
        
        for step in plan.steps:
            for dep in step.depends_on:
                adjacency[dep].append(step.id)
        
        # Topological sort (Kahn's algorithm)
        queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return order
    
    def _get_step(self, plan: Plan, step_id: str) -> Optional[Step]:
        """Get step by ID."""
        for step in plan.steps:
            if step.id == step_id:
                return step
        return None
    
    def _build_step_context(
        self, 
        plan: Plan, 
        step: Step,
        state: ExecutionState
    ) -> Dict:
        """
        Build execution context for a step.
        
        Includes:
        - Original objective
        - Input refs from dependencies
        - Inline context from agent_spec
        """
        context = {
            "objective": plan.objective,
            "step_id": step.id,
            "step_title": step.title
        }
        
        # Add input refs from io spec
        if step.agent_spec.io.input_refs:
            context["input_refs"] = step.agent_spec.io.input_refs
        
        # Add artifacts from completed dependencies
        dependency_artifacts = []
        for dep_id in step.depends_on:
            if dep_id in state.artifacts:
                dependency_artifacts.extend(state.artifacts[dep_id])
        
        if dependency_artifacts:
            context["dependency_artifacts"] = dependency_artifacts
        
        # Add inline context
        if step.agent_spec.io.inline_context:
            context.update(step.agent_spec.io.inline_context)
        
        return context
    
    def _print_summary(self, state: ExecutionState, plan: Plan):
        """Print execution summary."""
        self.console.print("\n" + "="*60)
        
        if state.status == "completed":
            self.console.print("[bold green]✓ Execution completed successfully![/bold green]")
        else:
            self.console.print("[bold red]✗ Execution failed[/bold red]")
        
        self.console.print(f"\nCompleted steps: {len(state.completed_steps)}/{len(plan.steps)}")
        
        if state.failed_steps:
            self.console.print(f"[red]Failed steps: {', '.join(state.failed_steps)}[/red]")
        
        # Show final artifacts
        self.console.print("\n[bold]Generated Artifacts:[/bold]")
        for step_id, artifacts in state.artifacts.items():
            step = self._get_step(plan, step_id)
            if step:
                self.console.print(f"  {step_id} ({step.title}):")
                for artifact in artifacts:
                    self.console.print(f"    • {artifact}")
        
        duration = (state.end_time - state.start_time).total_seconds()
        self.console.print(f"\n[dim]Total duration: {duration:.1f}s[/dim]")
        self.console.print("="*60 + "\n")
