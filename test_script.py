"""
Quick test script to verify the system is working.
Tests individual components before running the full orchestration.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from plan_spawn.config.settings import settings
from plan_spawn.core.storage.artifacts import ArtifactStore
from plan_spawn.core.tools.registry import get_registry
from plan_spawn.core.tools import web_tools, file_tools, llm_tools
from plan_spawn.core.models import TaskRequest
from plan_spawn.core.planner import Planner
from rich.console import Console

console = Console()


def test_configuration():
    """Test configuration loading."""
    console.print("\n[bold]Testing Configuration...[/bold]")
    
    try:
        assert settings.ANTHROPIC_API_KEY, "API key not configured"
        assert settings.ARTIFACTS_PATH.exists(), "Artifacts path doesn't exist"
        console.print("[green]✓[/green] Configuration OK")
        return True
    except AssertionError as e:
        console.print(f"[red]✗[/red] Configuration failed: {e}")
        return False


def test_artifact_store():
    """Test artifact storage."""
    console.print("\n[bold]Testing Artifact Store...[/bold]")
    
    try:
        store = ArtifactStore("./artifacts_test")
        
        # Test save
        uri = store.save("test_step", "test.txt", "Hello World", "text")
        assert uri == "artifact://test_step/test.txt"
        
        # Test load
        content = store.load(uri)
        assert content == "Hello World"
        
        # Test exists
        assert store.exists(uri)
        
        # Cleanup
        store.cleanup_step("test_step")
        
        console.print("[green]✓[/green] Artifact Store OK")
        return True
    except Exception as e:
        console.print(f"[red]✗[/red] Artifact Store failed: {e}")
        return False


def test_tool_registry():
    """Test tool registry."""
    console.print("\n[bold]Testing Tool Registry...[/bold]")
    
    try:
        registry = get_registry()
        
        # Check tools are registered
        tools = registry.list_all()
        assert len(tools) > 0, "No tools registered"
        
        tool_names = [t.name for t in tools]
        assert "web_search" in tool_names
        assert "write_artifact" in tool_names
        assert "llm_call" in tool_names
        
        console.print(f"[green]✓[/green] Tool Registry OK ({len(tools)} tools registered)")
        console.print(f"[dim]Tools: {', '.join(tool_names)}[/dim]")
        return True
    except AssertionError as e:
        console.print(f"[red]✗[/red] Tool Registry failed: {e}")
        return False


async def test_planner():
    """Test plan generation."""
    console.print("\n[bold]Testing Planner...[/bold]")
    
    try:
        planner = Planner()
        
        task = TaskRequest(
            objective="Write a short article about artificial intelligence",
            available_tools=["web_search", "write_artifact", "llm_call"]
        )
        
        console.print("[dim]Generating test plan...[/dim]")
        plan = await planner.create_plan(task)
        
        assert plan is not None, "Plan is None"
        assert len(plan.steps) > 0, "Plan has no steps"
        assert plan.objective == task.objective
        
        # Validate plan
        is_valid, issues = planner.validate_plan(plan)
        if not is_valid:
            console.print(f"[yellow]⚠[/yellow] Plan validation warnings:")
            for issue in issues:
                console.print(f"  • {issue}")
        
        console.print(f"[green]✓[/green] Planner OK (generated {len(plan.steps)} steps)")
        
        # Show plan structure
        console.print("\n[dim]Generated plan:[/dim]")
        for step in plan.steps:
            console.print(f"  {step.id}: {step.title}")
            console.print(f"    [dim]Agent: {step.agent_spec.role}[/dim]")
        
        return True
    except Exception as e:
        console.print(f"[red]✗[/red] Planner failed: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False


async def test_web_tools():
    """Test web tools (basic)."""
    console.print("\n[bold]Testing Web Tools...[/bold]")
    
    try:
        # Test web_search (will use fallback if no API key)
        result = await web_tools.web_search("test query", max_results=3)
        assert result is not None
        assert "results" in result
        
        console.print("[green]✓[/green] Web Tools OK")
        if "note" in result:
            console.print(f"[dim]{result['note']}[/dim]")
        return True
    except Exception as e:
        console.print(f"[red]✗[/red] Web Tools failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    console.print("\n" + "="*60)
    console.print("[bold cyan]PLAN-AND-SPAWN SYSTEM - COMPONENT TESTS[/bold cyan]")
    console.print("="*60)
    
    results = {}
    
    # Synchronous tests
    results["configuration"] = test_configuration()
    results["artifact_store"] = test_artifact_store()
    results["tool_registry"] = test_tool_registry()
    
    # Asynchronous tests
    results["web_tools"] = await test_web_tools()
    results["planner"] = await test_planner()
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold]Test Summary[/bold]")
    console.print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[green]✓ PASS[/green]" if result else "[red]✗ FAIL[/red]"
        console.print(f"{status} - {test_name}")
    
    console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("\n[bold green]🎉 All tests passed! System is ready.[/bold green]")
        console.print("\nYou can now run:")
        console.print("  python -m plan_spawn.main article \"Your topic\"")
    else:
        console.print("\n[bold yellow]⚠ Some tests failed. Please check the errors above.[/bold yellow]")
    
    console.print("")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Test suite error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
