#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/cube_builder.py
# role: data_processing
# desc: removed – cubes are prebuilt via SQL in ./database; shim retained for compatibility
# === FILE META CLOSING ===

print("Loading cube_builder module (shim)...")

def create_cubes_from_config(exec_config):
    print("[INFO] Cube build disabled. Tables are built upstream (see database/*.sql).")
    return {"success": True, "message": "cube build skipped (upstream-managed)"}

def load_yaml_config(yaml_path):
    print("[INFO] Cube build disabled. YAML parsing not required here.")
    return {}

def build_descriptor_sql(config):
    print("[INFO] Cube build disabled. No descriptor SQL generation.")
    return "-- disabled"

def build_norm_sql(config):
    print("[INFO] Cube build disabled. No norm SQL generation.")
    return "-- disabled"

def create_cubes(dimensions_file_path):
    print("[INFO] Cube build disabled. Nothing to do.")
    return True