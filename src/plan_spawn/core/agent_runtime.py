"""
Agent runtime for executing individual steps.
Creates ephemeral agents that can use tools iteratively.
"""
import json
import time
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from .models import Step, StepResult, AcceptanceCheck
from .tools.registry import ToolRegistry
from .storage.artifacts import ArtifactStore
from ..config.settings import settings

# Setup detailed logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.model = settings.OPENAI_MODEL
        self.tools = tool_registry
        self.artifacts = artifact_store

        # Setup file logging for detailed debugging
        self._setup_file_logging()

    def _setup_file_logging(self):
        """Setup detailed file logging for debugging agent conversations."""
        import os
        from datetime import datetime

        # Create logs directory if it doesn't exist
        log_dir = "agent_logs"
        os.makedirs(log_dir, exist_ok=True)

        # Create a file handler with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"agent_runtime_{timestamp}.log")

        # Add file handler to logger
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(file_handler)

        logger.info(f"Agent runtime logging initialized: {log_file}")

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

        logger.info(f"=== Starting execution of step {step.id}: {step.title} ===")
        logger.debug(f"Agent role: {step.agent_spec.role}")
        logger.debug(f"Available tools: {step.agent_spec.tools}")
        logger.debug(f"Context: {json.dumps(context, indent=2, ensure_ascii=False)}")

        # Build initial messages (system + user)
        messages = [
            {
                "role": "system",
                "content": step.agent_spec.system_prompt
            },
            {
                "role": "user",
                "content": json.dumps({
                    "type": "execute_step",
                    "step_id": step.id,
                    "context": context
                }, ensure_ascii=False)
            }
        ]

        logger.debug(f"Initial system prompt length: {len(step.agent_spec.system_prompt)} chars")
        logger.debug(f"System prompt preview: {step.agent_spec.system_prompt[:200]}...")
        
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
                # Make API call to OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=step.agent_spec.policies.max_tokens or settings.MAX_TOKENS_PER_CALL,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None
                )

                # Get the message and finish reason
                message = response.choices[0].message
                finish_reason = response.choices[0].finish_reason

                # Check finish reason
                if finish_reason == "stop":
                    # Agent has finished
                    logger.info(f"[Step {step.id}] Agent finished with finish_reason='stop'")
                    result = self._parse_final_result(response, step.id, execution_log)
                    result.duration_s = time.time() - start_time
                    logger.info(f"[Step {step.id}] Execution completed in {result.duration_s:.2f}s with status={result.status}")
                    return result

                elif finish_reason == "tool_calls":
                    # Agent wants to use tools
                    tool_calls = message.tool_calls

                    # Add assistant message to conversation
                    messages.append({
                        "role": "assistant",
                        "content": message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in tool_calls
                        ]
                    })

                    # Execute each tool
                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        tool_input = json.loads(tool_call.function.arguments)

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

                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        })

                        # If write_artifact was successful, remind agent to finish
                        if tool_name == "write_artifact" and tool_result.get("status") == "success":
                            logger.info(f"[Step {step.id}] write_artifact completed - adding reminder to finish")
                            reminder_json_example = {
                                "type": "step_result",
                                "step_id": step.id,
                                "status": "ok",
                                "artifacts": ["artifact://YOUR_STEP_ID/filename.ext"],
                                "summary": "Brief description of what was accomplished",
                                "log": [],
                                "acceptance_check": {
                                    "passed": True,
                                    "evidence": "Explanation of why acceptance criteria are met"
                                }
                            }
                            messages.append({
                                "role": "user",
                                "content": f"Perfect! The artifact was saved successfully.\n\nNow you MUST respond with the final step_result JSON. Do NOT use any more tools. Your next response must be ONLY this JSON structure (fill in the actual artifact URIs you created):\n\n{json.dumps(reminder_json_example, indent=2, ensure_ascii=False)}"
                            })
                
                elif finish_reason == "length":
                    execution_log.append("Warning: Hit max_tokens limit")
                    console.print(f"    [yellow]⚠ Hit max_tokens limit[/yellow]")

                    # Check if there are any tool_calls that need results
                    has_tool_calls = message.tool_calls is not None and len(message.tool_calls) > 0
                    has_incomplete_tool = False

                    if has_tool_calls:
                        # Add assistant message first
                        messages.append({
                            "role": "assistant",
                            "content": message.content,
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": tc.type,
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                } for tc in message.tool_calls
                            ]
                        })

                        for tool_call in message.tool_calls:
                            tool_name = tool_call.function.name
                            try:
                                tool_input = json.loads(tool_call.function.arguments)

                                # Check if tool input is complete
                                # For write_artifact, both 'name' and 'content' are required
                                if tool_name == "write_artifact":
                                    if not isinstance(tool_input, dict) or 'content' not in tool_input or 'name' not in tool_input:
                                        has_incomplete_tool = True
                                        execution_log.append(f"Tool call (max_tokens, INCOMPLETE): {tool_name}")
                                        console.print(f"      [yellow]⚠ Incomplete tool call, skipping[/yellow]")
                                        continue

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

                                # Add tool result
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps(tool_result, ensure_ascii=False)
                                })
                            except json.JSONDecodeError:
                                has_incomplete_tool = True
                                execution_log.append(f"Tool call (max_tokens, INVALID JSON): {tool_name}")
                                console.print(f"      [yellow]⚠ Invalid JSON in tool arguments[/yellow]")

                    else:
                        # No tool calls, add assistant message and prompt to continue
                        messages.append({
                            "role": "assistant",
                            "content": message.content
                        })

                        if has_incomplete_tool:
                            # Had incomplete tool calls, ask agent to retry with smaller output
                            messages.append({
                                "role": "user",
                                "content": "Your previous response was truncated due to token limit. Please try again with a more concise approach. If writing artifacts, consider breaking content into smaller chunks or summarizing."
                            })
                        else:
                            # Just text content, prompt to continue
                            messages.append({
                                "role": "user",
                                "content": "Continue with your task. Provide final step_result when done."
                            })
                
                elif finish_reason == "content_filter":
                    # OpenAI content filter triggered
                    refusal_text = message.content or "Content filtered by OpenAI"
                    execution_log.append(f"Content filter: {refusal_text[:200]}")

                    return StepResult(
                        step_id=step.id,
                        status="fail",
                        artifacts=[],
                        summary=f"Content filtered: {refusal_text[:150]}",
                        log=execution_log,
                        acceptance_check=AcceptanceCheck(
                            passed=False,
                            evidence=f"Content filter: {refusal_text}"
                        ),
                        duration_s=time.time() - start_time
                    )

                else:
                    # Unexpected finish reason
                    return StepResult(
                        step_id=step.id,
                        status="fail",
                        artifacts=[],
                        summary=f"Unexpected finish reason: {finish_reason}",
                        log=execution_log,
                        acceptance_check=AcceptanceCheck(
                            passed=False,
                            evidence=f"Finish reason: {finish_reason}"
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
        # Get text content from OpenAI response
        text_content = response.choices[0].message.content

        # Log the raw response for debugging
        logger.debug(f"[Step {step_id}] Raw final response from agent:")
        logger.debug(f"{text_content}")
        execution_log.append(f"Raw response length: {len(text_content) if text_content else 0} chars")

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

            execution_log.append(f"Cleaning response...")

            # Remove leading text before JSON (common pattern: agent explains then provides JSON)
            # Look for the first { or [ character
            json_start = -1
            for i, char in enumerate(cleaned_content):
                if char in ['{', '[']:
                    json_start = i
                    break

            if json_start > 0:
                skipped_text = cleaned_content[:json_start]
                execution_log.append(f"Skipped leading text: {skipped_text[:100]}...")
                cleaned_content = cleaned_content[json_start:]

            # Remove markdown code blocks if present
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]  # Remove ```json
                execution_log.append("Removed ```json wrapper")
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]  # Remove ```
                execution_log.append("Removed ``` wrapper")

            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]  # Remove trailing ```
                execution_log.append("Removed trailing ```")

            cleaned_content = cleaned_content.strip()

            # Log the cleaned JSON for debugging
            logger.debug(f"[Step {step_id}] Cleaned JSON content:")
            logger.debug(f"{cleaned_content[:500]}...")
            execution_log.append(f"Cleaned JSON length: {len(cleaned_content)} chars")

            # Try to parse as JSON
            result_dict = json.loads(cleaned_content)
            execution_log.append(f"Successfully parsed JSON with type: {result_dict.get('type', 'NO TYPE')}")

            # Validate it's a step_result
            if result_dict.get("type") != "step_result":
                logger.warning(f"[Step {step_id}] Response type is '{result_dict.get('type')}', expected 'step_result'")
                execution_log.append(f"Invalid type: {result_dict.get('type')}")
                # Log the full dict structure
                logger.debug(f"[Step {step_id}] Full response dict: {json.dumps(result_dict, indent=2)}")
                raise ValueError(f"Response type is '{result_dict.get('type')}', expected 'step_result'")

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

                # Check required fields (use schema_def which has alias 'schema')
                if acceptance.schema_def and "required" in acceptance.schema_def:
                    required_fields = acceptance.schema_def["required"]
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