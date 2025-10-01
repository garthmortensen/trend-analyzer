#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/auth.py
# role: authentication
# desc: database and service authentication for trend analyzer
# === FILE META CLOSING ===

from .logging_config import info, debug, error, warning

info("Loading auth module...")

from .postgres_client import get_postgres_client

def get_database_client(config):
    """Get database client based on configuration"""
    db_type = config.get("database", {}).get("type", "postgresql")
    
    if db_type == "postgresql":
        info("Getting PostgreSQL client...")
        return get_postgres_client(config)
    elif db_type == "bigquery":
        warning("BigQuery no longer supported - use PostgreSQL")
        return None
    else:
        error(f"Unknown database type: {db_type}")
        return None

def get_credentials():
    """Placeholder for credentials (simplified for PostgreSQL)"""
    debug("Getting database credentials...")
    debug("   - Would load from config or environment")
    debug("Credentials obtained")
    return "placeholder-credentials"

def get_docs_service():
    """Placeholder for document service (optional)"""
    debug("Document service not required for PostgreSQL setup")
    return "placeholder-docs-service"

def get_drive_service():
    """Placeholder for file service (optional)"""
    debug("File service not required for PostgreSQL setup")
    return "placeholder-drive-service"