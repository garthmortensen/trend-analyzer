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

info("===START TREND ANALYZER===")

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
        # Boolean flags (cube build removed)
        "run_analysis": config.should_run_analysis(),
        "test_data": config.should_test_data(),
    }

    return combined_config


def execute_analysis(config_data):
    """Execute trend analysis with PostgreSQL"""
    info("EXECUTING: Trend Analysis (PostgreSQL)")

    analysis_config = config_data.get("analyze", {})
    output_config = config_data.get("output", {})
    db_config = config_data.get("database", {})

    info(
        f"Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}"
    )
    info(f"Group by: {analysis_config.get('group_by_dimensions', [])}")
    info(f"Filters: {len(analysis_config.get('filters', []))} filters")
    info(f"Top N: {analysis_config.get('top_n', 'unlimited')}")
    info(f"Output format: {output_config.get('format', 'json')}")

    # Log detailed analysis configuration
    debug("Analysis configuration details:")
    for key, value in analysis_config.items():
        debug(f"  {key}: {value}")

    # Import and use PostgreSQL data access
    try:
        import json
        from .data_access import get_trend_data_from_config

        result = get_trend_data_from_config(config_data)
        
        # Print the SQL query
        info("\nSQL Query Executed:")
        print("\n" + result["sql"] + "\n")
        
        # Parse and display row count
        rows = json.loads(result["data"])
        info(f"Query returned {len(rows)} rows")

        # TODO: implement AI analysis
        info("Would execute AI analysis...")
        debug("   - Run trend analysis")
        debug("   - Generate report")
        info("Analysis complete")
    except Exception as e:
        error(f"Analysis failed: {e}")
        if (
            "NoSuchTableError" in str(type(e))
            or "agg_trend_descriptor" in str(e)
            or "agg_trend_normalizer" in str(e)
        ):
            error(
                "Required database tables not found. Please ensure the following tables exist:"
            )
            error("  - agg_trend_descriptor")
            error("  - agg_trend_normalizer")
            error("See database/*.sql for table definitions")
        raise


def execute_data_tests(config_data):
    """Execute data testing with PostgreSQL"""
    info("EXECUTING: Data Testing (PostgreSQL)")

    db_config = config_data.get("database", {})

    info(
        f"Database: {db_config.get('type', 'postgresql')} at {db_config.get('host', 'localhost')}"
    )

    # Test database connection
    from .auth import get_database_client
    from .data_access import DESCRIPTOR_TABLE, NORMALIZER_TABLE

    db_client = get_database_client(config_data)
    connection_success = db_client.connect()

    if connection_success:
        info("PostgreSQL connection test: SUCCESS")

        # Check if required tables exist
        schema = db_config.get("schema", "public")
        descriptor_exists = db_client.table_exists(DESCRIPTOR_TABLE, schema)
        normalizer_exists = db_client.table_exists(NORMALIZER_TABLE, schema)

        info(
            f"Table check: {schema}.{DESCRIPTOR_TABLE} {'EXISTS' if descriptor_exists else 'NOT FOUND'}"
        )
        info(
            f"Table check: {schema}.{NORMALIZER_TABLE} {'EXISTS' if normalizer_exists else 'NOT FOUND'}"
        )
    else:
        error("PostgreSQL connection test: FAILED")

    info("Data testing complete")


def main():
    """Main entry point with comprehensive logging"""
    info("TREND ANALYZER===arting up...")

    # Load the config files
    config_data = load_config()
    if not config_data:
        error("Failed to load configuration. Exiting.")
        return

    # Check which operations to run
    run_analysis = config_data.get("run_analysis", True)
    # Cube build removed
    test_data = config_data.get("test_data", False)

    operations = []
    if run_analysis:
        operations.append("analysis")
    if test_data:
        operations.append("data testing")

    if not operations:
        warning("No operations enabled. Enable at least one in config/analysis.yml")
        return

    info(f"Will run: {', '.join(operations)}")
    debug(f"Operation flags - run_analysis: {run_analysis}, test_data: {test_data}")

    # Execute enabled operations
    try:
        # simple test to ensure database connectivity and tables exist
        if test_data:
            execute_data_tests(config_data)

        # TODO: understand this
        if run_analysis:
            execute_analysis(config_data)

        info("Execution completed successfully")

    except Exception as e:
        error(f"Execution failed with error: {e}")
        debug(f"Error details: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
