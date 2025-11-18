#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/ai_runner.py
# role: ai agent runner
# desc: minimal ask() function that uses OpenAI and safely pings Postgres; no CLI
# === FILE META CLOSING ===

import json
import os
import time
from typing import Any, Dict

import yaml
from openai import OpenAI
from sqlalchemy import create_engine, text

# Optionally load .env for local development (non-fatal if package missing)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass


def _load_infrastructure() -> Dict[str, Any]:
    """Load infrastructure.yml for database settings."""
    with open("config/infrastructure.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _make_engine_and_timeout():
    """Create a SQLAlchemy engine and return (engine, timeout_seconds).

    Environment variables override yaml values for 12-factor compatibility.
    """
    cfg = _load_infrastructure()
    db = cfg.get("database", {})

    host = os.environ.get("DB_HOST", db.get("host", "localhost"))
    port = int(os.environ.get("DB_PORT", db.get("port", 5432)))
    name = os.environ.get("DB_NAME", db.get("database", "aca_health"))
    user = os.environ.get("DB_USERNAME", db.get("username", "etl"))
    pwd = os.environ.get("DB_PASSWORD", db.get("password", "etl"))
    timeout_s = int(
        os.environ.get(
            "DB_STATEMENT_TIMEOUT_SECONDS", db.get("statement_timeout_seconds", 30)
        )
    )

    url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"
    engine = create_engine(url, pool_pre_ping=True, future=True)
    return engine, timeout_s


def _db_ping_ms() -> int:
    """Execute a lightweight query with a per-statement timeout and return latency in ms."""
    engine, timeout_s = _make_engine_and_timeout()
    start = time.time()
    timeout_ms = max(1, int(timeout_s * 1000))
    with engine.begin() as conn:
        conn.execute(text(f"set local statement_timeout = {timeout_ms}"))
        conn.execute(text("select 1"))
    return int((time.time() - start) * 1000)


_DEFAULT_OPENAI_TIMEOUT_S = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30"))
_SINGLE_SHOT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "1"))


def ask(
    question: str,
    *,
    max_steps: int = _SINGLE_SHOT_MAX_STEPS,
    timeout_s: int | None = None,
) -> Dict[str, Any]:
    """Minimal entrypoint: derive a concise intent and verify DB connectivity.

    This does NOT run arbitrary SQL. It returns:
      - original question
      - intent extracted by the model (short)
      - db_ping_ms latency
      - model used
    """
    if not question or not isinstance(question, str):
        raise ValueError("question must be a non-empty string")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your environment or a .env file (python-dotenv supported)."
        )

    # OpenAI client reads OPENAI_API_KEY from environment
    if max_steps != 1:
        raise ValueError("Single-shot agent: max_steps must be 1")

    # apply request timeout to avoid hanging calls
    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    system = (
        "you extract a concise intent from the user's question for healthcare trend analysis. "
        'answer with a single json object: {"intent": "..."}. keep it short.'
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        timeout=timeout_s or _DEFAULT_OPENAI_TIMEOUT_S,
    )

    content = (resp.choices[0].message.content or "").strip()
    intent_value = content
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "intent" in parsed:
            intent_value = parsed["intent"]
    except Exception:
        # If content isn't json, return it as-is
        pass

    db_ms = _db_ping_ms()

    return {
        "question": question,
        "intent": intent_value,
        "db_ping_ms": db_ms,
        "model": model,
    }


#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/ai_sdk.py
# role: ai agent sdk
# desc: minimal ask() function that uses OpenAI and safely pings Postgres; no CLI
# === FILE META CLOSING ===

import json
import os
import time
from typing import Any, Dict

import yaml
from openai import OpenAI
from sqlalchemy import create_engine, text

# Optionally load .env for local development (non-fatal if package missing)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass


def _load_infrastructure() -> Dict[str, Any]:
    """Load infrastructure.yml for database settings."""
    with open("config/infrastructure.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _make_engine_and_timeout():
    """Create a SQLAlchemy engine and return (engine, timeout_seconds).

    Environment variables override yaml values for 12-factor compatibility.
    """
    cfg = _load_infrastructure()
    db = cfg.get("database", {})

    host = os.environ.get("DB_HOST", db.get("host", "localhost"))
    port = int(os.environ.get("DB_PORT", db.get("port", 5432)))
    name = os.environ.get("DB_NAME", db.get("database", "aca_health"))
    user = os.environ.get("DB_USERNAME", db.get("username", "etl"))
    pwd = os.environ.get("DB_PASSWORD", db.get("password", "etl"))
    timeout_s = int(
        os.environ.get(
            "DB_STATEMENT_TIMEOUT_SECONDS", db.get("statement_timeout_seconds", 30)
        )
    )

    url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"
    engine = create_engine(url, pool_pre_ping=True, future=True)
    return engine, timeout_s


def _db_ping_ms() -> int:
    """Execute a lightweight query with a per-statement timeout and return latency in ms."""
    engine, timeout_s = _make_engine_and_timeout()
    start = time.time()
    timeout_ms = max(1, int(timeout_s * 1000))
    with engine.begin() as conn:
        conn.execute(text(f"set local statement_timeout = {timeout_ms}"))
        conn.execute(text("select 1"))
    return int((time.time() - start) * 1000)


def ask(question: str) -> Dict[str, Any]:
    """Minimal entrypoint: derive a concise intent and verify DB connectivity.

    This does NOT run arbitrary SQL. It returns:
      - original question
      - intent extracted by the model (short)
      - db_ping_ms latency
      - model used
    """
    if not question or not isinstance(question, str):
        raise ValueError("question must be a non-empty string")

    # OpenAI client reads OPENAI_API_KEY from environment
    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    system = (
        "you extract a concise intent from the user's question for healthcare trend analysis. "
        'answer with a single json object: {"intent": "..."}. keep it short.'
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
    )

    content = (resp.choices[0].message.content or "").strip()
    intent_value = content
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "intent" in parsed:
            intent_value = parsed["intent"]
    except Exception:
        # If content isn't json, return it as-is
        pass

    db_ms = _db_ping_ms()

    return {
        "question": question,
        "intent": intent_value,
        "db_ping_ms": db_ms,
        "model": model,
    }
