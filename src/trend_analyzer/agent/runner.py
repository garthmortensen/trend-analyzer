#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/agent/runner.py
# role: ai_agent_runner
# desc: Agent creation, execution orchestration, and streaming event handling
# === FILE META CLOSING ===

import json
import os
from datetime import datetime

from agents import Agent, Runner, RunConfig
from agents.exceptions import MaxTurnsExceeded

from ..logging_config import info, debug, error
from ..config import config
from .tools import (
    get_trend_data_tool,
    list_available_dimensions_tool,
    get_dimension_values_tool,
    save_query_to_csv_tool,
)
from .prompts import make_analysis_prompt, get_iteration_phase


# ───────────────────────────────
# Agent Creation
# ───────────────────────────────

# async def: This function is async to maintain consistency with the async execution pattern
# used throughout the SDK. While it doesn't perform async I/O itself, it's called from
# async contexts (run_analysis) and returns an Agent that will be used in async operations.
async def create_analysis_agent(model: str, system_prompt: str) -> Agent:
    """Create the trend analysis agent with tools and instructions.
    
    Args:
        model: OpenAI model name (from config or env)
        system_prompt: The system instructions for this agent
    
    Returns:
        Configured Agent instance
    """
    
    agent = Agent(
        name="Trend Analysis Agent",
        instructions=system_prompt,
        model=model,
        tools=[
            get_trend_data_tool,
            list_available_dimensions_tool,
            get_dimension_values_tool,
            save_query_to_csv_tool
        ]
    )
    
    return agent


# ───────────────────────────────
# Streaming Execution
# ───────────────────────────────

# async def: REQUIRED for streaming agent execution. The SDK's Runner.run_streamed() returns
# an async iterator (result.stream_events()) that must be consumed with "async for".
# This function performs actual async I/O operations by streaming events from the OpenAI API.
async def run_once_streamed(agent: Agent, user_msg: str, iteration_num: int = 1, max_turns: int = 5):
    """Run the agent for one iteration (allows multiple tool calls within the turn).
    
    Args:
        agent: The agent instance
        user_msg: User message or conversation history
        iteration_num: Current iteration number (for logging)
        max_turns: Maximum turns for this iteration (default: 5 to allow thinking + tool calls)
    
    Returns:
        Tuple of (result, transcript, tool_call_count, tool_calls_made)
    """
    
    transcript = []
    tool_call_count = 0
    tool_calls_made = []  # Track tool calls for loop detection
    
    info(f"[Iteration {iteration_num}] Starting agent execution with max_turns={max_turns}")
    debug(f"[Iteration {iteration_num}] User message length: {len(user_msg)} chars")
    
    result = Runner.run_streamed(
        agent,
        input=user_msg,
        max_turns=max_turns,
        run_config=RunConfig(tracing_disabled=True),
    )
    
    try:
        async for ev in result.stream_events():
            if ev.type != "run_item_stream_event":
                continue
            
            it = ev.item
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Model reasoning (PLAN/REFLECT)
            if it.type == "reasoning_item":
                thought = "\n".join(
                    s.text for s in it.raw_item.summary
                    if s.type == "summary_text"
                )
                if thought:
                    info(f"\n[{ts}] >> THOUGHT (Iteration {iteration_num}):")
                    print(thought)
                    transcript.append(f"\n[{ts}] >> THOUGHT (Iteration {iteration_num}):\n{thought}")
            
            # Tool call
            elif it.type == "tool_call_item":
                tool_call_count += 1
                
                # Format args in a readable way without escape characters
                args_raw = it.raw_item.arguments
                
                # Handle case where arguments might be a string or dict
                if isinstance(args_raw, str):
                    try:
                        args_dict = json.loads(args_raw)
                    except Exception:
                        args_dict = {"raw": args_raw}
                else:
                    args_dict = args_raw
                
                # Store tool call signature for loop detection
                tool_signature = {
                    "name": it.raw_item.name,
                    "args": args_dict
                }
                tool_calls_made.append(tool_signature)
                
                # Format as line-separated key-value pairs
                formatted_args = []
                for key, value in args_dict.items():
                    # Handle string values that might be JSON
                    if isinstance(value, str) and value.startswith('['):
                        try:
                            # Try to parse as JSON for better formatting
                            parsed = json.loads(value)
                            formatted_args.append(f"  {key}: {json.dumps(parsed, indent=4)}")
                        except Exception:
                            formatted_args.append(f"  {key}: {value}")
                    else:
                        formatted_args.append(f"  {key}: {value}")
                
                args_text = "\n".join(formatted_args)
                
                tool_msg = f"-> TOOL #{tool_call_count}: {it.raw_item.name}\nArgs:\n{args_text}"
                info(f"\n[{ts}] {tool_msg}")
                transcript.append(f"\n[{ts}] {tool_msg}")
            
            # Tool result
            elif it.type == "tool_call_output_item":
                result_preview = str(it.output)[:200] if hasattr(it, 'output') else "N/A"
                debug(f"[{ts}] <- TOOL RESULT (preview): {result_preview}...")
            
            # Assistant message
            elif it.type == "message_output_item":
                msg = it.content if hasattr(it, 'content') else str(it)
                info(f"\n[{ts}] << ASSISTANT:")
                print(msg)
                transcript.append(f"\n[{ts}] << ASSISTANT:\n{msg}")
        
        info(f"[Iteration {iteration_num}] Completed successfully. Tool calls: {tool_call_count}")
    
    except MaxTurnsExceeded:
        # Can happen if agent tries to do too many things in one iteration
        # This is usually fine - agent has made progress before hitting limit
        info(f"[Iteration {iteration_num}] Turn limit reached. Tool calls made: {tool_call_count}")
    
    except Exception as e:
        error(f"[Iteration {iteration_num}] Unexpected error during streaming: {e}")
        raise
    
    return result, transcript, tool_call_count, tool_calls_made


# ───────────────────────────────
# Main Analysis Orchestration
# ───────────────────────────────

# async def: Main entry point for agent execution. Must be async because it:
# 1. Calls await create_analysis_agent() to create the agent
# 2. Calls await run_once_streamed() which performs async streaming I/O
# 3. Uses asyncio to coordinate multiple async operations (agent creation, execution, streaming)
async def run_analysis(iterations: int = 10) -> str:
    """
    Run the iterative trend analysis with phase-specific prompting.
    
    This is the main orchestration function that:
    1. Creates a fresh agent for each iteration with updated instructions
    2. Manages conversation history across iterations
    3. Detects completion markers to stop early
    4. Generates the final report
    
    Args:
        iterations: Total number of iterations allowed
        
    Returns:
        str: Path to the generated report file
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info("=" * 60)
    info(f"[{ts}] Starting Trend Analysis Agent")
    info(f"Max iterations: {iterations}")
    info("=" * 60)
    
    # Verify OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        error("OPENAI_API_KEY environment variable not set")
        error("Set it in your .env file or environment")
        return ""
    
    # Get configuration from analysis.yml
    analysis_config = config.get_analysis_config()
    model = analysis_config.get("openai_model", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    timeout = analysis_config.get("openai_timeout_seconds", int(os.environ.get("OPENAI_TIMEOUT_SECONDS", "30")))
    
    debug(f"Using OpenAI model: {model}")
    debug(f"API timeout: {timeout} seconds")
    
    # SDK Stack Diagram - shows full call chain from this code to OpenAI API
    sdk_stack_diagram = """
╔════════════════════════════════════════════════════════════════╗
║                    OPENAI AGENTS SDK STACK                     ║
╠════════════════════════════════════════════════════════════════╣
║ Layer 1: runner.py (this file)                                ║
║   - Manages iterative loop with phase-specific prompts        ║
║   - Logs system prompts, tool calls, and responses            ║
║   - Calls: Runner.run_streamed(agent, user_message)           ║
║                            ↓                                   ║
║ Layer 2: openai-agents library                                ║
║   - Agent orchestration and function tool registration        ║
║   - Converts function_tool decorators to OpenAI tool schemas  ║
║   - Manages conversation state and tool call routing          ║
║   - Calls: openai.Client.beta.threads.runs.create()           ║
║                            ↓                                   ║
║ Layer 3: openai Python SDK                                    ║
║   - HTTP client wrapping OpenAI REST API                      ║
║   - Handles authentication, retries, timeouts                 ║
║   - Serializes requests to JSON, parses responses             ║
║   - Calls: POST https://api.openai.com/v1/threads/runs        ║
║                            ↓                                   ║
║ Layer 4: OpenAI Assistants API                                ║
║   - Receives system prompt + user message + tool schemas      ║
║   - LLM generates response (text or tool calls)               ║
║   - Returns assistant message or required_action              ║
╚════════════════════════════════════════════════════════════════╝
"""
    
    # Log SDK stack once at start
    info(sdk_stack_diagram)
    
    # Run iterative analysis loop with phase-specific prompts
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info("\n" + "=" * 60)
    info(f"[{ts}] Starting Iterative Analysis")
    info(f"[{ts}] Total iterations: {iterations}")
    info("=" * 60)
    
    all_transcripts = []
    all_system_prompts = []  # Track system prompts per iteration
    total_tool_calls = 0
    conversation_history = []
    tool_call_history = []  # Track all tool calls for loop detection
    final_result = None
    
    try:
        for current_iter in range(1, iterations + 1):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Detect phase and generate phase-specific system prompt
            phase = get_iteration_phase(current_iter, iterations)
            system_prompt = make_analysis_prompt(iterations, current_iteration=current_iter)
            
            # Log iteration header with phase
            info("\n" + "=" * 60)
            info(f"[{ts}] ITERATION {current_iter} of {iterations} - {phase.upper()} PHASE")
            info("=" * 60)
            
            # Log the system prompt for full transparency
            info(f"\n[{ts}] System Prompt for Iteration {current_iter}:")
            info("-" * 60)
            info(system_prompt)
            info("-" * 60)
            
            # Store system prompt for final report
            all_system_prompts.append({
                "iteration": current_iter,
                "phase": phase,
                "prompt": system_prompt
            })
            
            # Create agent with current iteration's system prompt
            agent = await create_analysis_agent(model=model, system_prompt=system_prompt)
            
            # Build user message
            if current_iter == 1:
                user_msg = """Begin the trend analysis.

Start by understanding what dimensions are available, then systematically drill down into key drivers.
Follow the PLAN-ACTION-REFLECT pattern for each analytical step.

CRITICAL: As you discover important findings, use save_query_to_csv_tool to preserve diverse datasets.
Remember: maximum 3 tool calls per iteration, then reflect and move to next iteration."""
            else:
                # Continue conversation - provide context from previous iteration
                user_msg_parts = [f"Continue your analysis. This is iteration {current_iter} of {iterations}."]
                
                # Add previous findings
                if conversation_history:
                    prev_summary = conversation_history[-1]
                    user_msg_parts.append(f"\nPrevious findings: {prev_summary}")
                
                # Add tool call history to prevent repetition
                if tool_call_history:
                    recent_calls = tool_call_history[-6:]  # Show last 6 tool calls
                    tools_summary = "\n\nRECENT TOOL CALLS (avoid repeating these exact queries):"
                    for idx, call in enumerate(recent_calls, 1):
                        tools_summary += f"\n  {idx}. {call['name']}("
                        args_str = ", ".join(f"{k}={v}" for k, v in call['args'].items())
                        tools_summary += args_str + ")"
                    user_msg_parts.append(tools_summary)
                    user_msg_parts.append("\n\nIMPORTANT: Do NOT repeat the exact same tool calls shown above. Use different dimensions, filters, or group_by options.")
                
                user_msg = "".join(user_msg_parts)
            
            # Run one iteration (max_turns=5 allows agent to think AND call tools in same iteration)
            result, transcript, tool_calls, tool_calls_made = await run_once_streamed(
                agent,
                user_msg=user_msg,
                iteration_num=current_iter,
                max_turns=5
            )
            
            all_transcripts.extend(transcript)
            total_tool_calls += tool_calls
            tool_call_history.extend(tool_calls_made)  # Track all tool calls
            
            # Detect repetitive tool call patterns (loop detection)
            if len(tool_call_history) >= 6:
                # Check if the last 2 calls match any of the previous 4 calls
                recent_2 = tool_call_history[-2:]
                previous_4 = tool_call_history[-6:-2]
                
                # Count how many times the recent pattern appears
                repetition_count = 0
                for i in range(len(previous_4) - 1):
                    if previous_4[i] == recent_2[0] and previous_4[i+1] == recent_2[1]:
                        repetition_count += 1
                
                if repetition_count >= 2:
                    ts_loop = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    warning_msg = f"\n[{ts_loop}] /!\\ LOOP DETECTED: Agent is repeating the same tool calls. Breaking out of analysis loop."
                    info(warning_msg)
                    all_transcripts.append(warning_msg)
                    
                    # Add diagnostic info
                    loop_info = "\n\nLOOP DETECTION DETAILS:"
                    loop_info += f"\nRepeated tool call pattern found {repetition_count + 1} times:"
                    loop_info += f"\n  1. {recent_2[0]['name']}({', '.join(f'{k}={v}' for k, v in recent_2[0]['args'].items())})"
                    loop_info += f"\n  2. {recent_2[1]['name']}({', '.join(f'{k}={v}' for k, v in recent_2[1]['args'].items())})"
                    loop_info += "\n\nThis indicates the agent is stuck and unable to make progress."
                    info(loop_info)
                    all_transcripts.append(loop_info)
                    
                    final_result = result
                    break
            
            # Extract assistant response for conversation history
            if result and result.final_output:
                assistant_msg = result.final_output
                conversation_history.append(assistant_msg)
                
                # Check for completion markers
                completion_markers = [
                    "FINAL REPORT AND ANALYSIS CONCLUDED",
                    "ABSOLUTE FINAL SUMMARY AND RECOMMENDATIONS",
                    "## COMPANY-WIDE SUMMARY & KEY DRIVERS FINAL DOCUMENT"
                ]
                if any(marker in assistant_msg for marker in completion_markers):
                    ts_complete = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    info(f"\n[{ts_complete}] Completion marker detected - analysis finished early")
                    final_result = result
                    break
            
            final_result = result
        
        # Extract final output
        if not final_result or not final_result.final_output:
            # Iterations exhausted - use last conversation history item
            final_report = f"ANALYSIS INCOMPLETE: All {iterations} iterations used.\n\n"
            final_report += "Latest analysis state:\n"
            if conversation_history:
                final_report += conversation_history[-1]
            else:
                final_report += "No final summary available. See transcript for analysis progress."
        else:
            final_report = final_result.final_output
        
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info("\n" + "=" * 60)
        info(f"[{ts}] === ANALYSIS COMPLETE ===")
        info(f"[{ts}] Total tool calls made: {total_tool_calls}")
        info("=" * 60)
        
        # Get metadata
        db_config = config.get_database_config()
        
        # Build comprehensive report with SDK stack and all system prompts
        full_report = "=" * 60 + "\n"
        full_report += "TREND ANALYSIS REPORT\n"
        full_report += "=" * 60 + "\n\n"
        
        # SDK Stack Diagram
        full_report += sdk_stack_diagram
        full_report += "\n\n"
        
        # Report metadata
        full_report += "REPORT METADATA:\n"
        full_report += "-" * 60 + "\n"
        full_report += f"Generated: {ts}\n"
        full_report += f"AI Model: {model}\n"
        full_report += f"Max Iterations: {iterations}\n"
        full_report += f"Iterations Completed: {len(all_system_prompts)}\n"
        full_report += f"Total Tool Calls: {total_tool_calls}\n"
        full_report += f"Database: {db_config.get('database', 'N/A')}\n"
        full_report += f"Schema: {db_config.get('schema', 'N/A')}\n"
        full_report += f"Host: {db_config.get('host', 'N/A')}:{db_config.get('port', 'N/A')}\n"
        
        # Add filter configuration
        filters = analysis_config.get('filters', [])
        if filters:
            full_report += f"Filters Applied: {len(filters)}\n"
            for f in filters:
                dim = f.get('dimension_name', '?')
                op = f.get('operator', '?')
                val = f.get('value', '?')
                full_report += f"  - {dim} {op} {val}\n"
        
        full_report += "\n" + "=" * 60 + "\n\n"
        
        # System prompts section - show what instructions were given each iteration
        full_report += "SYSTEM PROMPTS PER ITERATION:\n"
        full_report += "-" * 60 + "\n"
        for prompt_info in all_system_prompts:
            full_report += f"\nIteration {prompt_info['iteration']} ({prompt_info['phase'].upper()} phase):\n"
            full_report += prompt_info['prompt']
            full_report += "\n" + "-" * 60 + "\n"
        
        full_report += "\n" + "=" * 60 + "\n\n"
        
        # Analysis transcript
        full_report += "ANALYSIS TRANSCRIPT:\n"
        full_report += "\n".join(all_transcripts)
        full_report += "\n\n" + "=" * 60 + "\n"
        
        # Final summary
        full_report += "FINAL SUMMARY:\n"
        full_report += "=" * 60 + "\n\n"
        full_report += final_report
        
        # Save to file
        output_dir = config.get_output_dir()
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_trend_analysis_report.out"
        output_file = os.path.join(output_dir, filename)
        
        with open(output_file, "w") as f:
            f.write(full_report)
        
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info(f"\n[{ts}] Report saved to: {output_file}")
        
        return full_report
        
    except Exception as e:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error(f"\n[{ts}] Analysis failed: {e}")
        raise
