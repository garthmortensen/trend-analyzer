#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/__main__.py
# role: entry_point
# desc: main entry point that loads configs and executes enabled operations
# === FILE META CLOSING ===

from pathlib import Path
import yaml

from .logging_config import info, debug, error, warning
from .config import config

info("Starting Trend Analyzer...")

def load_config():
    """Load configuration from config directory - now uses infrastructure and analysis configs"""
    info("Loading configuration from config directory...")
    
    # Config is now loaded automatically by the config module
    # Just validate that it loaded successfully
    if not config.infrastructure_config or not config.analysis_config:
        error("Failed to load configuration files")
        error("Please ensure config/infrastructure.yml and config/analysis.yml exist")
        return None
    
    info("Configuration loaded successfully from:")
    info("  - config/infrastructure.yml")
    info("  - config/analysis.yml") 
    info("  - config/dimensions.yml")
    
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
    info("EXECUTING: Trend Analysis (PostgreSQL)")
    
    analysis_config = config_data.get("analyze", {})
    output_config = config_data.get("output", {})
    db_config = config_data.get("database", {})
    
    info(f"Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}")
    info(f"Group by: {analysis_config.get('group_by_dimensions', [])}")
    info(f"Filters: {len(analysis_config.get('filters', []))} filters")
    info(f"Top N: {analysis_config.get('top_n', 'unlimited')}")
    info(f"Output format: {output_config.get('format', 'json')}")
    
    # Log detailed analysis configuration
    debug("Analysis configuration details:")
    for key, value in analysis_config.items():
        debug(f"  {key}: {value}")
    
    # Import and use PostgreSQL data access
    from .data_access import get_trend_data_from_config
    result = get_trend_data_from_config(config_data)
    
    info("Would execute AI analysis...")
    debug("   - Load data from PostgreSQL tables")
    debug("   - Run trend analysis") 
    debug("   - Generate report")
    info("Analysis complete")

def execute_cube_build(config_data):
    """Execute cube building with PostgreSQL"""
    info("EXECUTING: Table Creation (PostgreSQL)")
    
    cube_config = config_data.get("cube_building", {})
    db_config = config_data.get("database", {})
    
    info(f"Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}")
    info(f"Dimensions file: ./config/dimensions.yml")
    info(f"Force rebuild: {cube_config.get('force_rebuild', False)}")
    info(f"Validate data: {cube_config.get('validate_data', True)}")
    
    # Log detailed cube configuration
    debug("Cube building configuration details:")
    for key, value in cube_config.items():
        debug(f"  {key}: {value}")
    
    # Import and use cube builder
    from .cube_builder import build_cubes_from_config
    result = build_cubes_from_config(config_data)
    
    info("Would execute table creation...")
    debug("   - Load YAML configuration")
    debug("   - Generate SQL for PostgreSQL tables")
    debug("   - Execute CREATE TABLE statements")
    debug("   - Create indexes for performance")
    info("Table creation complete")

def execute_data_tests(config_data):
    """Execute data testing with PostgreSQL"""
    info("EXECUTING: Data Testing (PostgreSQL)")
    
    test_config = config_data.get("test_data", {})
    db_config = config_data.get("database", {})
    
    info(f"Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}")
    info(f"Connection tests: {test_config.get('connection_tests', [])}")
    info(f"Sample queries: {test_config.get('run_sample_queries', False)}")
    
    # Log detailed test configuration
    debug("Data testing configuration details:")
    for key, value in test_config.items():
        debug(f"  {key}: {value}")
    
    # Test database connection
    from .auth import get_database_client
    db_client = get_database_client(config_data)
    
    if db_client:
        connection_success = db_client.connect()
        if connection_success:
            info("PostgreSQL connection test: SUCCESS")
        else:
            error("PostgreSQL connection test: FAILED")
    
    info("Would execute data testing...")
    debug("   - Test PostgreSQL connection")
    debug("   - Validate table schemas")
    debug("   - Run sample queries")
    debug("   - Check data quality")
    info("Data testing complete")

def main():
    """Main entry point with comprehensive logging"""
    info("Trend Analyzer starting up...")
    
    # Load the config files
    config_data = load_config()
    if not config_data:
        error("Failed to load configuration. Exiting.")
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
        warning("No operations enabled. Enable at least one in config/analysis.yml")
        return
    
    info(f"Will run: {', '.join(operations)}")
    debug(f"Operation flags - run_analysis: {run_analysis}, build_cubes: {build_cubes}, test_data: {test_data}")
    
    # Execute enabled operations
    try:
        if run_analysis:
            execute_analysis(config_data)
        
        if build_cubes:
            execute_cube_build(config_data)
        
        if test_data:
            execute_data_tests(config_data)
        
        info("Execution completed successfully")
    
    except Exception as e:
        error(f"Execution failed with error: {e}")
        debug(f"Error details: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
