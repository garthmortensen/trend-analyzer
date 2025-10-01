#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/__main__.py
# role: entry_point
# desc: simplified single entry point that reads config.yml and executes
# === FILE META CLOSING ===

from pathlib import Path
import yaml

from .config import config

print("Starting Trend Analyzer...")

def load_config():
    """Load configuration from config directory - now uses infrastructure and analysis configs"""
    print("Loading configuration from config directory...")
    
    # Config is now loaded automatically by the config module
    # Just validate that it loaded successfully
    if not config.infrastructure_config or not config.analysis_config:
        print("Error: Failed to load configuration files")
        print("Please ensure config/infrastructure.yml and config/analysis.yml exist")
        return None
    
    print("Configuration loaded successfully from:")
    print("  - config/infrastructure.yml")
    print("  - config/analysis.yml") 
    print("  - config/dimensions.yml")
    
    # Return combined config for backward compatibility
    combined_config = {
        "database": config.get_database_config(),
        "output": config.get_output_config(),
        "analyze": config.get_analysis_config(),
        "cube_building": config.get_cube_building_config(),
        # Include the boolean flags
        "run_analysis": config.should_run_analysis(),
        "build_cubes": config.should_build_cubes(),
        "test_data": config.should_test_data()
    }
    
    return combined_config

def execute_analysis(config_data):
    """Execute trend analysis with PostgreSQL"""
    print("\nEXECUTING: Trend Analysis (PostgreSQL)")
    
    analysis_config = config_data.get("analyze", {})
    output_config = config_data.get("output", {})
    db_config = config_data.get("database", {})
    
    print(f"[PLACEHOLDER] Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}")
    print(f"[PLACEHOLDER] Group by: {analysis_config.get('group_by_dimensions', [])}")
    print(f"[PLACEHOLDER] Filters: {len(analysis_config.get('filters', []))} filters")
    print(f"[PLACEHOLDER] Top N: {analysis_config.get('top_n', 'unlimited')}")
    print(f"[PLACEHOLDER] Output format: {output_config.get('format', 'json')}")
    
    # Import and use PostgreSQL data access
    from .data_access import get_trend_data_from_config
    result = get_trend_data_from_config(config_data)
    
    print("[PLACEHOLDER] Would execute AI analysis...")
    print("   - Load data from PostgreSQL tables")
    print("   - Run trend analysis")
    print("   - Generate report")
    print("[PLACEHOLDER] Analysis complete")

def execute_cube_build(config_data):
    """Execute cube building with PostgreSQL"""
    print("\nEXECUTING: Table Creation (PostgreSQL)")
    
    cube_config = config_data.get("cube_building", {})
    paths_config = config_data.get("paths", {})
    db_config = config_data.get("database", {})
    
    print(f"[PLACEHOLDER] Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}")
    print(f"[PLACEHOLDER] Dimensions file: {paths_config.get('dimensions_file', './config/dimensions.yml')}")
    print(f"[PLACEHOLDER] Force rebuild: {cube_config.get('force_rebuild', False)}")
    print(f"[PLACEHOLDER] Validate data: {cube_config.get('validate_data', True)}")
    
    print("[PLACEHOLDER] Would execute table creation...")
    print("   - Load YAML configuration")
    print("   - Generate SQL for PostgreSQL tables")
    print("   - Execute CREATE TABLE statements")
    print("   - Create indexes for performance")
    print("[PLACEHOLDER] Table creation complete")

def execute_data_tests(config_data):
    """Execute data testing with PostgreSQL"""
    print("\nEXECUTING: Data Testing (PostgreSQL)")
    
    test_config = config_data.get("test_data", {})
    db_config = config_data.get("database", {})
    
    print(f"[PLACEHOLDER] Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}")
    connections = test_config.get("connection_tests", [])
    print(f"[PLACEHOLDER] Testing connections: {connections}")
    print(f"[PLACEHOLDER] Run sample queries: {test_config.get('run_sample_queries', True)}")
    
    # Test PostgreSQL connection
    from .auth import get_database_client
    db_client = get_database_client(config_data)
    
    if db_client:
        connection_success = db_client.connect()
        print(f"[PLACEHOLDER] PostgreSQL connection test: {'SUCCESS' if connection_success else 'FAILED'}")
    
    print("[PLACEHOLDER] Would execute data testing...")
    print("   - Test PostgreSQL connection")
    print("   - Validate table schemas")
    print("   - Run sample queries")
    print("   - Check data quality")
    print("[PLACEHOLDER] Data testing complete")

def main():
    """Ultra-simplified main entry point"""
    print("Trend Analyzer starting up...")
    
    # Load the single config file
    config_data = load_config()
    if not config_data:
        print("Failed to load configuration. Exiting.")
        return
    
    # Check which operations to run
    run_analysis = config_data.get("run_analysis", True)
    build_cubes = config_data.get("build_cubes", False)
    test_data = config_data.get("test_data", False)
    
    operations = []
    if run_analysis: operations.append("analysis")
    if build_cubes: operations.append("cube building")
    if test_data: operations.append("data testing")
    
    if not operations:
        print("No operations enabled. Enable at least one in config/analysis.yml")
        return
    
    print(f"Will run: {', '.join(operations)}")
    
    # Execute enabled operations
    if run_analysis:
        execute_analysis(config_data)
    
    if build_cubes:
        execute_cube_build(config_data)
    
    if test_data:
        execute_data_tests(config_data)
    
    print("\nExecution completed successfully")

if __name__ == "__main__":
    main()
