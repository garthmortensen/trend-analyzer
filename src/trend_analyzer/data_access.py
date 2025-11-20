#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/data_access.py
# role: data_access
# desc: PostgreSQL data access for trend analyzer (queries prebuilt descriptor/norm tables)
# === FILE META CLOSING ===

print("Loading data_access module...")

import json
from typing import Any, Dict, List, Optional, Tuple
import os

from .auth import get_database_client
from .config import config
from sqlalchemy import MetaData, Table, select, and_, create_engine

"""Simple data access for prebuilt tables using SQLAlchemy Core.

Why this approach:
- Reflect table schema at runtime (no hard-coded columns)
- Build where/order/limit using SQLAlchemy expressions (safer and readable)
- Keep helpers minimal and obvious
"""

# Defaults match SQL files under ./database/
DESCRIPTOR_TABLE = "agg_trend_descriptor"
NORMALIZER_TABLE = "agg_trend_normalizer"


# Basic client compatibility with the notebook (module scope)
def get_client(config_data: Optional[Dict[str, Any]] = None):
    """Return a SQLAlchemy Engine built from config (notebook-compatible)."""
    database_config = (
        (config_data or {}).get("database")
    ) or config.get_database_config()
    username = os.getenv(
        "DB_USERNAME", database_config.get("username") or database_config.get("user")
    )
    password = os.getenv(
        "DB_PASSWORD", database_config.get("password") or database_config.get("pass")
    )
    host = database_config.get("host", "localhost")
    port = int(database_config.get("port", 5432))
    database_name = (
        database_config.get("database") or database_config.get("dbname") or "postgres"
    )
    url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database_name}"
    return create_engine(url, future=True)


def run_query(
    sql: str,
    params: Optional[Dict[str, Any]] = None,
    config_data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute arbitrary SQL and return rows as list[dict] (notebook-compatible)."""
    engine = get_client(config_data)
    with engine.connect() as connection:
        result = connection.execute(sql, params or {})
        return [dict(r._mapping) for r in result]


def _get_schema(cfg: Dict[str, Any]) -> str:
    """Return configured schema or default to 'public'."""
    db = cfg.get("database") or {}
    return db.get("schema") or "public"


def _fqtn(schema: str, table: str) -> str:
    return f"{schema}.{table}"


def _get_engine(config_dict: Dict[str, Any]):
    """Create or reuse a SQLAlchemy engine via the existing db client."""
    client = get_database_client(config_dict)
    if not client:
        return None
    try:
        ok = client.connect()
        return client.engine if ok else None
    except Exception:
        return None


def _reflect_table(engine, schema: str, table_name: str):
    """Reflect a table given schema and name."""
    md = MetaData()
    return Table(table_name, md, autoload_with=engine, schema=schema)


def _build_clause(table: Table, filters: List[Dict[str, Any]]):
    """Translate a simple filter dict list into SQLAlchemy expressions.

    Supports operators: =, !=, >, >=, <, <=, like, ilike, in, between, is null, is not null
    Skips invalid columns silently (keeps things forgiving for user-provided filters).
    """
    if not filters:
        return None
    clauses = []
    for f in filters:
        col_name = (f.get("dimension_name") or f.get("column") or "").strip()
        if not col_name or col_name not in table.c:
            continue
        col = table.c[col_name]
        op = str(f.get("operator", "=")).lower().strip()
        val = f.get("value")
        if op == "is null":
            clauses.append(col.is_(None))
        elif op == "is not null":
            clauses.append(col.is_not(None))
        elif op == "in" and isinstance(val, list):
            clauses.append(col.in_(val))
        elif op == "between" and isinstance(val, list) and len(val) == 2:
            clauses.append(col.between(val[0], val[1]))
        elif op == "like":
            clauses.append(col.like(val))
        elif op == "ilike":
            clauses.append(col.ilike(val))
        elif op == "!=":
            clauses.append(col != val)
        elif op == ">":
            clauses.append(col > val)
        elif op == ">=":
            clauses.append(col >= val)
        elif op == "<":
            clauses.append(col < val)
        elif op == "<=":
            clauses.append(col <= val)
        else:  # default '='
            clauses.append(col == val)
    return and_(*clauses) if clauses else None


def _execute(engine, stmt) -> List[Dict[str, Any]]:
    try:
        with engine.connect() as conn:
            res = conn.execute(stmt)
            return [dict(r._mapping) for r in res]
    except Exception:
        return []


def _pagination_params(analysis_cfg: Dict[str, Any]) -> Tuple[int, int]:
    """Return page and page_size as ints with sane bounds."""
    page = analysis_cfg.get("page")
    page_size = analysis_cfg.get("page_size")
    try:
        page = int(page) if page is not None else 1
    except Exception:
        page = 1
    try:
        page_size = int(page_size) if page_size is not None else 100
    except Exception:
        page_size = 100
    if page < 1:
        page = 1
    # Clamp page_size between 1 and 10_000 to prevent blowups
    page_size = max(1, min(page_size, 10_000))
    return page, page_size


def get_trend_data_from_config(config_data):
    """Select rows from prebuilt descriptor table with optional filtering and projection."""
    print("[INFO] Selecting trend data from prebuilt tables...")

    analysis_config = (config_data or {}).get("analyze", {}) or {}
    # choose columns to return (optional); otherwise return the full row
    select_columns = analysis_config.get("select_columns")
    filters = analysis_config.get("filters", []) or []
    top_n = analysis_config.get("top_n")
    # Only parse pagination if page or page_size explicitly provided
    page = analysis_config.get("page")
    page_size = analysis_config.get("page_size")
    if page is not None or page_size is not None:
        page, page_size = _pagination_params(analysis_config)
    else:
        page, page_size = None, None

    # database/schema from config
    database_config = {
        "database": (config_data or {}).get("database") or config.get_database_config()
    }
    schema = _get_schema(database_config)

    engine = _get_engine(database_config)
    if engine is None:
        return {
            "data": json.dumps([], default=str),
            "sql": "",
            "tables": {},
            "config_summary": {},
        }

    # reflect the descriptor table defined in database/*.sql
    descriptor_table = _reflect_table(engine, schema, DESCRIPTOR_TABLE)

    # projection list (fall back to full row if none valid)
    if select_columns:
        columns_to_select = [
            descriptor_table.c[c] for c in select_columns if c in descriptor_table.c
        ]
        if not columns_to_select:
            columns_to_select = [descriptor_table]
    else:
        columns_to_select = [descriptor_table]

    # build select with optional where/order/limit
    query = select(*columns_to_select)
    where_clause = _build_clause(descriptor_table, filters)
    if where_clause is not None:
        query = query.where(where_clause)
    if select_columns:
        # order by first selected column for deterministic results
        query = query.order_by(columns_to_select[0])
    if top_n is not None:
        # Explicit top_n specified - use it
        try:
            query = query.limit(int(top_n))
        except Exception:
            pass
    elif page_size and page:
        # Pagination requested via page_size/page
        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)
    # else: No limit - return all rows

    # best-effort: compile a literal SQL string for transparency/debugging
    try:
        sql_compiled = str(
            query.compile(engine, compile_kwargs={"literal_binds": True})
        )
    except Exception:
        sql_compiled = ""

    rows = _execute(engine, query)

    return {
        "data": json.dumps(rows, default=str),
        "sql": sql_compiled,
        "tables": {
            "descriptor": _fqtn(schema, DESCRIPTOR_TABLE),
            "normalizer": _fqtn(schema, NORMALIZER_TABLE),
        },
        "config_summary": {
            "select_columns": select_columns or "*",
            "filter_count": len(filters),
            "top_n": top_n,
            "page": page,
            "page_size": page_size,
            "database_type": (database_config.get("database") or {}).get(
                "type", "postgresql"
            ),
        },
    }


def list_available_dimensions(config_data):
    """Return available columns for descriptor table (name -> type)."""
    print("[INFO] Listing available columns from descriptor table...")

    database_config = {
        "database": (config_data or {}).get("database") or config.get_database_config()
    }
    schema = _get_schema(database_config)

    engine = _get_engine(database_config)
    if engine is None:
        return {"data": json.dumps({}, indent=2)}
    descriptor_table = _reflect_table(engine, schema, DESCRIPTOR_TABLE)
    dims = {c.name: str(c.type) for c in descriptor_table.columns}
    return {"data": json.dumps(dims, indent=2)}


def get_dimension_values(dimension_name, config_data):
    """Get distinct non-null values for a given column from the descriptor table."""
    print(f"[INFO] Getting values for column: {dimension_name}")

    database_config = {
        "database": (config_data or {}).get("database") or config.get_database_config()
    }
    schema = _get_schema(database_config)

    engine = _get_engine(database_config)
    if engine is None:
        return {"data": json.dumps([], default=str)}
    descriptor_table = _reflect_table(engine, schema, DESCRIPTOR_TABLE)
    col = str(dimension_name)
    if col not in descriptor_table.c:
        return {"data": json.dumps([], default=str)}

    stmt = (
        select(descriptor_table.c[col].label("v"))
        .where(descriptor_table.c[col].is_not(None))
        .distinct()
        .order_by(descriptor_table.c[col])
        .limit(500)
    )
    rows = _execute(engine, stmt)
    values = [r.get("v") for r in rows] if rows else []
    return {"data": json.dumps(values, default=str)}
