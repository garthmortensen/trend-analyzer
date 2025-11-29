# Structured Output for Agent Responses

## Overview
Implement JSON Schema validation for agent iteration responses to ensure consistent, parseable output structure.

## Benefits
- **Consistency**: Enforces required sections (PLAN, ACTION, REFLECT) and prevents output drift
- **Parse reliability**: Downstream code can consume outputs without brittle regex
- **Validation & testing**: Unit test agent responses; catch missing fields early
- **Evolvability**: Version the schema and add fields without breaking consumers
- **Analytics**: Easier to measure coverage (dimensions explored, CSV exports)
- **Guardrails**: Reject malformed outputs before propagation

## JSON Schema
Location: `src/trend_analyzer/agent/iteration_response.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://trend-analyzer.example/schemas/iteration-response.json",
  "title": "IterationResponse",
  "type": "object",
  "required": ["iteration_number", "phase", "plan", "actions", "reflect"],
  "additionalProperties": false,
  "properties": {
    "iteration_number": { "type": "integer", "minimum": 1 },
    "phase": {
      "type": "string",
      "enum": ["exploration", "pre_final", "synthesis", "final"]
    },
    "plan": { "type": "string", "minLength": 5 },
    "actions": {
      "type": "array",
      "maxItems": 3,
      "items": {
        "type": "object",
        "required": ["tool_name", "arguments"],
        "additionalProperties": false,
        "properties": {
          "tool_name": {
            "type": "string",
            "enum": [
              "get_trend_data_tool",
              "list_available_dimensions_tool",
              "get_dimension_values_tool",
              "save_query_to_csv_tool"
            ]
          },
          "arguments": { "type": "object" }
        }
      }
    },
    "reflect": { "type": "string", "minLength": 10 },
    "saved_csv": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["description", "corresponding_action_index"],
        "additionalProperties": false,
        "properties": {
          "description": { "type": "string", "minLength": 3 },
          "corresponding_action_index": { "type": "integer", "minimum": 0 }
        }
      }
    },
    "meta": {
      "type": "object",
      "description": "Optional metadata (versioning, timing, token counts)",
      "additionalProperties": true
    }
  }
}
```

## Validator Utility
Add to `src/trend_analyzer/agent/validation.py`:

```python
import json
from pathlib import Path
from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).with_name("iteration_response.schema.json")
_validator = Draft202012Validator(json.loads(_SCHEMA_PATH.read_text()))

def validate_iteration_response(payload: dict) -> list[str]:
    """Return list of validation error messages (empty if valid)."""
    errors = []
    for err in _validator.iter_errors(payload):
        errors.append(f"{err.message} (path: {'/'.join(map(str, err.path))})")
    return errors
```

## Integration
1. Parse agent output to dict
2. Call `validate_iteration_response(parsed_output)`
3. Log/raise if errors list is non-empty
4. Add unit tests with valid/invalid fixtures

## Dependencies
Add to `pyproject.toml`:
```toml
jsonschema = "^4.20.0"
```

## Future Extensions
- Final report schema variant
- Confidence scores per finding
- Driver impact quantification structure
- Recommendation prioritization fields
