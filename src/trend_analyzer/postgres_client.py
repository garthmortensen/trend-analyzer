#!/usr/bin/env python3

# === FILE META OPENING ===
# file: ./src/trend_analyzer/postgres_client.py
# role: data_access
# desc: PostgreSQL database client for trend analyzer
# === FILE META CLOSING ===

import os
from typing import Optional, Dict, Any

import pandas as pd
from sqlalchemy import create_engine, text

# Optionally load .env for local development (non-fatal if package missing)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass


class PostgreSQLClient:
    """Simple PostgreSQL client with optional statement timeout.

    - Reads host/port/database from config["database"].
    - Username/password are overridden by DB_USERNAME/DB_PASSWORD env vars if set.
    - statement_timeout_seconds (in config) is converted to milliseconds and applied via
      psycopg2 "options" connect arg.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = None
        self.connection_string = ""
        self._connect_args: Dict[str, Any] = {}
        self._build_connection_string()

    def _build_connection_string(self) -> None:
        db_config = self.config.get("database", {})

        host = db_config.get("host", "localhost")
        port = db_config.get("port", 5432)
        database = db_config.get("database", "trend_analyzer")
        # environment overrides for 12-factor compatibility
        username = os.getenv("DB_USERNAME", db_config.get("username", "postgres"))
        password = os.getenv("DB_PASSWORD", db_config.get("password", "password"))

        # Timeout configuration (seconds only)
        statement_timeout_seconds = db_config.get("statement_timeout_seconds")
        statement_timeout_ms: Optional[int] = None
        if isinstance(statement_timeout_seconds, (int, float)):
            statement_timeout_ms = int(float(statement_timeout_seconds) * 1000)

        self.connection_string = (
            f"postgresql://{username}:{password}@{host}:{port}/{database}"
        )

        # Configure server-side statement timeout if provided (in milliseconds)
        if isinstance(statement_timeout_ms, int) and statement_timeout_ms > 0:
            # psycopg2 supports passing options flags
            self._connect_args = {
                "options": f"-c statement_timeout={int(statement_timeout_ms)}"
            }
        else:
            self._connect_args = {}

    def connect(self) -> bool:
        """Create an engine and verify connectivity."""
        try:
            # Use future engine and pre-ping; apply connect args (e.g., statement_timeout)
            self.engine = create_engine(
                self.connection_string,
                future=True,
                pool_pre_ping=True,
                connect_args=self._connect_args or {},
            )

            # Test connection
            with self.engine.connect() as conn:
                _ = conn.execute(text("select 1"))

            return True
        except Exception:
            return False

    def run_query(
        self, sql: str, params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Execute SQL query and return DataFrame."""
        if not self.engine:
            if not self.connect():
                return pd.DataFrame()

        try:
            return pd.read_sql(sql, self.engine, params=params)
        except Exception:
            return pd.DataFrame()

    def execute_ddl(self, sql: str) -> bool:
        """Execute DDL statements (create, drop, etc.)."""
        if not self.engine:
            if not self.connect():
                return False

        try:
            with self.engine.begin() as conn:
                conn.execute(text(sql))
            return True
        except Exception:
            return False

    def table_exists(self, table_name: str, schema: str = "public") -> bool:
        """Check if a table exists using information_schema."""
        sql = f"""
        select exists (
            select from information_schema.tables
            where table_schema = '{schema}'
              and table_name = '{table_name}'
        );
        """
        try:
            df = self.run_query(sql)
            return bool(df.iloc[0, 0]) if not df.empty else False
        except Exception:
            return False

    def get_table_info(self, table_name: str, schema: str = "public") -> pd.DataFrame:
        """Get table column metadata (name, type, nullability)."""
        sql = f"""
        select column_name, data_type, is_nullable
        from information_schema.columns
        where table_schema = '{schema}' and table_name = '{table_name}'
        order by ordinal_position;
        """
        return self.run_query(sql)


# Global client instance
_postgres_client: Optional[PostgreSQLClient] = None


def get_postgres_client(config: Dict[str, Any]) -> PostgreSQLClient:
    """Get or create a singleton PostgreSQL client for this process."""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgreSQLClient(config)
    return _postgres_client
