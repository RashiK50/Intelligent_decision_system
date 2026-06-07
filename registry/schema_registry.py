SCHEMA_REGISTRY = {

    "customers": {
        "description": "Customer information",
        "primary_key": "customer_id",
        "columns": [
            "customer_id",
            "customer_unique_id",
            "customer_city",
            "customer_state",
            "customer_zip_code_prefix"
        ]
    },

    "orders": {
        "description": "Customer orders",
        "primary_key": "order_id",
        "foreign_keys": {
            "customer_id": "customers.customer_id"
        },
        "columns": [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_customer_date",
            "order_delivered_carrier_date",
            "order_estimated_delivery_date"
        ]
    },

    "products": {
        "description": "Product catalog",
        "primary_key": "product_id",
        "columns": [
            "product_id",
            "product_category_name",
            "product_weight_g",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm"
        ]
    },

    "sellers": {
        "description": "Seller information",
        "primary_key": "seller_id",
        "columns": [
            "seller_id",
            "seller_city",
            "seller_state",
            "seller_zip_code_prefix",

        ]
    },

    "order_items": {
        "description": "Items belonging to orders",
        "columns": [
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "price",
            "freight_value",
            "shipping_limit_date"
        ]
    },

    "order_payments": {
        "description": "Order payment information",
        "columns": [
            "order_id",
            "payment_type",
            "payment_installments",
            "payment_value",
            "payment_sequential"
        ]
    },

    "order_reviews": {
        "description": "Customer reviews",
        "columns": [
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp"
        ]
    },

    "category_translation": {
        "description": "Portuguese to English category mapping",
        "columns": [
            "product_category_name",
            "product_category_name_english"
        ]
    }
}