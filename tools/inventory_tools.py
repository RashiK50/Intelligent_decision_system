import asyncio

async def check_current_stock(product_id: str, warehouse_id: str = None) -> dict:
    """
    Simulates a live API ping to an external Warehouse Management System (WMS)
    to get real-time stock levels, bypassing the delayed data warehouse.
    """
    warehouse_label = warehouse_id if warehouse_id else "All Warehouses"
    print(f"🔧 [TOOL EXECUTED] Fetching live stock for Product {product_id} at {warehouse_label}...")
    
    # Simulate a network delay to an external API
    await asyncio.sleep(0.5)
    
    # Mock response from a WMS (In reality, use httpx to hit your API here)
    mock_wms_response = {
        "product_id": product_id,
        "warehouse": warehouse_label,
        "on_hand": 142,
        "allocated": 12,
        "available_to_sell": 130,
        "status": "In Stock"
    }
    
    return mock_wms_response