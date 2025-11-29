# Function Tool Surface Refactor

Concise action list to align tools with OpenAI function best practices.

## Objectives
- Reduce cognitive load (keep tool count small; combine sequential steps)
- Make invalid states unrepresentable (typed enums & validation)
- Provide explicit output contracts and edge case behavior
- Eliminate redundant queries & parameter repetition

## Action Items
1. Filter Operator Enum & Validator
   - Introduce `FilterOperator` enum (`=`, `in`, `between`, `ilike`, `is null`, `is not null`).
   - Replace raw JSON operator strings; parse & validate before query.
   - Fail fast with structured error payload `{ "error": ..., "detail": ... }`.
2. Filter Spec Type
   - Add `FilterSpec` dataclass / TypedDict; convert from JSON to internal objects.
   - Enforce presence of `dimension_name` & `operator`; allow `value` only when required.
3. Consolidate Query + Save
   - Add `save: bool` + `description: str` to `get_trend_data_tool`.
   - Deprecate `save_query_to_csv_tool` (leave stub returning deprecation message for one release).
4. Result Handle Caching
   - On query success, issue UUID `handle`; cache raw payload.
   - New lightweight `save_cached_result_tool(handle, description)` for delayed persistence without re-query.
5. Structured Output Contract
   - Explicit keys: `handle`, `rows`, `row_count`, `sql`, `dimensions`, `filters_applied`, `saved_csv?`, `started_at`, `description?`.
   - Document in tool docstring + repo markdown (update `AGENTS.md` section if needed).
6. Edge Case Examples (Docstrings)
   - Empty `group_by_dimensions` (aggregate total). 
   - Invalid dimension name (return error object). 
   - `top_n` > max allowed (clamp & warn). 
   - `filters` empty/whitespace.
7. Constants for Defaults
   - Define `TOP_N_DEFAULT`, `MAX_PREVIEW_ROWS`; reference instead of magic numbers.
8. Structured Errors
   - Standard shape: `{ "error": str, "detail": str|None, "retryable": bool }`.
   - Never raise uncaught exceptions to model; log internally.
9. Discovery Tool Usage Guidance
   - Update docstrings: when NOT to call `list_available_dimensions_tool` / `get_dimension_values_tool` (avoid repeated calls after initial discovery).
10. Docstring Enhancements
    - First sentence = one-line purpose. Then parameter table semantics. Output schema + 2–3 edge cases.
11. Logging Improvements
    - Log: start, sanitized params, row_count, elapsed_ms, saved filename, error classification.
12. Deprecation Plan
    - Mark old save tool: return `{ "deprecated": true, "use": "get_trend_data_tool(save=True) or save_cached_result_tool" }`.
13. Prompt Adjustments
    - Update `prompts.py` to instruct usage of `save` flag and handle caching workflow.

## Sequence (Suggested)
1. Add enums, dataclass, constants.
2. Refactor `get_trend_data_tool` (add save + handle caching + structured output).
3. Implement `save_cached_result_tool`.
4. Deprecate old save tool.
5. Update docstrings & `AGENTS.md` / `copilot-instructions.md` sections.
6. Adjust prompts for new usage.
7. QA: Run agent loop to ensure CSV uniqueness & no duplicate queries for same handle.

## Acceptance Criteria
- All tool docstrings specify input formats & output JSON keys.
- Running a query then saving via handle does not re-run SQL.
- Invalid filter operator returns structured error (no traceback leakage).
- Old save tool clearly flagged deprecated.
- Prompts instruct minimal tool usage pattern.

## Follow-Up (Optional Enhancements)
- Add rate limiting / caching horizon (TTL) for large identical queries.
- Introduce lightweight metrics tool for derived KPIs without full query.
- Unit tests for filter parsing & error shapes.

---
Short and focused; update or prune after implementation to keep lean.
