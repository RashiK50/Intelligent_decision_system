"""Pytest bootstrap: make the project root importable and keep env sane.

The suite is fully offline — no LLM calls, no database connections. Modules
that create engines at import time (database.engine) only need DATABASE_URL
to be *set*; nothing here ever opens a connection.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Safety net for CI machines without a .env file.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb"
)
