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

from ..logging_config import info, debug, error, warning
from ..config import config
from .tools import (
    get_trend_data_tool,
    list_available_dimensions_tool,
    get_dimension_values_tool,
    save_query_to_csv_tool,
    timestamp,
)
from .prompts import make_analysis_prompt


# ───────────────────────────────
# Agent Creation
# ───────────────────────────────

# async def: This function is async to maintain consistency with the async execution pattern
# used throughout the SDK. While it doesn't perform async I/O itself, it's called from
# async contexts (run_analysis) and returns an Agent that will be used in async operations.
async def create_analysis_agent(iterations: int = 10, model: str = None, timeout: int = None) -> Agent:
    """Create the trend analysis agent with tools and instructions.
    
    Args:
        iterations: Maximum number of analysis iterations
        model: OpenAI model name (from config or env)
        timeout: API timeout in seconds (from config or env)
    """
    
    prompt = make_analysis_prompt(iterations)
    
    # Use provided model or fall back to env var or default
    if model is None:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    agent = Agent(
        name="Trend Analysis Agent",
        instructions=prompt,
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
async def run_once_streamed(agent: Agent, user_msg: str, iteration_num: int = 1, max_turns: int = 50):
    """Run the agent for one iteration (allows multiple tool calls within the turn).
    
    Args:
        agent: The agent instance
        user_msg: User message or conversation history
        iteration_num: Current iteration number (for logging)
        max_turns: Maximum turns for this iteration (default: 50, set high to let agent work)
    
    Returns:
        Tuple of (result, transcript, tool_call_count, max_turns_exceeded)
    """
    
    transcript = []
    tool_call_count = 0
    max_turns_exceeded = False
    
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
            
            # Model reasoning (PLAN/REFLECT)
            if it.type == "reasoning_item":
                thought = "\n".join(
                    s.text for s in it.raw_item.summary
                    if s.type == "summary_text"
                )
                if thought:
                    ts = timestamp()
                    info(f"\n[{ts}] >> THOUGHT (Iteration {iteration_num}):")
                    print(thought)
                    transcript.append(f"\n[{ts}] >> THOUGHT (Iteration {iteration_num}):\n{thought}")
            
            # Tool call
            elif it.type == "tool_call_item":
                tool_call_count += 1
                ts = timestamp()
                
                # Format args in a readable way without escape characters
                args_dict = it.raw_item.arguments
                formatted_args = []
                for key, value in args_dict.items():
                    # Handle string values that might be JSON
                    if isinstance(value, str) and value.startswith('['):
                        try:
                            # Try to parse as JSON for better formatting
                            parsed = json.loads(value)
                            formatted_args.append(f"     {key}: {json.dumps(parsed, indent=6)}")
                        except:
                            formatted_args.append(f"     {key}: {value}")
                    else:
                        formatted_args.append(f"     {key}: {value}")
                
                args_text = "\n".join(formatted_args)
                
                info(f"[{ts}] -> TOOL #{tool_call_count}: {it.raw_item.name}")
                info(f"   Args:\n{args_text}")
                transcript.append(f"\n[{ts}] -> TOOL #{tool_call_count}: {it.raw_item.name}")
                transcript.append(f"   Args:\n{args_text}")
            
            # Tool result
            elif it.type == "tool_call_output_item":
                tname = getattr(it, "tool_call", None)
                tname = tname.name if tname else "<unknown>"
                # Result is logged by the tool itself
            
            # Assistant message
            elif it.type == "message_output_item":
                from agents.items import ItemHelpers
                msg = ItemHelpers.text_message_output(it)
                ts = timestamp()
                info(f"\n[{ts}] << ASSISTANT:")
                print(msg)
                transcript.append(f"\n[{ts}] << ASSISTANT:\n{msg}")
    
    except Exception as e:
        # Catch MaxTurnsExceeded or other errors and continue to return results
        from agents.exceptions import MaxTurnsExceeded
        if isinstance(e, MaxTurnsExceeded):
            max_turns_exceeded = True
            ts = timestamp()
            warning_msg = f"Max turns ({max_turns}) exceeded. Analysis incomplete."
            warning(f"[{ts}] {warning_msg}")
            transcript.append(f"\n[{ts}] >> WARNING: {warning_msg}")
        else:
            # Re-raise other exceptions
            raise
    
    return result, transcript, tool_call_count, max_turns_exceeded


# ───────────────────────────────
# Main Analysis Orchestration
# ───────────────────────────────

# async def: Main entry point for agent execution. Must be async because it:
# 1. Calls await create_analysis_agent() to create the agent
# 2. Calls await run_once_streamed() which performs async streaming I/O
# 3. Uses asyncio to coordinate multiple async operations (agent creation, execution, streaming)
async def run_analysis(iterations: int = 10) -> str:
    """
    Run the main trend analysis loop.
    
    Configuration is loaded from config/analysis.yml:
    - analyze.max_iterations: Number of analysis iterations
    - analyze.openai_model: OpenAI model to use
    - analyze.openai_timeout_seconds: API timeout
    
    Environment variables can override these settings:
    - AGENT_MAX_ITERATIONS
    - OPENAI_MODEL
    - OPENAI_TIMEOUT_SECONDS
    
    Args:
        iterations: Maximum number of analysis iterations (usually from config)
        
    Returns:
        Final analysis report as string
    """
    ts = timestamp()
    info("=" * 60)
    info(f"[{ts}] Starting Trend Analysis Agent")
    info(f"[{ts}] Max iterations: {iterations}")
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
    
    # Create agent
    agent = await create_analysis_agent(iterations, model=model, timeout=timeout)
    
    # Run analysis in single session with max_turns = iterations (each turn can have multiple tool calls)
    ts = timestamp()
    info("\n" + "=" * 60)
    info(f"[{ts}] Starting Analysis Session")
    info(f"[{ts}] Max turns: {iterations}")
    info("=" * 60)
    
    try:
        user_msg = f"""Begin the trend analysis. You have up to {iterations} turns to complete your analysis.
        
Start by understanding what data is available, then systematically drill down into the key drivers.

CRITICAL: As you discover important findings, use save_query_to_csv_tool to preserve the data.
Save at least 3-5 CSV files showing:
- Key cost drivers or trends
- Year-over-year comparisons
- Top conditions, states, or other segments
- Any data that supports your final conclusions

When you've completed your analysis, provide a clear final summary with recommendations."""
        
        # Run analysis with all turns in one session
        result, transcript, tool_calls, max_turns_exceeded = await run_once_streamed(
            agent,
            user_msg=user_msg,
            iteration_num=1,
            max_turns=iterations
        )
        
        # Extract final output - handle case where max turns reached
        if max_turns_exceeded or not result.final_output:
            # Max turns reached - extract latest assistant message from transcript
            final_report = f"ANALYSIS INCOMPLETE: Max turns ({iterations}) reached.\n\n"
            final_report += "Latest analysis state:\n"
            
            # Find last assistant message in transcript
            last_assistant_msg = None
            for i in range(len(transcript) - 1, -1, -1):
                if "<< ASSISTANT:" in transcript[i]:
                    # Get the next line which contains the actual message
                    if i + 1 < len(transcript):
                        last_assistant_msg = transcript[i + 1]
                    break
            
            if last_assistant_msg:
                final_report += last_assistant_msg
            else:
                final_report += "No final summary available. See transcript for analysis progress."
        else:
            final_report = result.final_output
        
        ts = timestamp()
        end_ts = timestamp()
        info("\n" + "=" * 60)
        info(f"[{ts}] === ANALYSIS COMPLETE ===")
        info(f"[{ts}] Total tool calls made: {tool_calls}")
        info("=" * 60)
        
        # Get metadata
        db_config = config.get_database_config()
        analysis_config = config.get_analysis_config()
        # model is already set earlier in run_analysis
        
        # Combine transcript with final report
        full_report = "=" * 60 + "\n"
        full_report += "TREND ANALYSIS REPORT\n"
        full_report += "=" * 60 + "\n\n"
        
        # Add metadata
        full_report += "REPORT METADATA:\n"
        full_report += "-" * 60 + "\n"
        full_report += f"Generated: {end_ts}\n"
        full_report += f"AI Model: {model}\n"
        full_report += f"Max Iterations: {iterations}\n"
        full_report += f"Database: {db_config.get('name', 'N/A')}\n"
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
        full_report += "ANALYSIS TRANSCRIPT:\n"
        full_report += "\n".join(transcript)
        full_report += "\n\n" + "=" * 60 + "\n"
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
        
        ts = timestamp()
        info(f"\n[{ts}] Report saved to: {output_file}")
        
        return full_report
        
    except Exception as e:
        ts = timestamp()
        error(f"\n[{ts}] Analysis failed: {e}")
        raise
