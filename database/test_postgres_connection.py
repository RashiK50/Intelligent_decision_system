import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

print("HOST:", os.getenv("DB_HOST"))
print("PORT:", os.getenv("DB_PORT"))
print("DB:", os.getenv("DB_NAME"))
print("USER:", os.getenv("DB_USER"))

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    sslmode="require"
)

print("Connected Successfully!")

conn.close()