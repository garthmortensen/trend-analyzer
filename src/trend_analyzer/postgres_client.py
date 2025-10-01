#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/postgres_client.py
# role: data_access
# desc: PostgreSQL database client for trend analyzer
# === FILE META CLOSING ===

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
from typing import Optional, Dict, Any
import logging

print("Loading postgres_client module...")

class PostgreSQLClient:
    """PostgreSQL database client for trend analyzer"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = None
        self.connection_string = None
        self._build_connection_string()
    
    def _build_connection_string(self):
        """Build PostgreSQL connection string from config"""
        db_config = self.config.get("database", {})
        
        host = db_config.get("host", "localhost")
        port = db_config.get("port", 5432)
        database = db_config.get("database", "trend_analyzer")
        username = db_config.get("username", "postgres")
        password = db_config.get("password", "password")
        
        self.connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        print(f"[PLACEHOLDER] Connection string built for: {username}@{host}:{port}/{database}")
    
    def connect(self) -> bool:
        """Test database connection"""
        print("[PLACEHOLDER] Connecting to PostgreSQL...")
        
        try:
            self.engine = create_engine(self.connection_string)
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"[PLACEHOLDER] Connected successfully: {version[:50]}...")
            
            return True
            
        except Exception as e:
            print(f"[PLACEHOLDER] Connection failed: {str(e)}")
            return False
    
    def run_query(self, sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute SQL query and return DataFrame"""
        print(f"[PLACEHOLDER] Executing query: {sql[:100]}...")
        
        if not self.engine:
            if not self.connect():
                print("[PLACEHOLDER] Cannot execute query - no connection")
                return pd.DataFrame()
        
        try:
            df = pd.read_sql(sql, self.engine, params=params)
            print(f"[PLACEHOLDER] Query successful: {len(df)} rows returned")
            return df
            
        except Exception as e:
            print(f"[PLACEHOLDER] Query failed: {str(e)}")
            return pd.DataFrame()
    
    def execute_ddl(self, sql: str) -> bool:
        """Execute DDL statements (CREATE, DROP, etc.)"""
        print(f"[PLACEHOLDER] Executing DDL: {sql[:100]}...")
        
        if not self.engine:
            if not self.connect():
                print("[PLACEHOLDER] Cannot execute DDL - no connection")
                return False
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            
            print("[PLACEHOLDER] DDL executed successfully")
            return True
            
        except Exception as e:
            print(f"[PLACEHOLDER] DDL failed: {str(e)}")
            return False
    
    def table_exists(self, table_name: str, schema: str = "public") -> bool:
        """Check if table exists"""
        sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = %s
        );
        """
        
        try:
            df = self.run_query(sql, {"schema": schema, "table_name": table_name})
            exists = df.iloc[0, 0] if not df.empty else False
            print(f"[PLACEHOLDER] Table {schema}.{table_name} exists: {exists}")
            return exists
            
        except Exception as e:
            print(f"[PLACEHOLDER] Error checking table existence: {e}")
            return False
    
    def get_table_info(self, table_name: str, schema: str = "public") -> pd.DataFrame:
        """Get table column information"""
        sql = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """
        
        return self.run_query(sql, {"schema": schema, "table_name": table_name})

# Global client instance
_postgres_client: Optional[PostgreSQLClient] = None

def get_postgres_client(config: Dict[str, Any]) -> PostgreSQLClient:
    """Get or create PostgreSQL client"""
    global _postgres_client
    
    if _postgres_client is None:
        _postgres_client = PostgreSQLClient(config)
    
    return _postgres_client