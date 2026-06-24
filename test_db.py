import asyncio
import json
from database.engine import execute_read_query

async def test_schema():
    print("\n==================================================")
    print(" [TEST DB] Fetching Real Database Columns...")
    print("==================================================\n")
    
    # Query PostgreSQL's system catalog for table structures
    query = """
    SELECT table_name, column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name IN ('orders', 'products')
    ORDER BY table_name, column_name;
    """
    
    try:
        results = await execute_read_query(query)
        if not results:
            print("⚠️ Connected, but no tables named 'orders' or 'products' were found.")
            return

        current_table = ""
        for row in results:
            if row['table_name'] != current_table:
                current_table = row['table_name']
                print(f"\n📋 Table: {current_table.upper()}")
                print("-" * 30)
            print(f"  🔹 {row['column_name']} ({row['data_type']})")
            
        print("\n==================================================")
        print(" ✅ Connection & inspection complete!")
        print("==================================================")
        
    except Exception as e:
        print(f"❌ Database inspection failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_schema())