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

### Pattern 1: Hospital Readmission Deep Dive
```python
# Step 1: Overall IP trend
filters=[{"dimension_name": "channel", "operator": "=", "value": "IP"}]

# Step 2: By condition
group_by=["ccsr_description"]

# Step 3: Top readmission conditions
# Look for conditions with high utilization_pkpy in 2024 vs 2023

# Step 4: Provider-level
group_by=["provider_group_name", "ccsr_description"]
filters=[{"dimension_name": "ccsr_description", "operator": "IN", "value": ["CHF", "COPD"]}]

# Step 5: Calculate readmission impact
# Compare allowed_pmpm for high-readmission providers vs. benchmark
```

### Pattern 2: Cost Driver Decomposition
```python
# Step 1: Overall trend
# No filters, just get total allowed_pmpm

# Step 2: By service type
group_by=["channel"]  # IP, OP, Pharmacy

# Step 3: Within largest driver (e.g., IP)
filters=[{"dimension_name": "channel", "operator": "=", "value": "IP"}]
group_by=["ccsr_system_description"]

# Step 4: Specific condition
filters=[{"dimension_name": "ccsr_system_description", "operator": "=", "value": "Cardiovascular"}]
group_by=["ccsr_description"]

# Step 5: Provider impact
group_by=["provider_group_name"]
```
