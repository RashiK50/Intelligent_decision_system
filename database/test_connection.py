from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("URL Loaded:", bool(url))
print("KEY Loaded:", bool(key))

supabase = create_client(url, key)

response = (
    supabase
    .table("orders")
    .select("*")
    .limit(5)
    .execute()
)

print(f"\nRows fetched: {len(response.data)}\n")

for row in response.data:
    print(row)