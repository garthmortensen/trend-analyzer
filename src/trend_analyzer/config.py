#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/config.py
# role: configuration
# desc: configuration loader that handles both runtime config and dimensions schema
# === FILE META CLOSING ===

import os
import yaml
from pathlib import Path

print("Loading config module...")

def load_config_files():
    """Load infrastructure.yml, analysis.yml, and dimensions.yml from config directory"""
    config_dir = Path("config")
    
    # Load all config files
    infrastructure_config_path = config_dir / "infrastructure.yml"
    analysis_config_path = config_dir / "analysis.yml"
    dimensions_config_path = config_dir / "dimensions.yml"
    
    configs = {}
    
    # Load infrastructure config
    if not infrastructure_config_path.exists():
        print(f"[ERROR] Infrastructure config not found: {infrastructure_config_path}")
        return None, None, None
    
    # Load analysis config
    if not analysis_config_path.exists():
        print(f"[ERROR] Analysis config not found: {analysis_config_path}")
        return None, None, None
    
    # Load dimensions config
    if not dimensions_config_path.exists():
        print(f"[ERROR] Dimensions config not found: {dimensions_config_path}")
        return None, None, None
    
    try:
        with open(infrastructure_config_path, 'r') as f:
            infrastructure_config = yaml.safe_load(f)
        
        with open(analysis_config_path, 'r') as f:
            analysis_config = yaml.safe_load(f)
        
        with open(dimensions_config_path, 'r') as f:
            dimensions_config = yaml.safe_load(f)
        
        print(f"[SUCCESS] Loaded infrastructure, analysis, and dimensions configs")
        return infrastructure_config, analysis_config, dimensions_config
    
    except Exception as e:
        print(f"[ERROR] Failed to load configs: {e}")
        return None, None, None

class Config:
    """Configuration class that loads infrastructure, analysis, and dimensions configs"""
    
    def __init__(self):
        print("Initializing Config class")
        
        # Load config files
        self.infrastructure_config, self.analysis_config, self.dimensions_config = load_config_files()
        
        # Environment variables for services that need them
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "placeholder-key")
        
        if self.analysis_config:
            operations = []
            if self.analysis_config.get("run_analysis", True):
                operations.append("analysis")
            if self.analysis_config.get("build_cubes", False):
                operations.append("cubes")
            if self.analysis_config.get("test_data", False):
                operations.append("testing")
            print(f"Config loaded with operations: {', '.join(operations) if operations else 'none'}")
        else:
            print("Config failed to load")
    
    def should_run_analysis(self):
        """Check if analysis should be run"""
        if not self.analysis_config:
            return True
        return self.analysis_config.get("run_analysis", True)
    
    def should_build_cubes(self):
        """Check if cubes should be built"""
        if not self.analysis_config:
            return False
        return self.analysis_config.get("build_cubes", False)
    
    def should_test_data(self):
        """Check if data testing should be run"""
        if not self.analysis_config:
            return False
        return self.analysis_config.get("test_data", False)
    
    def get_database_config(self):
        """Get database configuration"""
        if not self.infrastructure_config:
            return {}
        return self.infrastructure_config.get("database", {})
    
    def get_output_config(self):
        """Get output configuration"""
        if not self.infrastructure_config:
            return {}
        return self.infrastructure_config.get("output", {})
    
    def get_output_dir(self):
        """Get output directory"""
        output_config = self.get_output_config()
        return output_config.get("dir", "./output")
    
    def get_ai_config(self):
        """Get AI configuration"""
        if not self.infrastructure_config:
            return {}
        return self.infrastructure_config.get("ai", {})
    
    def get_analysis_config(self):
        """Get analysis configuration"""
        if not self.analysis_config:
            return {}
        return self.analysis_config.get("analyze", {})
    
    def get_cube_building_config(self):
        """Get cube building configuration"""
        if not self.analysis_config:
            return {}
        return self.analysis_config.get("cube_building", {})
    
    def get_trends_config(self):
        """Get trends configuration"""
        if not self.analysis_config:
            return {}
        return self.analysis_config.get("trends", {})
    
    def get_alerts_config(self):
        """Get alerts configuration"""
        if not self.analysis_config:
            return {}
        return self.analysis_config.get("alerts", {})
    
    def get_dimensions(self):
        """Get dimensions configuration"""
        if not self.dimensions_config:
            return []
        return self.dimensions_config.get("dimensions", [])
    
    def get_metrics(self):
        """Get metrics configuration"""
        if not self.dimensions_config:
            return []
        return self.dimensions_config.get("metrics", [])
    
    def validate(self):
        """Validate all configuration files"""
        print("Validating configuration...")
        
        errors = []
        
        if not self.infrastructure_config:
            errors.append("Infrastructure config file not loaded")
        
        if not self.analysis_config:
            errors.append("Analysis config file not loaded")
        
        if not self.dimensions_config:
            errors.append("Dimensions config file not loaded")
        
        if self.analysis_config:
            # Validate boolean flags
            run_analysis = self.analysis_config.get("run_analysis")
            build_cubes = self.analysis_config.get("build_cubes")
            test_data = self.analysis_config.get("test_data")
            
            if not isinstance(run_analysis, bool) and run_analysis is not None:
                errors.append("run_analysis must be true or false")
            if not isinstance(build_cubes, bool) and build_cubes is not None:
                errors.append("build_cubes must be true or false")
            if not isinstance(test_data, bool) and test_data is not None:
                errors.append("test_data must be true or false")
        
        if errors:
            print(f"Configuration errors found: {len(errors)}")
            for error in errors:
                print(f"   - {error}")
        else:
            print("All configurations are valid")
        
        return errors

# Global config instance
print("Creating global config instance...")
config = Config()