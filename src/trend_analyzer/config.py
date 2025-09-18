#!/usr/bin/env python3
#
# === FILE META OPENING ===
# file: ./trend-analyzer/src/trend_analyzer/config.py
# role: configuration
# desc: basic configuration skeleton with placeholder environment variables
# === FILE META CLOSING ===

import os

print("Loading config module...")

class Config:
    """Basic configuration class with placeholder environment variables"""
    
    def __init__(self):
        print("Initializing Config class")
        
        # Placeholder environment variables
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "placeholder-key")
        self.BILLING_PROJECT_ID_BQ = os.getenv("BILLING_PROJECT_ID_BQ", "placeholder-project")
        self.DESTINATION_PROJECT_ID_BQ = os.getenv("DESTINATION_PROJECT_ID_BQ", "placeholder-project")
        
        print(f"Config loaded with project: {self.BILLING_PROJECT_ID_BQ}")
    
    def validate(self):
        """Placeholder validation - just prints what it would check"""
        print("Validating configuration...")
        
        errors = []
        
        if self.OPENAI_API_KEY == "placeholder-key":
            errors.append("OPENAI_API_KEY is not set (placeholder)")
        
        if self.BILLING_PROJECT_ID_BQ == "placeholder-project":
            errors.append("BILLING_PROJECT_ID_BQ is not set (placeholder)")
        
        if errors:
            print(f"Configuration errors found: {len(errors)}")
            for error in errors:
                print(f"   - {error}")
        else:
            print("Configuration is valid")
        
        return errors

# Global config instance
print("Creating global config instance...")
config = Config()