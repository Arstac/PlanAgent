"""
CLI entry point for Plan-and-Spawn agent system.
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from plan_spawn.core.orchestrator import Orchestrator
from plan_spawn.config.settings import settings


console = Console()


def print_banner():
    """Print welcome banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║          PLAN-AND-SPAWN AGENT SYSTEM                  ║
    ║          Autonomous Multi-Agent Orchestrator          ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


async def run_interactive_mode():
    """Interactive mode - ask for task and execute."""
    console.print("\n[bold]Interactive Mode[/bold]")
    console.print("[dim]Enter your objective, and the system will plan and execute automatically.[/dim]\n")
    
    objective = Prompt.ask("🎯 What would you like me to do?")
    
    if not objective:
        console.print("[yellow]No objective provided. Exiting.[/yellow]")
        return
    
    # Initialize orchestrator
    orchestrator = Orchestrator()
    
    # Run orchestration
    try:
        state = await orchestrator.run(objective)
        
        if state.status == "completed":
            console.print("\n[bold green]✓ Task completed successfully![/bold green]\n")
            
            # Show all artifacts
            console.print("[bold]Generated Artifacts:[/bold]")
            all_artifacts = orchestrator.list_artifacts()
            for uri in all_artifacts:
                console.print(f"  📄 {uri}")
            
            # Show tool usage
            tool_stats = orchestrator.get_tool_stats()
            if tool_stats:
                console.print("\n[bold]Tool Usage:[/bold]")
                for tool_name, count in sorted(tool_stats.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:
                        console.print(f"  {tool_name}: {count} calls")
        
        else:
            console.print(f"\n[bold red]✗ Task failed with status: {state.status}[/bold red]")
    
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {str(e)}[/bold red]\n")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


async def run_custom_mode(objective: str, **kwargs):
    """
    Custom mode with additional parameters.
    
    Args:
        objective: Task objective
        **kwargs: Additional parameters
    """
    orchestrator = Orchestrator()
    
    try:
        state = await orchestrator.run(objective, **kwargs)
        
        if state.status == "completed":
            console.print("\n[bold green]✓ Execution completed![/bold green]")
            return state
        else:
            console.print(f"\n[bold red]✗ Execution failed: {state.status}[/bold red]")
            return state
    
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {str(e)}[/bold red]")
        raise


def show_help():
    """Show help information."""
    help_text = """
# Plan-and-Spawn Agent System - CLI Help

## Usage

### Article Mode
Generate articles or news content:
```bash
python -m plan_spawn.main article "Topic of the article"
```

Example:
```bash
python -m plan_spawn.main article "The future of quantum computing in 2025"
```

### Interactive Mode
Interactive prompt for any task:
```bash
python -m plan_spawn.main interactive
```

### Custom Mode
Direct objective execution:
```bash
python -m plan_spawn.main run "Your objective here"
```

## Features

- **Autonomous Planning**: AI generates optimal execution plans
- **Specialized Agents**: Research, Writing, Editing, Fact-checking
- **Tool Usage**: Web search, content generation, quality checks
- **Artifact Management**: All outputs saved with logical URIs

## Configuration

Edit `.env` file:
- `ANTHROPIC_API_KEY`: Your Claude API key (required)
- `BRAVE_API_KEY`: For web search (optional)
- `MAX_ITERATIONS_PER_STEP`: Agent autonomy level (default: 15)

## Artifacts

All generated content is saved in `./artifacts/<step_id>/`

View artifacts:
```bash
ls -la artifacts/
```

## Examples

1. **News Article**:
   ```bash
   python -m plan_spawn.main article "Latest developments in AI safety"
   ```

2. **Technical Article**:
   ```bash
   python -m plan_spawn.main article "How neural networks learn: a deep dive"
   ```

3. **Custom Task**:
   ```bash
   python -m plan_spawn.main interactive
   > What would you like me to do? Create a comprehensive guide about starting a podcast
   ```

## Need Help?

Check README.md for more information or visit the documentation.
    """
    console.print(Markdown(help_text))


async def run_article_mode(objective: Optional[str] = None):
    """
    Article generation mode.

    Args:
        objective: Article topic/objective
    """
    if not objective:
        console.print("\n[bold]Article Generation Mode[/bold]\n")
        objective = Prompt.ask("📝 What article would you like to create?")

    if not objective:
        console.print("[yellow]No objective provided. Exiting.[/yellow]")
        return

    # Initialize orchestrator
    orchestrator = Orchestrator()

    # Run orchestration
    try:
        state = await orchestrator.run(objective)

        if state.status == "completed":
            console.print("\n[bold green]🎉 Article generation completed![/bold green]\n")

            # Find final article
            final_artifacts = []
            for step_id in state.completed_steps:
                if step_id in state.artifacts:
                    for artifact_uri in state.artifacts[step_id]:
                        if "article" in artifact_uri.lower() or "final" in artifact_uri.lower():
                            final_artifacts.append(artifact_uri)

            if final_artifacts:
                console.print("[bold]Final Article:[/bold]")
                for uri in final_artifacts:
                    console.print(f"  📄 {uri}")

                # Ask if user wants to view
                if Confirm.ask("\nWould you like to view the article?"):
                    for uri in final_artifacts:
                        content = orchestrator.get_artifact_content(uri)
                        console.print(Panel(
                            Markdown(content[:2000]),  # First 2000 chars
                            title=uri,
                            border_style="green"
                        ))

                        if len(content) > 2000:
                            console.print(f"\n[dim]... (showing first 2000 chars, full article saved to {orchestrator.artifact_store.get_path(uri)})[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {str(e)}[/bold red]\n")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


async def main():
    """Main CLI entry point."""
    print_banner()
    
    # Check if API key is configured
    if not settings.ANTHROPIC_API_KEY:
        console.print("[bold red]❌ ERROR: ANTHROPIC_API_KEY not configured[/bold red]\n")
        console.print("Please set your API key in the .env file:")
        console.print("  ANTHROPIC_API_KEY=your_key_here\n")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        console.print("[yellow]No command specified. Use 'help' for usage information.[/yellow]\n")
        
        # Show quick menu
        console.print("[bold]Quick Start:[/bold]")
        console.print("  1. article <topic>  - Generate an article")
        console.print("  2. interactive      - Interactive mode")
        console.print("  3. help            - Show detailed help\n")
        
        choice = Prompt.ask("Select mode", choices=["1", "2", "3", "exit"], default="2")
        
        if choice == "1":
            await run_article_mode()
        elif choice == "2":
            await run_interactive_mode()
        elif choice == "3":
            show_help()
        else:
            console.print("Goodbye! 👋")
        
        return
    
    command = sys.argv[1].lower()
    
    if command == "article":
        if len(sys.argv) > 2:
            objective = " ".join(sys.argv[2:])
            await run_article_mode(objective)
        else:
            await run_article_mode()
    
    elif command == "interactive":
        await run_interactive_mode()
    
    elif command == "run":
        if len(sys.argv) > 2:
            objective = " ".join(sys.argv[2:])
            await run_custom_mode(objective)
        else:
            console.print("[red]Error: 'run' command requires an objective[/red]")
            console.print("Usage: python -m plan_spawn.main run \"Your objective\"")
    
    elif command == "help" or command == "--help" or command == "-h":
        show_help()
    
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print("Use 'help' for usage information.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user. Goodbye! 👋[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {str(e)}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)