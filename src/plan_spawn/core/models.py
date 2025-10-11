"""
Data models for Plan-and-Spawn system using Pydantic.
All models follow the specification from the system document.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional
from datetime import datetime


# ============================================================================
# INPUT MODELS
# ============================================================================

class TaskRequest(BaseModel):
    """External input request to the orchestrator."""
    objective: str = Field(..., description="Main objective/task to accomplish")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Optional constraints")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    available_tools: List[str] = Field(
        default_factory=lambda: [
            "web_search", "web_fetch", "llm_call", 
            "write_artifact", "read_artifact", "quality_check"
        ],
        description="Whitelist of available tools"
    )
    policies: Dict[str, Any] = Field(default_factory=dict, description="Execution policies")


# ============================================================================
# ACCEPTANCE CRITERIA
# ============================================================================

class Acceptance(BaseModel):
    """Acceptance criteria for step validation."""
    model_config = {"protected_namespaces": ()}  # Allow 'schema' field
    
    type: Literal["schema", "file_exists", "text_checks", "numeric_bounds", "llm_review"]
    path_ref: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    columns: Optional[List[str]] = None
    min_rows: Optional[int] = None
    must_contain: Optional[List[str]] = None
    min_chars: Optional[int] = None
    bounds: Optional[Dict[str, Any]] = None
    rubric: Optional[List[str]] = None
    threshold: Optional[str] = None


# ============================================================================
# AGENT SPECIFICATION
# ============================================================================

class IOSpec(BaseModel):
    """Input/Output specification for an agent."""
    input_refs: List[str] = Field(default_factory=list, description="Artifact URIs from previous steps")
    inline_context: Dict[str, Any] = Field(default_factory=dict, description="Inline context data")
    output_decl: List[Dict[str, str]] = Field(default_factory=list, description="Expected outputs")


class PolicySpec(BaseModel):
    """Execution policies for an agent."""
    json_mode: bool = True
    disallow_network: bool = False
    timeout_s: int = 180
    max_tokens: Optional[int] = None


class StopConditions(BaseModel):
    """Stop conditions for agent execution."""
    max_calls: int = 10
    accept_on: Literal["acceptance_pass", "explicit_result"] = "acceptance_pass"


class AgentSpec(BaseModel):
    """Complete specification for an ephemeral agent."""
    role: str = Field(..., description="Agent archetype (e.g., ResearchAgent, WriterAgent)")
    system_prompt: str = Field(..., description="System prompt for the agent")
    tools: List[str] = Field(..., description="Allowed tools for this agent")
    io: IOSpec
    policies: PolicySpec = Field(default_factory=PolicySpec)
    stop_conditions: StopConditions = Field(default_factory=StopConditions)
    telemetry: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# PLAN STRUCTURE
# ============================================================================

class Step(BaseModel):
    """A single step in the execution plan."""
    id: str = Field(..., description="Unique step identifier (e.g., s1, s2)")
    title: str = Field(..., description="Human-readable step title")
    depends_on: List[str] = Field(default_factory=list, description="IDs of prerequisite steps")
    agent_spec: AgentSpec
    acceptance: Acceptance
    status: Literal["pending", "running", "done", "error"] = "pending"


class Plan(BaseModel):
    """Complete execution plan."""
    plan_id: str = Field(..., description="Unique plan identifier")
    objective: str = Field(..., description="Original objective")
    assumptions: List[str] = Field(default_factory=list, description="Plan assumptions")
    steps: List[Step] = Field(..., description="Ordered list of steps")
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# OUTPUT MODELS
# ============================================================================

class PlanResponse(BaseModel):
    """Response containing a generated plan."""
    type: Literal["plan"] = "plan"
    plan: Plan


class AcceptanceCheck(BaseModel):
    """Result of acceptance criteria validation."""
    passed: bool
    evidence: str
    details: Dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Result of step execution."""
    type: Literal["step_result"] = "step_result"
    step_id: str
    status: Literal["ok", "fail"]
    artifacts: List[str] = Field(default_factory=list, description="Generated artifact URIs")
    summary: str
    log: List[str] = Field(default_factory=list, description="Execution log")
    acceptance_check: AcceptanceCheck
    duration_s: Optional[float] = None


class NeedClarification(BaseModel):
    """Request for clarification from user."""
    type: Literal["need_clarification"] = "need_clarification"
    step_id: Optional[str] = None
    question: str
    details: Dict[str, Any] = Field(default_factory=dict)


class PolicyBlock(BaseModel):
    """Blocked by policy violation."""
    type: Literal["policy_block"] = "policy_block"
    step_id: Optional[str] = None
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class Replan(BaseModel):
    """Request to modify the plan."""
    type: Literal["replan"] = "replan"
    reason: str
    details: Dict[str, Any] = Field(
        description="Contains insert_after, new_steps, remove_steps"
    )


# ============================================================================
# TOOL MODELS
# ============================================================================

class ToolCall(BaseModel):
    """Tool invocation request from agent."""
    name: str
    args: Dict[str, Any]


class ToolResult(BaseModel):
    """Result from tool execution."""
    status: Literal["success", "error"]
    result: Any = None
    error: Optional[str] = None


# ============================================================================
# EXECUTION STATE
# ============================================================================

class ExecutionState(BaseModel):
    """Overall execution state tracking."""
    plan_id: str
    current_step: Optional[str] = None
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)
    artifacts: Dict[str, List[str]] = Field(default_factory=dict)  # step_id -> artifact URIs
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: Literal["running", "completed", "failed", "paused"] = "running"