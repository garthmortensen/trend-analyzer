#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/agent/__init__.py
# role: ai_agent_api
# desc: Public API for the trend analysis agent
# === FILE META CLOSING ===

"""
Trend Analysis Agent

This module provides an AI-powered agent for analyzing healthcare claims trends.
The agent uses OpenAI's Agents SDK to perform exploratory analysis, identify
cost drivers, and generate insights from claims data.

Main entry points:
- run_analysis_sync(): Synchronous wrapper for running the agent
- run_analysis(): Async function for running the agent
- create_analysis_agent(): Factory for creating agent instances

Example:
    from trend_analyzer.agent import run_analysis_sync
    
    report = run_analysis_sync(iterations=10)
    print(report)
"""

import asyncio

from .runner import run_analysis, create_analysis_agent
from .tools import (
    get_trend_data_tool,
    list_available_dimensions_tool,
    get_dimension_values_tool,
    save_query_to_csv_tool,
)
from .prompts import (
    build_base_system_prompt,
    make_analysis_prompt,
)


# ───────────────────────────────
# Synchronous Wrapper
# ───────────────────────────────

# NOT async: This is the synchronous wrapper that allows calling the async run_analysis()
# from synchronous code (like __main__.py). Uses asyncio.run() to create an event loop,
# execute the async function, and return the result. This bridges sync/async boundaries.
def run_analysis_sync(iterations: int = 10) -> str:
    """
    Synchronous wrapper for run_analysis().
    
    Run the trend analysis agent and return the final report.
    This is the recommended entry point for synchronous code.
    
    Args:
        iterations: Maximum number of analysis iterations (default: 10)
        
    Returns:
        Final analysis report as string
    """
    return asyncio.run(run_analysis(iterations))


# ───────────────────────────────
# Public API Exports
# ───────────────────────────────

__all__ = [
    # Main entry points
    "run_analysis_sync",
    "run_analysis",
    "create_analysis_agent",
    # Tools (exported for testing/inspection)
    "get_trend_data_tool",
    "list_available_dimensions_tool",
    "get_dimension_values_tool",
    "save_query_to_csv_tool",
    # Prompts (exported for customization)
    "build_base_system_prompt",
    "make_analysis_prompt",
]
