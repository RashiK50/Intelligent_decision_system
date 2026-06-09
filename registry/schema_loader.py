import json


def load_schema():

    with open(
        "registry/schema_registry_generated.json",
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def get_schema_context():

    schema = load_schema()

    context = ""

    for table, info in schema.items():

        context += f"\nTABLE: {table}\n"

        context += (
            f"PRIMARY KEY: "
            f"{info['primary_key']}\n"
        )

        if info["foreign_keys"]:

            context += (
                f"FOREIGN KEYS: "
                f"{info['foreign_keys']}\n"
            )

        context += (
            f"COLUMNS: "
            f"{', '.join(info['columns'])}\n"
        )

    return context