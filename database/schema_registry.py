import json
import os
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaRegistry:
    def __init__(self, registry_filepath: str = "registry/schema_registry_generated.json"):
        """
        Initializes the registry by loading the dynamically generated JSON file.
        """
        self.tables: Dict[str, dict] = {}
        self.registry_filepath = registry_filepath
        self._load_registry()

    def _load_registry(self):
        """Loads the JSON schema file into memory."""
        try:
            if os.path.exists(self.registry_filepath):
                with open(self.registry_filepath, "r") as f:
                    self.tables = json.load(f)
                logger.info(f"Successfully loaded schema registry from {self.registry_filepath}")
            else:
                logger.error(f"Schema registry file not found at {self.registry_filepath}. Please run generate_schema_registry.py first.")
        except Exception as e:
            logger.error(f"Failed to load schema registry: {e}")

    def get_formatted_menu_for_intent(self, requested_tables: List[str] = None) -> str:
        """
        Converts the requested tables (or all tables if none specified) into a 
        token-efficient, highly readable string menu to inject into the LLM context prompt.
        """
        if not self.tables:
            return "Error: Database schema is currently unavailable."

        # If no specific tables requested, default to all available
        tables_to_format = requested_tables if requested_tables else list(self.tables.keys())
        
        menu_lines = []
        for table_name in tables_to_format:
            table = self.tables.get(table_name)
            if not table:
                continue
                
            menu_lines.append(f"TABLE: {table.get('table_name')}")
            menu_lines.append(f"DESCRIPTION: {table.get('description', 'No description available.')}")
            menu_lines.append("COLUMNS:")
            
            for col in table.get("columns", []):
                # Format: - column_name (type): description [Example: data]
                name = col.get("name")
                dtype = col.get("data_type")
                desc = col.get("description", "")
                example = col.get("example", "")
                
                menu_lines.append(f"  - {name} ({dtype}): {desc} [Example: {example}]")
                
            menu_lines.append("") # Spacing between tables
            
        return "\n".join(menu_lines)

# Create a global instance that can be imported by your agents
schema_registry = SchemaRegistry()