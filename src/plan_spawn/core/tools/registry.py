"""
Tool registry for managing available tools.
Tools are registered and can be invoked by agents.
"""
from typing import Callable, Dict, Any, Optional
from pydantic import BaseModel
from dataclasses import dataclass


@dataclass
class Tool:
    """Tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    function: Callable
    allowed_agents: list[str] = None  # None = all agents
    
    def __post_init__(self):
        if self.allowed_agents is None:
            self.allowed_agents = ["*"]
    
    def to_anthropic_schema(self) -> dict:
        """Convert to Anthropic tool schema format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
        }


class ToolRegistry:
    """
    Central registry for all available tools.
    Manages tool registration and retrieval.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._usage_stats: Dict[str, int] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a new tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        
        self._tools[tool.name] = tool
        self._usage_stats[tool.name] = 0
    
    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._tools.get(name)
    
    def list_all(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def list_for_agent(self, agent_role: str, tool_names: list[str] = None) -> list[Tool]:
        """
        Get tools available for a specific agent.
        
        Args:
            agent_role: Role of the agent
            tool_names: Optional list of specific tool names to filter
            
        Returns:
            List of available tools
        """
        available = []
        
        for tool in self._tools.values():
            # Check if tool_names filter is specified
            if tool_names and tool.name not in tool_names:
                continue
            
            # Check if agent is allowed to use this tool
            if "*" in tool.allowed_agents or agent_role in tool.allowed_agents:
                available.append(tool)
        
        return available
    
    def get_schemas_for_agent(
        self, 
        agent_role: str, 
        tool_names: list[str] = None
    ) -> list[dict]:
        """Get Anthropic-compatible tool schemas for an agent."""
        tools = self.list_for_agent(agent_role, tool_names)
        return [tool.to_anthropic_schema() for tool in tools]
    
    def track_usage(self, tool_name: str):
        """Track tool usage for statistics."""
        if tool_name in self._usage_stats:
            self._usage_stats[tool_name] += 1
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics for all tools."""
        return self._usage_stats.copy()
    
    def exists(self, name: str) -> bool:
        """Check if tool exists."""
        return name in self._tools


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    allowed_agents: list[str] = None
):
    """
    Decorator to register a function as a tool.
    
    Usage:
        @register_tool(
            name="my_tool",
            description="Does something",
            parameters={...}
        )
        async def my_tool(arg1: str, arg2: int):
            ...
    """
    def decorator(func: Callable):
        registry = get_registry()
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=func,
            allowed_agents=allowed_agents
        )
        registry.register(tool)
        return func
    
    return decorator
