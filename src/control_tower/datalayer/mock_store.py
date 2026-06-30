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
    "ORD-5004": {"customer_id": "C-100", "item": "USB Cable", "value_usd": 12.00,
             "carrier_status": "delivered", "tracking_signal": "delivered_confirmed", "days_since_order": 3},
    "ORD-5005": {"customer_id": "C-100", "item": "Smart Speaker", "value_usd": 65.00,
             "carrier_status": "delivered", "tracking_signal": "delivered_no_signature", "days_since_order": 1},
}


def retrieve_context(order_id: str) -> dict:
    """Assemble the full operational context for an order: the order + its customer."""
    order = ORDERS.get(order_id, {})
    customer = CUSTOMERS.get(order.get("customer_id", ""), {})
    return {"order_id": order_id, "order": order, "customer": customer}

def process_refund(order_id: str, attempt: int = 0) -> dict:
    """Simulate a refund. Fails on first attempt (transient gateway timeout)
    to exercise the retry loop, succeeds on retry."""
    order = ORDERS.get(order_id, {})
    if not order:
        return {"success": False, "details": f"Order {order_id} not found."}
    if attempt == 0:
        return {"success": False, "details": "Payment gateway timeout — please retry."}
    return {
        "success": True,
        "details": f"Refund of ${order.get('value_usd', 0):.2f} processed for {order.get('item', 'item')}.",
    }


def create_replacement_order(order_id: str, attempt: int = 0) -> dict:
    """Simulate creating a replacement shipment. Succeeds immediately."""
    order = ORDERS.get(order_id, {})
    if not order:
        return {"success": False, "details": f"Order {order_id} not found."}
    return {
        "success": True,
        "details": f"Replacement for {order.get('item', 'item')} created and queued for shipment.",
    }


def apply_compensation(order_id: str, attempt: int = 0) -> dict:
    """Simulate applying store credit. Succeeds immediately."""
    order = ORDERS.get(order_id, {})
    if not order:
        return {"success": False, "details": f"Order {order_id} not found."}
    return {
        "success": True,
        "details": f"Store credit applied to account for order {order_id}.",
    }