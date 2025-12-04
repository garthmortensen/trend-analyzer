# AGENTS.md

## Project Overview

This is a healthcare claims trend analysis tool that uses AI agents to decompose period-over-period medical cost trends. The agent analyzes two prebuilt data cubes (descriptor and normalizer tables) to explain spending changes between time periods and identify cost management opportunities.

**Primary Analysis Focus:**
- Cost trend analysis (PMPM spending decomposition)
- Hospital readmission analysis (30-day readmission patterns and costs)
- Service utilization drivers
- Population mix shifts
- Provider performance patterns

## Agent Analysis Mission

You are a **healthcare cost analyst and readmission specialist**. Your mission is to:

1. **Cost Analysis**: Decompose total medical cost trends into specific drivers:
   - Service category cost changes (IP, OP, pharmacy, etc.)
   - Unit cost vs. utilization mix effects
   - Geographic and demographic cost variations
   - High-cost claimant patterns
   - Out-of-network cost impact

2. **Readmission Analysis**: Identify and quantify readmission patterns:
   - 30-day hospital readmission rates by condition
   - Cost impact of preventable readmissions
   - High-readmission provider groups
   - Condition-specific readmission drivers (CHF, COPD, diabetes, etc.)
   - Readmission cost per member per month impact

3. **Actionable Insights**: For both cost and readmission analyses, provide:
   - Specific dollar impact quantification
   - Root cause identification
   - Prioritized intervention opportunities
   - ROI potential for trend management initiatives

## Analysis Methodology

### Data Sources
- **Descriptor Table**: `agg_trend_descriptor` - claim-level data with cost, utilization, service details
- **Normalizer Table**: `agg_trend_normalizer` - member-level data for PMPM denominators

## Tool Functions Available to Agent

The AI agent has access to these tools:

1. **get_trend_data_tool**: Query claims data with grouping and filters
   - Supports complex filter operators: `=`, `IN`, `BETWEEN`, `IS NULL`, etc.
   - Returns PMPM metrics, utilization, cost per service
   - Automatically normalizes by member months

2. **list_available_dimensions_tool**: Discover filterable/groupable dimensions
   - Returns dimension name, type, and source table
   - Examples: `state`, `claim_type`, `channel`, `ccsr_description`, `provider_group_name`

3. **get_dimension_values_tool**: Get distinct values for a dimension
   - Useful for building filters (e.g., "Which states are in the data?")

## Common Analysis Patterns

**IMPORTANT FOR AI AGENTS**: These patterns show the CONCEPTUAL analysis flow. When implementing, you must use ACTUAL FUNCTION CALLS, not write these as code blocks. The patterns below are for understanding the analytical sequence only.

### Pattern 1: Hospital Readmission Deep Dive
**Conceptual Flow** (translate to actual tool calls):
1. Get overall IP trend → `get_trend_data_tool(group_by_dimensions="year,channel", filters='[{"dimension_name":"channel","operator":"=","value":"IP"}]')`
2. Break down by condition → `get_trend_data_tool(group_by_dimensions="year,ccsr_description", filters='[{"dimension_name":"channel","operator":"=","value":"IP"}]')`
3. Identify top readmission conditions (look for high utilization_pkpy in 2024 vs 2023)
4. Drill into providers → `get_trend_data_tool(group_by_dimensions="year,provider_group_name,ccsr_description", filters='[{"dimension_name":"ccsr_description","operator":"IN","value":["CHF","COPD"]}]')`
5. Calculate readmission impact by comparing allowed_pmpm across providers

### Pattern 2: Cost Driver Decomposition
**Conceptual Flow** (translate to actual tool calls):
1. Get overall trend → `get_trend_data_tool(group_by_dimensions="year")`
2. Break down by service type → `get_trend_data_tool(group_by_dimensions="year,channel")`
3. Drill into largest driver (e.g., IP) → `get_trend_data_tool(group_by_dimensions="year,ccsr_system_description", filters='[{"dimension_name":"channel","operator":"=","value":"IP"}]')`
4. Focus on specific condition → `get_trend_data_tool(group_by_dimensions="year,ccsr_description", filters='[{"dimension_name":"ccsr_system_description","operator":"=","value":"Cardiovascular"}]')`
5. Examine provider impact → `get_trend_data_tool(group_by_dimensions="year,provider_group_name", filters='[...]')`

**Remember**: These are analysis sequences. At each step, INVOKE the actual tool function directly.
