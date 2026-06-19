import os
import json
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(
    DATABASE_URL,
    sslmode="require"
)

cur = conn.cursor()

# ==========================================
# GET ALL TABLES
# ==========================================

cur.execute("""
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
""")

tables = [row[0] for row in cur.fetchall()]

schema_registry = {}

for table in tables:

    print(f"Processing table: {table}")

    # ==========================================
    # COLUMNS + DATA TYPES
    # ==========================================

    cur.execute("""
    SELECT
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = %s
    ORDER BY ordinal_position;
    """, (table,))

    column_rows = cur.fetchall()

    columns = []
    column_types = {}

    for column_name, data_type in column_rows:
        columns.append(column_name)
        column_types[column_name] = data_type

    # ==========================================
    # PRIMARY KEY
    # ==========================================

    cur.execute("""
    SELECT
        kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
       AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema = 'public'
      AND tc.table_name = %s;
    """, (table,))

    pk_row = cur.fetchone()

    primary_key = (
        pk_row[0]
        if pk_row
        else None
    )

    # ==========================================
    # FOREIGN KEYS
    # ==========================================

    cur.execute("""
    SELECT
        kcu.column_name,
        ccu.table_name,
        ccu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
       AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu
        ON ccu.constraint_name = tc.constraint_name
       AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'public'
      AND tc.table_name = %s;
    """, (table,))

    fk_rows = cur.fetchall()

    foreign_keys = {}

    for local_col, ref_table, ref_col in fk_rows:

        foreign_keys[local_col] = (
            f"{ref_table}.{ref_col}"
        )


    # ==========================================
    # SAMPLE DATA (1 ROW FOR LLM CONTEXT)
    # ==========================================

    cur.execute(f"SELECT * FROM public.{table} LIMIT 1;")
    sample_row = cur.fetchone()
    
    column_examples = {}
    if sample_row:
        # Extract column names from the cursor description
        col_names = [desc[0] for desc in cur.description]
        
        # Map column names to their sample values, cast to string for JSON safety
        for col_name, val in zip(col_names, sample_row):
            column_examples[col_name] = str(val) if val is not None else "None"

    # ==========================================
    # BUILD REGISTRY
    # ==========================================

    schema_registry[table] = {

        "description": "",

        "primary_key": primary_key,

        "foreign_keys": foreign_keys,

        "columns": columns,

        "column_types": column_types,

        "column_examples": column_examples
    }

# ==========================================
# SAVE JSON
# ==========================================

os.makedirs("registry", exist_ok=True)

with open(
    "registry/schema_registry_generated.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        schema_registry,
        f,
        indent=4
    )

cur.close()
conn.close()

print("\n✅ Schema Registry Generated Successfully!")
print(
    "Saved to: "
    "registry/schema_registry_generated.json"
)