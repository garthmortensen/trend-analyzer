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
from colorama import Fore, Back, Style, init

from ..logging_config import info, debug, error
from ..config import config

# Initialize colorama for cross-platform color support
init(autoreset=True)
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
                    # Only print to console, don't log (keeps analytical content out of logs)
                    print(f"\n{Fore.CYAN}[{ts}] >> THOUGHT (Iteration {iteration_num}):{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{thought}{Style.RESET_ALL}")
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
                
                # Log tool call with key parameters for infrastructure tracking
                # Create concise parameter summary for log
                param_summary = []
                for key, value in args_dict.items():
                    if isinstance(value, str):
                        # Truncate long strings
                        val_str = value[:50] + "..." if len(value) > 50 else value
                    elif isinstance(value, (list, dict)):
                        val_str = f"{type(value).__name__}[{len(value)}]"
                    else:
                        val_str = str(value)
                    param_summary.append(f"{key}={val_str}")
                
                params_log = ", ".join(param_summary) if param_summary else "no args"
                info(f"Tool call #{tool_call_count}: {it.raw_item.name}({params_log})")
                
                # Print tool call to console with color
                print(f"\n{Fore.YELLOW}[{ts}] -> TOOL #{tool_call_count}: {it.raw_item.name}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Args: {params_log}{Style.RESET_ALL}")
                
                transcript.append(f"\n[{ts}] {tool_msg}")
            
            # Tool result
            elif it.type == "tool_call_output_item":
                result_preview = str(it.output)[:200] if hasattr(it, 'output') else "N/A"
                debug(f"[{ts}] <- TOOL RESULT (preview): {result_preview}...")
            
            # Assistant message
            elif it.type == "message_output_item":
                msg = it.content if hasattr(it, 'content') else str(it)
                # Only print to console, don't log (keeps analytical content out of logs)
                print(f"\n{Fore.GREEN}[{ts}] << ASSISTANT:{Style.RESET_ALL}")
                print(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")
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
    # Create timestamped run directory structure
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base_dir = config.get_output_dir()
    run_dir = os.path.join(output_base_dir, run_timestamp)
    os.makedirs(run_dir, exist_ok=True)
    
    # Reconfigure logger to write to run directory
    from ..logging_config import reconfigure_log_file
    log_file_path = os.path.join(run_dir, "analysis.log")
    reconfigure_log_file(log_file_path)
    
    # Create data subdirectory for CSVs
    csv_output_dir = os.path.join(run_dir, "data")
    os.makedirs(csv_output_dir, exist_ok=True)
    
    # Create config subdirectory and copy config files for reproducibility
    config_output_dir = os.path.join(run_dir, "config")
    os.makedirs(config_output_dir, exist_ok=True)
    
    # Copy config files to run directory
    import shutil
    from pathlib import Path
    
    # Go up 4 levels from runner.py: agent/ -> trend_analyzer/ -> src/ -> project_root/
    config_dir = Path(__file__).parent.parent.parent.parent / "config"
    debug(f"Looking for config files in: {config_dir}")
    config_files = ["analysis.yml", "dimensions.yml", "infrastructure.yml"]
    
    copied_count = 0
    for config_file in config_files:
        source = config_dir / config_file
        if source.exists():
            dest = Path(config_output_dir) / config_file
            try:
                shutil.copy2(source, dest)
                debug(f"Copied config: {config_file} -> {dest}")
                copied_count += 1
            except Exception as e:
                error(f"Failed to copy {config_file}: {e}")
        else:
            error(f"Config file not found: {source}")
    
    if copied_count > 0:
        info(f"Copied {copied_count} config files to {config_output_dir}")
    else:
        error("No config files were copied!")
    
    # Set environment variables so tools know where to save CSVs
    os.environ["TREND_ANALYZER_RUN_DIR"] = run_dir
    os.environ["TREND_ANALYZER_CSV_DIR"] = csv_output_dir
    
    banner = """
    ▄▄▄▄▄▄ ▄▄▄▄  ▄▄▄▄▄ ▄▄  ▄▄ ▄▄▄▄         ▄▄▄  ▄▄  ▄▄  ▄▄▄  ▄▄  ▄▄ ▄▄ ▄▄▄▄▄ ▄▄▄▄▄ ▄▄▄▄
      ██   ██▄█▄ ██▄▄  ███▄██ ██▀██ g▄▄▄m ██▀██ ███▄██ ██▀██ ██  ▀███▀   ▄█▀ ██▄▄  ██▄█▄
      ██   ██ ██ ██▄▄▄ ██ ▀██ ████▀       ██▀██ ██ ▀██ ██▀██ ██▄▄▄ █   ▄██▄▄ ██▄▄▄ ██ ██"""
    # Print banner in red to console
    print(f"{Fore.RED}{Style.BRIGHT}{banner}{Style.RESET_ALL}")
    
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info("=" * 60)
    info(f"[{ts}] Starting Trend Analysis Agent")
    info(f"Max iterations: {iterations}")
    info(f"Run directory: {run_dir}")
    info("=" * 60)
    
    # Print colored startup message to console
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}Starting Trend Analysis Agent{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Max iterations: {iterations}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Run directory: {run_dir}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 60}{Style.RESET_ALL}\n")
    
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
    
    # SDK stack diagram saved to report only, not logged
    debug("SDK architecture diagram will be included in report")
    
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
            
            # Print colored iteration header to console
            print(f"\n{Fore.MAGENTA}{Back.BLACK}{'=' * 60}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}{Back.BLACK}[{ts}] ITERATION {current_iter} of {iterations} - {phase.upper()} PHASE{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}{Back.BLACK}{'=' * 60}{Style.RESET_ALL}\n")
            
            # Add iteration marker to transcript for report structuring
            iteration_marker = f"\n[{ts}] === ITERATION {current_iter} of {iterations} - {phase.upper()} PHASE ==="
            all_transcripts.append(iteration_marker)
            
            # Log iteration start (system prompt details saved in report only)
            debug(f"System prompt generated for iteration {current_iter} ({phase} phase)")
            
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
                user_msg = f"""Begin the trend analysis.

Start by understanding what dimensions are available, then systematically drill down into key drivers.
Follow the PLAN-ACTION-REFLECT pattern for each analytical step.

CSV EXPORT REQUIREMENT: You MUST save diverse query results to CSV files throughout your analysis:
- Target: 3-5 different CSV files by the end of exploration
- Use save_query_to_csv_tool after discovering interesting patterns
- Each CSV should capture a DIFFERENT analytical perspective (service mix, provider patterns, geographic trends, etc.)
- CSV files will be saved to: {csv_output_dir}

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
                    
                    # Print colored warning to console
                    print(f"\n{Fore.RED}{Style.BRIGHT}LOOP DETECTED: Agent is repeating the same tool calls{Style.RESET_ALL}")
                    print(f"{Fore.RED}Breaking out of analysis loop...{Style.RESET_ALL}\n")
                    
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
        
        # Build comprehensive markdown report with proper hierarchy
        full_report = "# Trend Analysis Report\n\n"
        
        full_report += "## Table of Contents\n\n"
        full_report += "1. [Report Metadata](#report-metadata)\n"
        full_report += "2. [OpenAI Agents SDK Stack](#openai-agents-sdk-stack)\n"
        full_report += "3. [System Prompts Per Iteration](#system-prompts-per-iteration)\n"
        full_report += "4. [Analysis Transcript](#analysis-transcript)\n"
        for i in range(1, len(all_system_prompts) + 1):
            full_report += f"   - [Iteration {i}](#iteration-{i})\n"
        full_report += "5. [Final Summary](#final-summary)\n\n"
        
        full_report += "---\n\n"
        
        # Report metadata
        full_report += "## Report Metadata\n\n"
        full_report += f"- **Generated**: {ts}\n"
        full_report += f"- **Run Directory**: `{run_dir}`\n"
        full_report += f"- **Log File**: `{log_file_path}`\n"
        full_report += f"- **Config Files**: `{config_output_dir}`\n"
        full_report += f"- **CSV Output**: `{csv_output_dir}`\n"
        full_report += f"- **AI Model**: `{model}`\n"
        full_report += f"- **Max Iterations**: {iterations}\n"
        full_report += f"- **Iterations Completed**: {len(all_system_prompts)}\n"
        full_report += f"- **Total Tool Calls**: {total_tool_calls}\n"
        full_report += f"- **Database**: `{db_config.get('database', 'N/A')}`\n"
        full_report += f"- **Schema**: `{db_config.get('schema', 'N/A')}`\n"
        full_report += f"- **Host**: `{db_config.get('host', 'N/A')}:{db_config.get('port', 'N/A')}`\n\n"
        
        # Add filter configuration
        filters = analysis_config.get('filters', [])
        if filters:
            full_report += f"### Filters Applied ({len(filters)})\n\n"
            for f in filters:
                dim = f.get('dimension_name', '?')
                op = f.get('operator', '?')
                val = f.get('value', '?')
                full_report += f"- `{dim} {op} {val}`\n"
            full_report += "\n"
        
        full_report += "---\n\n"
        
        # SDK Stack Diagram
        full_report += "## OpenAI Agents SDK Stack\n\n"
        full_report += "```\n"
        full_report += sdk_stack_diagram.strip()
        full_report += "\n```\n\n"
        full_report += "---\n\n"
        
        # System prompts section - show what instructions were given each iteration
        full_report += "## System Prompts Per Iteration\n\n"
        full_report += "_System prompts provided to the AI agent for each iteration._\n\n"
        
        for prompt_info in all_system_prompts:
            full_report += f"### Iteration {prompt_info['iteration']} - {prompt_info['phase'].upper()} Phase\n\n"
            full_report += prompt_info['prompt']
            full_report += "\n\n"
        
        full_report += "---\n\n"
        
        # Analysis transcript - organize by iteration
        full_report += "## Analysis Transcript\n\n"
        full_report += "_Detailed log of all agent actions, tool calls, and reasoning._\n\n"
        
        # Group transcript entries by iteration
        current_iteration_entries = []
        current_iteration_num = 1
        current_iteration_phase = "EXPLORATION"  # Default phase
        
        for entry in all_transcripts:
            # Check if this is a new iteration marker
            if "=== ITERATION" in entry and " PHASE ===" in entry:
                # Extract iteration number and phase from marker
                import re
                match = re.search(r'ITERATION (\d+) of \d+ - (\w+) PHASE', entry)
                if match:
                    new_iter_num = int(match.group(1))
                    new_phase = match.group(2).title()  # Convert "EXPLORATION" to "Exploration"
                    
                    # Save previous iteration's entries (if any)
                    if current_iteration_entries:
                        full_report += f"### Iteration {current_iteration_num} - {current_iteration_phase} Phase\n\n"
                        for transcript_entry in current_iteration_entries:
                            # Parse entry type
                            if ">> THOUGHT" in transcript_entry:
                                full_report += "#### Agent Reasoning\n\n"
                                thought_text = transcript_entry.split(">> THOUGHT")[1].strip()
                                full_report += f"{thought_text}\n\n"
                            elif "-> TOOL #" in transcript_entry:
                                full_report += "#### Tool Call\n\n"
                                full_report += f"```\n{transcript_entry.strip()}\n```\n\n"
                            elif "<- TOOL RESULT" in transcript_entry:
                                full_report += "#### Tool Result\n\n"
                                full_report += f"```\n{transcript_entry.strip()}\n```\n\n"
                            elif "<< ASSISTANT" in transcript_entry:
                                full_report += "#### Assistant Response\n\n"
                                response_text = transcript_entry.split("<< ASSISTANT:")[1].strip() if "<< ASSISTANT:" in transcript_entry else transcript_entry.strip()
                                full_report += f"{response_text}\n\n"
                            elif "/!\\" in transcript_entry and "LOOP DETECTED" in transcript_entry:
                                full_report += "#### Loop Detection Warning\n\n"
                                full_report += f"```\n{transcript_entry.strip()}\n```\n\n"
                            else:
                                # Generic entry
                                full_report += f"{transcript_entry}\n\n"
                        
                        full_report += "---\n\n"
                    
                    # Reset for next iteration using the extracted iteration number and phase
                    current_iteration_entries = []
                    current_iteration_num = new_iter_num
                    current_iteration_phase = new_phase
            else:
                current_iteration_entries.append(entry)
        
        # Don't forget the last iteration
        if current_iteration_entries:
            full_report += f"### Iteration {current_iteration_num} - {current_iteration_phase} Phase\n\n"
            for transcript_entry in current_iteration_entries:
                if ">> THOUGHT" in transcript_entry:
                    full_report += "#### Agent Reasoning\n\n"
                    thought_text = transcript_entry.split(">> THOUGHT")[1].strip()
                    full_report += f"{thought_text}\n\n"
                elif "-> TOOL #" in transcript_entry:
                    full_report += "#### Tool Call\n\n"
                    full_report += f"```\n{transcript_entry.strip()}\n```\n\n"
                elif "<- TOOL RESULT" in transcript_entry:
                    full_report += "#### Tool Result\n\n"
                    full_report += f"```\n{transcript_entry.strip()}\n```\n\n"
                elif "<< ASSISTANT" in transcript_entry:
                    full_report += "#### Assistant Response\n\n"
                    response_text = transcript_entry.split("<< ASSISTANT:")[1].strip() if "<< ASSISTANT:" in transcript_entry else transcript_entry.strip()
                    full_report += f"{response_text}\n\n"
                elif "/!\\" in transcript_entry and "LOOP DETECTED" in transcript_entry:
                    full_report += "#### Loop Detection Warning\n\n"
                    full_report += f"```\n{transcript_entry.strip()}\n```\n\n"
                else:
                    full_report += f"{transcript_entry}\n\n"
            
            full_report += "---\n\n"
        
        # Final summary
        full_report += "## Final Summary\n\n"
        full_report += final_report
        
        # Save markdown report to run directory
        report_filename = "trend_analysis_report.md"
        report_path = os.path.join(run_dir, report_filename)
        
        with open(report_path, "w") as f:
            f.write(full_report)
        
        # Convert markdown to HTML and save
        try:
            import markdown
            
            # Convert markdown to HTML with extensions for better formatting
            html_content = markdown.markdown(
                full_report,
                extensions=[
                    'extra',           # Tables, footnotes, etc.
                    'codehilite',      # Syntax highlighting
                    'toc',             # Table of contents
                    'fenced_code',     # Code blocks
                    'tables'           # Tables support
                ]
            )
            
            # Wrap in full HTML document with styling
            html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trend Analysis Report - {run_timestamp}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}
        h4 {{
            color: #95a5a6;
            margin-top: 15px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            line-height: 1.4;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
            color: inherit;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 20px 0;
            padding: 10px 20px;
            background-color: #f0f7fb;
        }}
        hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }}
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 8px 0;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        details {{
            margin: 15px 0;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }}
        summary {{
            cursor: pointer;
            font-weight: bold;
            color: #495057;
            padding: 5px;
        }}
        summary:hover {{
            color: #3498db;
        }}
        .toc {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
{html_content}
    </div>
</body>
</html>"""
            
            # Save HTML report
            html_filename = "trend_analysis_report.html"
            html_path = os.path.join(run_dir, html_filename)
            
            with open(html_path, "w") as f:
                f.write(html_document)
            
            info(f"HTML report generated: {html_filename}")
            
        except ImportError:
            error("markdown library not installed - HTML report not generated")
            error("Install with: pip install markdown")
            html_path = None
        except Exception as e:
            error(f"Failed to generate HTML report: {e}")
            html_path = None
        
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info(f"\n[{ts}] Markdown report saved to: {report_path}")
        if html_path:
            info(f"[{ts}] HTML report saved to: {html_path}")
        info(f"[{ts}] Log file saved to: {log_file_path}")
        info(f"[{ts}] CSV files saved to: {csv_output_dir}")
        info(f"[{ts}] Config files saved to: {config_output_dir}")
        
        # Print colored completion message to console
        print(f"\n{Fore.GREEN}{Style.BRIGHT}{'=' * 60}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}Analysis Complete!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Markdown report: {report_path}{Style.RESET_ALL}")
        if html_path:
            print(f"{Fore.GREEN}HTML report: {html_path}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}CSV files: {csv_output_dir}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}{'=' * 60}{Style.RESET_ALL}\n")
        
        return report_path
        
    except Exception as e:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error(f"\n[{ts}] Analysis failed: {e}")
        raise
