#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/agent/tools.py
# role: ai_agent_tools
# desc: Function tools that the AI agent can call (data queries, CSV export)
# === FILE META CLOSING ===

import json
import csv
import os
from datetime import datetime
from pathlib import Path

from agents import function_tool

from ..logging_config import info, debug, error
from ..data_access import get_trend_data_from_config, list_available_dimensions, get_dimension_values
from ..config import config


def timestamp():
    """Get current timestamp in log format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ───────────────────────────────
# Agent Function Tools
# ───────────────────────────────

# @function_tool: Decorator from OpenAI Agents SDK that converts a Python function into a tool
# the AI agent can call. It generates JSON schema for function parameters and handles serialization.
#
# async def: Required by OpenAI Agents SDK - all function_tool decorated functions must be async
# even if they don't perform I/O operations. The SDK's Runner uses asyncio for event streaming.

# Another way to say this...
# Take your Python function and its type hints
# Turn it into a tool definition with:
# name (usually the function name)
# description (from the docstring)
# parameters (a JSON Schema built from the arguments + type hints)
# https://platform.openai.com/docs/guides/function-calling

# Register that with the model as a tool of "type": "function".
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
        
        # Parse the data
        rows = json.loads(result["data"])
        # Log summary only (SQL is verbose, goes to report via tool response)
        debug(f"Query returned {len(rows)} rows")
        
        # Format response for agent
        response = f"""
TREND DATA ANALYSIS RESULTS:

Configuration:
- Grouping: {', '.join(group_by_list) if group_by_list else 'None'}
- Filters Applied: {len(filters_list) if filters_list else 0}
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


# @function_tool + async: Same as above - SDK requirement for tool registration and async execution
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
        debug(f"Retrieved {len(dims)} available dimensions")
        
        response = "AVAILABLE DIMENSIONS:\n\n"
        for dim_name, dim_type in sorted(dims.items()):
            response += f"• {dim_name}: {dim_type}\n"
        
        return response
        
    except Exception as e:
        error(f"   Tool error: {str(e)}")
        return f"Error listing dimensions: {str(e)}"


# @function_tool + async: Same as above - SDK requirement for tool registration and async execution
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
        debug(f"Retrieved {len(values)} distinct values for '{dimension_name}'")
        
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


# @function_tool + async: Same as above - SDK requirement for tool registration and async execution
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
        
        # Parse the data
        rows = json.loads(result["data"])
        debug(f"CSV export query returned {len(rows)} rows")
        
        if not rows:
            return "No data returned from query - CSV not created."
        
        # Get run-specific CSV directory from environment variable
        csv_dir = os.environ.get("TREND_ANALYZER_CSV_DIR")
        if csv_dir:
            output_dir = Path(csv_dir)
        else:
            # Fallback to old behavior if not set (backward compatibility)
            output_dir = Path("output_data")
            output_dir.mkdir(exist_ok=True)
        
        # Generate descriptive filename from query parameters
        import hashlib
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create descriptive name from dimensions
        if group_by_list:
            dim_part = "_".join(group_by_list[:3])  # Use first 3 dimensions
        else:
            dim_part = "ungrouped"
        
        # Create hash of query to ensure uniqueness
        query_str = f"{group_by_dimensions}|{filters}|{top_n}"
        query_hash = hashlib.md5(query_str.encode()).hexdigest()[:6]
        
        # Build filename: timestamp_dimensions_hash.csv
        filename = f"{ts}_{dim_part}_{query_hash}.csv"
        filepath = output_dir / filename
        
        # Write to CSV
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        # Log success summary
        info(f"CSV saved: {filepath.name} ({len(rows)} rows)")
        
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
