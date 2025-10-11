#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/data_access.py
# role: data_access
# desc: PostgreSQL data access for trend analyzer (queries prebuilt descriptor/norm tables)
# === FILE META CLOSING ===

print("Loading data_access module...")

import json
from typing import Any, Dict, List

from .auth import get_database_client
from .config import config

# Defaults match SQL files under ./database/
DESCRIPTOR_TABLE = "agg_trend_descriptor"
NORMALIZER_TABLE = "agg_trend_normalizer"


def _get_schema(cfg: Dict[str, Any]) -> str:
    db = cfg.get("database") or {}
    return db.get("schema") or "public"


def _fqtn(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def _fmt(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


_ALLOWED_OPS = {
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "like",
    "ilike",
    "in",
    "not in",
    "between",
    "is null",
    "is not null",
}


def _where(filters: List[Dict[str, Any]]) -> str:
    if not filters:
        return "true"
    parts: List[str] = []
    for f in filters:
        col = f.get("dimension_name") or f.get("column")
        op = str(f.get("operator", "=")).lower().strip()
        val = f.get("value")
        if not col:
            continue
        if op not in _ALLOWED_OPS:
            raise ValueError(f"operator not allowed: {op}")
        if op in ("is null", "is not null"):
            parts.append(f"{col} {op}")
        elif op in ("in", "not in") and isinstance(val, list):
            vals = ", ".join(_fmt(x) for x in val)
            parts.append(f"{col} {op} ({vals})")
        elif op == "between" and isinstance(val, list) and len(val) == 2:
            parts.append(f"{col} between {_fmt(val[0])} and {_fmt(val[1])}")
        else:
            parts.append(f"{col} {op} {_fmt(val)}")
    return " and ".join(parts) if parts else "true"


def _select_list(select_columns: List[str] | None) -> str:
    if not select_columns:
        return "*"
    return ", ".join(select_columns)


def _run_sql(config_dict: Dict[str, Any], sql: str) -> List[Dict[str, Any]]:
    """Run SQL using existing PostgreSQL client; return list of dict rows."""
    db_client = get_database_client(config_dict)
    if not db_client:
        return []
    try:
        df = db_client.run_query(sql)
        if df is None:
            return []
        # Convert DataFrame to list[dict]
        return [
            {k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}
            for row in df.to_dict(orient="records")
        ]
    except Exception:
        return []


def get_trend_data_from_config(config_data):
    """Select rows from prebuilt descriptor table with optional filtering and projection."""
    print("[INFO] Selecting trend data from prebuilt tables...")

    analysis_cfg = (config_data or {}).get("analyze", {}) or {}
    # optional: allow explicit projection via select_columns; otherwise return all columns
    select_columns = analysis_cfg.get("select_columns")
    filters = analysis_cfg.get("filters", []) or []
    top_n = analysis_cfg.get("top_n")

    # database/schema from config
    db_cfg = {"database": (config_data or {}).get("database") or config.get_database_config()}
    schema = _get_schema(db_cfg)
    descriptor_fqtn = _fqtn(schema, DESCRIPTOR_TABLE)

    sql = f"""
        select {_select_list(select_columns)}
        from {descriptor_fqtn}
        where {_where(filters)}
        order by 1
        {f'limit {int(top_n)}' if top_n else ''}
    """.strip()

    rows = _run_sql(db_cfg, sql)

    return {
        "data": json.dumps(rows, default=str),
        "sql": sql,
        "tables": {"descriptor": descriptor_fqtn, "normalizer": _fqtn(schema, NORMALIZER_TABLE)},
        "config_summary": {
            "select_columns": select_columns or "*",
            "filter_count": len(filters),
            "top_n": top_n,
            "database_type": (db_cfg.get("database") or {}).get("type", "postgresql"),
        },
    }


# legacy helper removed per ADR-004; use get_trend_data_from_config directly


def list_available_dimensions(config_data):
    """Return available columns for descriptor table from information_schema."""
    print("[INFO] Listing available columns from descriptor table...")

    db_cfg = {"database": (config_data or {}).get("database") or config.get_database_config()}
    schema = _get_schema(db_cfg)

    sql = f"""
        select column_name, data_type
        from information_schema.columns
        where table_schema = {_fmt(schema)}
          and table_name = {_fmt(DESCRIPTOR_TABLE)}
        order by ordinal_position
    """.strip()

    rows = _run_sql(db_cfg, sql)
    dims = {r.get("column_name"): r.get("data_type") for r in rows} if rows else {}
    return {"data": json.dumps(dims, indent=2)}


def get_dimension_values(dimension_name, config_data):
    """Get distinct values for a given column from the descriptor table."""
    print(f"[INFO] Getting values for column: {dimension_name}")

    db_cfg = {"database": (config_data or {}).get("database") or config.get_database_config()}
    schema = _get_schema(db_cfg)
    descriptor_fqtn = _fqtn(schema, DESCRIPTOR_TABLE)

    sql = f"""
        select distinct {dimension_name} as v
        from {descriptor_fqtn}
        where {dimension_name} is not null
        order by 1
        limit 500
    """.strip()

    rows = _run_sql(db_cfg, sql)
    values = [r.get("v") for r in rows] if rows else []
    return {"data": json.dumps(values, default=str)}