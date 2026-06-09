import os
from dotenv import load_dotenv
import psycopg2


load_dotenv()


def execute_query(sql_query: str):

    conn = psycopg2.connect(
        os.getenv("DATABASE_URL"),
        sslmode="require"
    )

    cur = conn.cursor()

    cur.execute(sql_query)

    columns = [
        desc[0]
        for desc in cur.description
    ]

    rows = cur.fetchall()

    result = []

    for row in rows:

        result.append(
            dict(zip(columns, row))
        )

    cur.close()
    conn.close()

    return result