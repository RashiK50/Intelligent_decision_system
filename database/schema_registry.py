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
        """Converts the requested tables (or all tables if none specified) into a token-efficient, highly readable string menu to inject into the LLM context prompt."""
        if not self.tables:
            return "Error: Database schema is currently unavailable."

        tables_to_format = requested_tables if requested_tables else list(self.tables.keys())

        menu_lines = []
        for table_name in tables_to_format:
            table = self.tables.get(table_name)
            if not table:
                continue

            column_types = table.get("column_types", {})

            menu_lines.append(f"TABLE: {table_name}")
            menu_lines.append(f"DESCRIPTION: {table.get('description') or 'No description available.'}")

            primary_key = table.get("primary_key")
            if primary_key:
                menu_lines.append(f"PRIMARY KEY: {primary_key}")

            menu_lines.append("COLUMNS:")
            for col_name in table.get("columns", []):
                dtype = column_types.get(col_name, "unknown")
                menu_lines.append(f"  - {col_name} ({dtype})")

            foreign_keys = table.get("foreign_keys", {})
            if foreign_keys:
                menu_lines.append("FOREIGN KEYS (use these exact join paths, do not invent others):")
                for local_col, target in foreign_keys.items():
                    menu_lines.append(f"  - {table_name}.{local_col} -> {target}")

            menu_lines.append("")  # Spacing between tables

        return "\n".join(menu_lines)

# Create a global instance that can be imported by your agents
schema_registry = SchemaRegistry()