#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/agent.py
# role: ai_agent
# desc: minimal AI agent for trend analysis using openai-agents SDK
# === FILE META CLOSING ===

import json
import os
from datetime import datetime


from agents import Agent, Runner, function_tool, RunConfig

from .logging_config import info, debug, error
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
    top_n: int = 100
) -> str:
    """
    Retrieve trend data from the descriptor table with optional grouping and filtering.
    
    Args:
        group_by_dimensions: Comma-separated dimension names to group by (e.g. "state,year")
        filters: JSON string of filter list, e.g. '[{"dimension_name":"state","operator":"in","value":["CA","NY"]}]'
        top_n: Maximum number of rows to return (default 100)
        
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
- list_available_dimensions_tool: See all available dimensions
- get_dimension_values_tool: Get distinct values for a dimension

Analysis Approach:
1. Start by understanding what dimensions are available
2. Query high-level trends (state, year, major categories)
3. Drill down into specific areas showing large changes
4. Form hypotheses and test them with targeted queries
5. Provide clear findings and recommendations

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
- Middle iterations: Drill into specific findings
- Final iterations: Synthesize insights and provide recommendations

When you've completed your analysis, clearly state your final findings and recommendations.
"""


# ───────────────────────────────
# Agent Creation and Execution
# ───────────────────────────────

async def create_analysis_agent(iterations: int = 10) -> Agent:
    """Create the trend analysis agent with tools and instructions."""
    
    prompt = make_analysis_prompt(iterations)
    
    agent = Agent(
        name="Trend Analysis Agent",
        instructions=prompt,
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        tools=[
            get_trend_data_tool,
            list_available_dimensions_tool,
            get_dimension_values_tool
        ]
    )
    
    return agent


async def run_once_streamed(agent: Agent, user_msg: str, max_turns: int = 10):
    """Run the agent once with streaming output and capture transcript."""
    
    transcript = []
    
    result = Runner.run_streamed(
        agent,
        input=user_msg,
        max_turns=max_turns,
        run_config=RunConfig(tracing_disabled=True),
    )
    
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
                info(f"\n[{ts}] >> THOUGHT:")
                print(thought)
                transcript.append(f"\n[{ts}] >> THOUGHT:\n{thought}")
        
        # Tool call
        elif it.type == "tool_call_item":
            ts = timestamp()
            info(f"[{ts}] -> TOOL: {it.raw_item.name}")
            debug(f"   Args: {json.dumps(it.raw_item.arguments, indent=2)}")
            transcript.append(f"\n[{ts}] -> TOOL: {it.raw_item.name}")
            transcript.append(f"   Args: {json.dumps(it.raw_item.arguments, indent=2)}")
        
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
    
    return result, transcript


async def run_analysis(iterations: int = 10) -> str:
    """
    Run the main trend analysis loop.
    
    Args:
        iterations: Maximum number of analysis iterations
        
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
    
    # Create agent
    agent = await create_analysis_agent(iterations)
    
    # Start analysis
    ts = timestamp()
    info(f"\n[{ts}] *** ITERATION 1: Initial exploration ***\n")
    
    try:
        result, transcript = await run_once_streamed(
            agent,
            user_msg="Begin the trend analysis. Start by understanding what data is available.",
            max_turns=iterations
        )
        
        # Extract final output
        final_report = result.final_output or "Analysis completed but no final output generated."
        
        ts = timestamp()
        end_ts = timestamp()
        info("\n" + "=" * 60)
        info(f"[{ts}] === ANALYSIS COMPLETE ===")
        info("=" * 60)
        
        # Get metadata
        db_config = config.get_database_config()
        analysis_config = config.get_analysis_config()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
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
