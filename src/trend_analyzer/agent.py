#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/agent.py
# role: ai_agent
# desc: minimal AI agent for trend analysis using openai-agents SDK
# === FILE META CLOSING ===

import json
import os
import csv
from datetime import datetime
from pathlib import Path


from agents import Agent, Runner, function_tool, RunConfig

from .logging_config import info, debug, error, warning
from .data_access import get_trend_data_from_config, list_available_dimensions, get_dimension_values
from .config import config


def timestamp():
    """Get current timestamp in log format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ───────────────────────────────
# Wrap data access functions as tools
# ───────────────────────────────

@function_tool
async def get_trend_data_tool(
    group_by_dimensions: str = "",
    filters: str = "",
    top_n: int = 999
) -> str:
    """
    Retrieve trend data from the descriptor table with optional grouping and filtering.
    
    Args:
        group_by_dimensions: Comma-separated dimension names to group by (e.g. "state,year")
        filters: JSON string of filter list, e.g. '[{"dimension_name":"state","operator":"in","value":["CA","NY"]}]'
        top_n: Maximum number of rows to return. Default 999 (effectively unlimited). Use small values (10-20) only for quick previews.
        
    Returns:
        JSON string with analysis results including data, SQL, and config summary
    """
    try:
        # Parse inputs
        group_by_list = [d.strip() for d in group_by_dimensions.split(",") if d.strip()]
        filters_list = json.loads(filters) if filters else []
        
        # Build config for data access function
        config_data = {
            "database": config.get_database_config(),
            "analyze": {
                "group_by_dimensions": group_by_list,
                "filters": filters_list,
                "top_n": top_n
            }
        }
        
        result = get_trend_data_from_config(config_data)
        
        # Log the SQL query executed
        if "sql" in result:
            info(f">> SQL Query Executed:\n{result['sql']}")
        
        # Parse the data to show summary
        rows = json.loads(result["data"])
        info(f"   Success: {len(rows)} rows returned")
        
        # Format response for agent
        response = f"""
TREND DATA ANALYSIS RESULTS:

Configuration:
- Grouping: {', '.join(group_by_dimensions) if group_by_dimensions else 'None'}
- Filters Applied: {len(filters) if filters else 0}
- Top N Limit: {top_n or 'All records'}
- Total Rows Returned: {len(rows)}

Data Sample (first 3 rows):
{json.dumps(rows[:3], indent=2, default=str)}

<!-- TRUNCATABLE_DATA_BLOCK -->
"""
        return response
        
    except Exception as e:
        error(f"   Tool error: {str(e)}")
        return f"Error retrieving trend data: {str(e)}"


@function_tool
async def list_available_dimensions_tool() -> str:
    """
    List all available dimensions that can be used for grouping and filtering.
    
    Returns:
        Formatted list of dimensions with descriptions
    """
    try:
        config_data = {"database": config.get_database_config()}
        result = list_available_dimensions(config_data)
        
        # Log the SQL query executed
        if "sql" in result:
            info(f">> SQL Query Executed:\n{result['sql']}")
        
        dims = json.loads(result["data"])
        info(f"   Success: {len(dims)} dimensions found")
        
        response = "AVAILABLE DIMENSIONS:\n\n"
        for dim_name, dim_type in sorted(dims.items()):
            response += f"• {dim_name}: {dim_type}\n"
        
        return response
        
    except Exception as e:
        error(f"   Tool error: {str(e)}")
        return f"Error listing dimensions: {str(e)}"


@function_tool
async def get_dimension_values_tool(dimension_name: str) -> str:
    """
    Get distinct values for a specific dimension.
    
    Args:
        dimension_name: Name of the dimension to get values for
        
    Returns:
        List of distinct values for the dimension
    """
    try:
        config_data = {"database": config.get_database_config()}
        result = get_dimension_values(dimension_name, config_data)
        
        # Log the SQL query executed
        if "sql" in result:
            info(f">> SQL Query Executed:\n{result['sql']}")
        
        values = json.loads(result["data"])
        info(f"   Success: {len(values)} distinct values for '{dimension_name}'")
        
        response = f"DIMENSION VALUES for '{dimension_name}':\n\n"
        
        # Show first 20 values
        display_values = values[:20]
        for i, value in enumerate(display_values, 1):
            response += f"{i:2d}. {value}\n"
        
        if len(values) > 20:
            response += f"... and {len(values) - 20} more values\n"
        
        response += f"\nTotal: {len(values)} distinct values"
        
        return response
        
    except Exception as e:
        error(f"   Tool error: {str(e)}")
        return f"Error getting dimension values for '{dimension_name}': {str(e)}"


@function_tool
async def save_query_to_csv_tool(
    group_by_dimensions: str = "",
    filters: str = "",
    top_n: int = 999,
    description: str = ""
) -> str:
    """
    Execute a query and save the results to a timestamped CSV file in output_data/.
    Use this to preserve intermediate analysis data for later reference.
    The default captures ALL rows - do not specify top_n unless you need to limit results.
    
    Args:
        group_by_dimensions: Comma-separated dimension names to group by (e.g. "state,year")
        filters: JSON string of filter list, e.g. '[{"dimension_name":"state","operator":"in","value":["CA","NY"]}]'
        top_n: Maximum rows (default 999 = all rows). Only specify small values (10-20) if you need a sample.
        description: Brief description of what this query captures (e.g. "Service categories 2023-2024")
        
    Returns:
        Confirmation message with filename and row count
    """
    try:
        # Parse inputs
        group_by_list = [d.strip() for d in group_by_dimensions.split(",") if d.strip()]
        filters_list = json.loads(filters) if filters else []
        
        # Build config for data access function
        config_data = {
            "database": config.get_database_config(),
            "analyze": {
                "group_by_dimensions": group_by_list,
                "filters": filters_list,
                "top_n": top_n
            }
        }
        
        result = get_trend_data_from_config(config_data)
        
        # Log the SQL query executed
        if "sql" in result:
            info(f">> SQL Query for CSV Export:\n{result['sql']}")
        
        # Parse the data
        rows = json.loads(result["data"])
        
        if not rows:
            return "No data returned from query - CSV not created."
        
        # Generate timestamped filename
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output_data")
        output_dir.mkdir(exist_ok=True)
        filename = f"{ts}_data.csv"
        filepath = output_dir / filename
        
        # Write to CSV
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        # Log success
        info(f"   >> CSV Saved: {filepath} ({len(rows)} rows)")
        if description:
            info(f"   >> Description: {description}")
        
        response = f"""
CSV DATA EXPORTED SUCCESSFULLY:

File: {filepath}
Rows: {len(rows)}
Description: {description or 'No description provided'}

Configuration:
- Grouping: {', '.join(group_by_list) if group_by_list else 'None'}
- Filters Applied: {len(filters_list)}
- Top N Limit: {top_n or 'All records'}
"""
        return response
        
    except Exception as e:
        error(f"   Tool error: {str(e)}")
        return f"Error saving query to CSV: {str(e)}"


# ───────────────────────────────
# System Prompt
# ───────────────────────────────

BASE_SYSTEM = """
You are a healthcare trend analysis expert specializing in health insurance claims analysis.

Your goal is to analyze period-over-period trends (2023 vs 2024) in the data and explain
what's driving the changes. Focus on:

1. Identifying the largest cost drivers
2. Understanding utilization patterns
3. Finding anomalies or significant changes
4. Providing actionable insights

Available Tools:
- get_trend_data_tool: Query the claims descriptor table with grouping and filtering
  * Default returns ALL rows (top_n=999)
  * Set top_n=10 or top_n=20 only for quick previews during exploration
- list_available_dimensions_tool: See all available dimensions
- get_dimension_values_tool: Get distinct values for a dimension
- save_query_to_csv_tool: Save query results to CSV file for key intermediate findings
  * Default captures ALL rows - do NOT specify top_n parameter
  * Complete data is crucial for thorough analysis

Analysis Approach:
1. Start by understanding what dimensions are available
2. Query high-level trends with top_n=10 for initial exploration
3. Drill down into specific areas showing large changes
4. **Save COMPLETE datasets to CSV** using save_query_to_csv_tool
   - Do NOT specify top_n parameter - use the default to get all rows
   - This ensures you capture complete data for thorough analysis
   - Add descriptive labels (e.g., "Service categories by state 2023-2024")
5. Form hypotheses and test them with targeted queries
6. Provide clear findings and recommendations based on complete data

Keep your analysis focused and data-driven. Use the PLAN-ACTION-REFLECT pattern:
- PLAN: State your hypothesis
- ACTION: Call the appropriate tool
- REFLECT: Interpret the results and decide next steps
"""


def make_analysis_prompt(iterations: int) -> str:
    """Create the full analysis prompt with iteration limit."""
    return BASE_SYSTEM + f"""

You have {iterations} iterations to complete your analysis. Use them wisely:
- Early iterations: Explore and understand the data
- Middle iterations: Drill into specific findings and **SAVE key data to CSV**
- Final iterations: Synthesize insights and provide recommendations

IMPORTANT: Use save_query_to_csv_tool to preserve intermediate data that supports your findings.
For example:
- Top conditions by cost
- Year-over-year comparisons by state
- High utilization provider groups
- Any data table you reference in your conclusions

When you've completed your analysis, clearly state your final findings and recommendations.
"""


# ───────────────────────────────
# Agent Creation and Execution
# ───────────────────────────────

async def create_analysis_agent(iterations: int = 10, model: str = None, timeout: int = None) -> Agent:
    """Create the trend analysis agent with tools and instructions.
    
    Args:
        iterations: Maximum number of analysis iterations
        model: OpenAI model name (from config or env)
        timeout: API timeout in seconds (from config or env)
    """
    
    prompt = make_analysis_prompt(iterations)
    
    # Use provided model or fall back to env var hhor default
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


async def run_once_streamed(agent: Agent, user_msg: str, iteration_num: int = 1, max_turns: int = 50):
    """Run the agent for one iteration (allows multiple tool calls within the turn).
    
    Args:
        agent: The agent instance
        user_msg: User message or conversation history
        iteration_num: Current iteration number (for logging)
        max_turns: Maximum turns for this iteration (default: 50, set high to let agent work)
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
                tool_args = json.dumps(it.raw_item.arguments, indent=2)
                info(f"[{ts}] -> TOOL #{tool_call_count}: {it.raw_item.name}")
                info(f"   Args: {tool_args}")
                transcript.append(f"\n[{ts}] -> TOOL #{tool_call_count}: {it.raw_item.name}")
                transcript.append(f"   Args: {tool_args}")
            
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


def run_analysis_sync(iterations: int = 10) -> str:
    """Synchronous wrapper for run_analysis."""
    import asyncio
    return asyncio.run(run_analysis(iterations))
