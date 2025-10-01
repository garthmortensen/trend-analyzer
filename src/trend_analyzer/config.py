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
            print(f"Config loaded with mode: {self.analysis_config.get('mode', 'unknown')}")
        else:
            print("Config failed to load")
    
    def get_mode(self):
        """Get execution mode from analysis config"""
        if not self.analysis_config:
            return "analyze"
        return self.analysis_config.get("mode", "analyze")
    
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
    
    def get_build_cubes_config(self):
        """Get cube building configuration"""
        if not self.analysis_config:
            return {}
        return self.analysis_config.get("build_cubes", {})
    
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
            mode = self.analysis_config.get("mode")
            if mode not in ["analyze", "build-cubes", "test-data"]:
                errors.append(f"Invalid mode: {mode}")
        
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