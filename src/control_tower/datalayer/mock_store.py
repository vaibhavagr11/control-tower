CUSTOMERS = {
    "C-100": {"name": "Dana Lee",  "lifetime_orders": 42, "prior_refund_claims": 0, "account_age_days": 1300},
    "C-200": {"name": "Sam Cruz",  "lifetime_orders": 3,  "prior_refund_claims": 4, "account_age_days": 21},
}

ORDERS = {
    "ORD-5001": {"customer_id": "C-100", "item": "Wireless Headphones", "value_usd": 89.00,
                 "carrier_status": "delivered", "tracking_signal": "delivered_no_signature", "days_since_order": 6},
    "ORD-5002": {"customer_id": "C-200", "item": "4K Monitor", "value_usd": 410.00,
                 "carrier_status": "delivered", "tracking_signal": "delivered_no_signature", "days_since_order": 2},
    "ORD-5003": {"customer_id": "C-100", "item": "Mechanical Keyboard", "value_usd": 120.00,
                 "carrier_status": "in_transit", "tracking_signal": "delayed_at_hub", "days_since_order": 9},
}


def retrieve_context(order_id: str) -> dict:
    """Assemble the full operational context for an order: the order + its customer."""
    order = ORDERS.get(order_id, {})
    customer = CUSTOMERS.get(order.get("customer_id", ""), {})
    return {"order_id": order_id, "order": order, "customer": customer}