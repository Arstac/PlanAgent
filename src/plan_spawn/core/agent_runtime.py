"""
Agent runtime for executing individual steps.
Creates ephemeral agents that can use tools iteratively.
"""
import json
import time
from typing import Dict, Any, Optional
from anthropic import Anthropic
from .models import Step, StepResult, AcceptanceCheck
from .tools.registry import ToolRegistry
from .storage.artifacts import ArtifactStore
from ..config.settings import settings


class AgentRuntime:
    """
    Executes individual steps by spawning ephemeral agents.
    Each agent can make multiple tool calls iteratively until completion.
    """
    
    def __init__(
        self, 
        api_key: str = None,
        tool_registry: ToolRegistry = None,
        artifact_store: ArtifactStore = None
    ):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.client = Anthropic(api_key=self.api_key)
        self.model = settings.CLAUDE_MODEL
        self.tools = tool_registry
        self.artifacts = artifact_store
    
    async def execute_step(self, step: Step, context: Dict[str, Any]) -> StepResult:
        """
        Execute a single step by creating an ephemeral agent.
        
        The agent can:
        - Make multiple tool calls iteratively
        - Access artifacts from previous steps
        - Self-validate against acceptance criteria
        - Request replan if needed
        
        Args:
            step: Step specification
            context: Execution context (objective, input_refs, etc.)
            
        Returns:
            StepResult with status and artifacts
        """
        start_time = time.time()
        
        # Build initial message
        messages = [
            {
                "role": "user",
                "content": json.dumps({
                    "type": "execute_step",
                    "step_id": step.id,
                    "context": context
                }, ensure_ascii=False)
            }
        ]
        
        # Get tool schemas for this agent
        tool_schemas = self.tools.get_schemas_for_agent(
            step.agent_spec.role,
            step.agent_spec.tools
        )
        
        iteration = 0
        max_iterations = step.agent_spec.stop_conditions.max_calls
        execution_log = []
        
        while iteration < max_iterations:
            iteration += 1
            execution_log.append(f"Iteration {iteration}")

            # Print progress to console for real-time monitoring
            from rich.console import Console
            console = Console()
            console.print(f"  [dim]→ Iteration {iteration}/{max_iterations}[/dim]")

            try:
                # Make API call to Claude
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=step.agent_spec.policies.max_tokens or settings.MAX_TOKENS_PER_CALL,
                    system=step.agent_spec.system_prompt,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None
                )
                
                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Agent has finished
                    result = self._parse_final_result(response, step.id, execution_log)
                    result.duration_s = time.time() - start_time
                    return result
                
                elif response.stop_reason == "tool_use":
                    # Agent wants to use tools
                    tool_results = []
                    
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input

                            execution_log.append(f"Tool call: {tool_name}")
                            console.print(f"    [cyan]🔧 {tool_name}[/cyan]")
                            
                            # Execute tool
                            tool_result = await self._execute_tool(
                                tool_name,
                                tool_input,
                                step.id
                            )

                            # Log detailed result
                            status = tool_result.get('status', 'unknown')
                            execution_log.append(f"Tool result: {status}")
                            if status == 'error':
                                error_msg = tool_result.get('error', 'Unknown error')
                                execution_log.append(f"  Error details: {error_msg}")
                                console.print(f"      [red]✗ Error: {error_msg[:100]}[/red]")
                            elif status == 'success':
                                console.print(f"      [green]✓ Success[/green]")
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })
                    
                    # Add to conversation
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": tool_results})
                
                elif response.stop_reason == "max_tokens":
                    execution_log.append("Warning: Hit max_tokens limit")
                    console.print(f"    [yellow]⚠ Hit max_tokens limit[/yellow]")

                    # Check if there are any tool_use blocks that need results
                    tool_results = []
                    has_tool_use = False

                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            has_tool_use = True
                            tool_name = content_block.name
                            tool_input = content_block.input

                            execution_log.append(f"Tool call (max_tokens): {tool_name}")

                            # Execute tool
                            tool_result = await self._execute_tool(
                                tool_name,
                                tool_input,
                                step.id
                            )

                            # Log detailed result
                            status = tool_result.get('status', 'unknown')
                            execution_log.append(f"Tool result: {status}")
                            if status == 'error':
                                error_msg = tool_result.get('error', 'Unknown error')
                                execution_log.append(f"  Error details: {error_msg}")
                                console.print(f"      [red]✗ Error: {error_msg[:100]}[/red]")
                            elif status == 'success':
                                console.print(f"      [green]✓ Success[/green]")

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })

                    # Add to conversation
                    messages.append({"role": "assistant", "content": response.content})

                    if has_tool_use:
                        # Provide tool results
                        messages.append({"role": "user", "content": tool_results})
                    else:
                        # Just text content, prompt to continue
                        messages.append({
                            "role": "user",
                            "content": "Continue with your task. Provide final step_result when done."
                        })
                
                elif response.stop_reason == "refusal":
                    # Claude refused to process the request
                    refusal_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            refusal_text = block.text
                            break

                    execution_log.append(f"Refusal: {refusal_text[:200]}")

                    return StepResult(
                        step_id=step.id,
                        status="fail",
                        artifacts=[],
                        summary=f"Claude refused the request: {refusal_text[:150]}",
                        log=execution_log,
                        acceptance_check=AcceptanceCheck(
                            passed=False,
                            evidence=f"Refusal: {refusal_text}"
                        ),
                        duration_s=time.time() - start_time
                    )

                else:
                    # Unexpected stop reason
                    return StepResult(
                        step_id=step.id,
                        status="fail",
                        artifacts=[],
                        summary=f"Unexpected stop reason: {response.stop_reason}",
                        log=execution_log,
                        acceptance_check=AcceptanceCheck(
                            passed=False,
                            evidence=f"Stop reason: {response.stop_reason}"
                        ),
                        duration_s=time.time() - start_time
                    )
            
            except Exception as e:
                execution_log.append(f"Error: {str(e)}")
                return StepResult(
                    step_id=step.id,
                    status="fail",
                    artifacts=[],
                    summary=f"Execution error: {str(e)}",
                    log=execution_log,
                    acceptance_check=AcceptanceCheck(
                        passed=False,
                        evidence=f"Exception: {str(e)}"
                    ),
                    duration_s=time.time() - start_time
                )
        
        # Max iterations exceeded
        execution_log.append(f"Max iterations ({max_iterations}) exceeded")
        return StepResult(
            step_id=step.id,
            status="fail",
            artifacts=[],
            summary="Maximum iterations exceeded without completion",
            log=execution_log,
            acceptance_check=AcceptanceCheck(
                passed=False,
                evidence="Timeout: max_calls reached"
            ),
            duration_s=time.time() - start_time
        )
    
    async def _execute_tool(
        self, 
        tool_name: str, 
        tool_input: Dict[str, Any],
        step_id: str
    ) -> Dict[str, Any]:
        """
        Execute a tool and return its result.
        
        Args:
            tool_name: Name of the tool
            tool_input: Tool parameters
            step_id: Current step ID
            
        Returns:
            Tool execution result
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return {
                "status": "error",
                "error": f"Tool '{tool_name}' not found in registry"
            }
        
        try:
            # Create injected dependencies (separate from tool_input to avoid serialization issues)
            injected_params = {
                "step_id": step_id,
                "artifact_store": self.artifacts,
                "current_step_id": step_id
            }

            # Merge tool input with injected dependencies
            # Note: tool_input comes from Claude API and contains only user-facing parameters
            # injected_params are runtime dependencies not exposed to the LLM
            merged_params = {**tool_input, **injected_params}

            # Execute tool function
            result = await tool.function(**merged_params)
            
            # Track usage
            self.tools.track_usage(tool_name)
            
            return result if isinstance(result, dict) else {"result": result}
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tool": tool_name
            }
    
    def _parse_final_result(
        self, 
        response, 
        step_id: str,
        execution_log: list[str]
    ) -> StepResult:
        """
        Parse the agent's final response into a StepResult.
        The agent should return JSON matching StepResult schema.
        """
        # Find text content in response
        text_content = None
        for block in response.content:
            if hasattr(block, "text"):
                text_content = block.text
                break
        
        if not text_content:
            return StepResult(
                step_id=step_id,
                status="fail",
                artifacts=[],
                summary="No text content in response",
                log=execution_log,
                acceptance_check=AcceptanceCheck(
                    passed=False,
                    evidence="Empty response"
                )
            )
        
        try:
            # Clean up the response - remove markdown code blocks and extra text
            cleaned_content = text_content.strip()

            # Remove leading text before JSON (common pattern: agent explains then provides JSON)
            # Look for the first { or [ character
            json_start = -1
            for i, char in enumerate(cleaned_content):
                if char in ['{', '[']:
                    json_start = i
                    break

            if json_start > 0:
                cleaned_content = cleaned_content[json_start:]

            # Remove markdown code blocks if present
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]  # Remove ```json
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]  # Remove ```

            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]  # Remove trailing ```

            cleaned_content = cleaned_content.strip()

            # Try to parse as JSON
            result_dict = json.loads(cleaned_content)

            # Validate it's a step_result
            if result_dict.get("type") != "step_result":
                raise ValueError("Response is not a step_result")

            # Create StepResult from dict
            result = StepResult(**result_dict)
            result.log = execution_log + result.log

            return result
            
        except json.JSONDecodeError as e:
            # Not valid JSON - create fallback result with detailed error
            return StepResult(
                step_id=step_id,
                status="fail",
                artifacts=[],
                summary=f"Agent did not return valid JSON: {str(e)}",
                log=execution_log + [
                    f"JSON Parse Error: {str(e)}",
                    f"Response length: {len(text_content)} chars",
                    f"Response preview: {text_content[:500]}..."
                ],
                acceptance_check=AcceptanceCheck(
                    passed=False,
                    evidence=f"Invalid JSON response: {str(e)}"
                )
            )
        except Exception as e:
            return StepResult(
                step_id=step_id,
                status="fail",
                artifacts=[],
                summary=f"Failed to parse result: {str(e)}",
                log=execution_log,
                acceptance_check=AcceptanceCheck(
                    passed=False,
                    evidence=f"Parse error: {str(e)}"
                )
            )
    
    def validate_acceptance(self, step: Step, result: StepResult) -> AcceptanceCheck:
        """
        Validate step result against acceptance criteria.
        This is a secondary validation (agents should self-validate).
        
        Args:
            step: Step with acceptance criteria
            result: Step execution result
            
        Returns:
            AcceptanceCheck with validation result
        """
        acceptance = step.acceptance
        
        try:
            if acceptance.type == "file_exists":
                # Check if artifact exists
                if not acceptance.path_ref:
                    return AcceptanceCheck(
                        passed=False,
                        evidence="No path_ref specified in acceptance"
                    )
                
                exists = self.artifacts.exists(acceptance.path_ref)
                return AcceptanceCheck(
                    passed=exists,
                    evidence=f"Artifact {'exists' if exists else 'not found'}: {acceptance.path_ref}"
                )
            
            elif acceptance.type == "schema":
                # Validate JSON schema
                if not acceptance.path_ref:
                    return AcceptanceCheck(
                        passed=False,
                        evidence="No path_ref for schema validation"
                    )
                
                content = self.artifacts.load(acceptance.path_ref)
                
                # Check required fields
                if acceptance.schema and "required" in acceptance.schema:
                    required_fields = acceptance.schema["required"]
                    if not all(field in content for field in required_fields):
                        missing = [f for f in required_fields if f not in content]
                        return AcceptanceCheck(
                            passed=False,
                            evidence=f"Missing required fields: {missing}"
                        )
                
                # Check min_rows if it's an array
                if acceptance.min_rows and isinstance(content, list):
                    if len(content) < acceptance.min_rows:
                        return AcceptanceCheck(
                            passed=False,
                            evidence=f"Expected min {acceptance.min_rows} rows, got {len(content)}"
                        )
                
                return AcceptanceCheck(
                    passed=True,
                    evidence="Schema validation passed"
                )
            
            elif acceptance.type == "text_checks":
                # Check text constraints
                if not acceptance.path_ref:
                    return AcceptanceCheck(
                        passed=False,
                        evidence="No path_ref for text checks"
                    )
                
                content = str(self.artifacts.load(acceptance.path_ref))
                
                # Check min_chars
                if acceptance.min_chars and len(content) < acceptance.min_chars:
                    return AcceptanceCheck(
                        passed=False,
                        evidence=f"Expected min {acceptance.min_chars} chars, got {len(content)}"
                    )
                
                # Check must_contain
                if acceptance.must_contain:
                    missing = [phrase for phrase in acceptance.must_contain if phrase not in content]
                    if missing:
                        return AcceptanceCheck(
                            passed=False,
                            evidence=f"Missing required phrases: {missing}"
                        )
                
                return AcceptanceCheck(
                    passed=True,
                    evidence="Text checks passed"
                )
            
            elif acceptance.type == "llm_review":
                # Agent should have done this - trust their judgment
                return result.acceptance_check
            
            else:
                # Unknown type - default to agent's assessment
                return result.acceptance_check
        
        except Exception as e:
            return AcceptanceCheck(
                passed=False,
                evidence=f"Validation error: {str(e)}"
            )