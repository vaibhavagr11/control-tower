from typing import Literal
from langchain_core.tools import tool
from control_tower.tools.data import CUSTOMERS, ORDERS

@tool
def lookup_order(order_id: str) -> dict:
    """Look up a customer order by order ID.
    Returns full order details including all line items, order status,
    tracking number, carrier, and the customer profile."""
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found."}

    customer = CUSTOMERS.get(order["customer_id"], {})
    return {
        "order_id": order_id,
        "order": order,
        "customer": customer,
    }

@tool
def cancel_order(order_id: str) -> dict:
    """Cancel an order that has not yet shipped.
    Only works if order status is 'pending' or 'processing'.
    Returns success/failure and the reason if cancellation is not possible."""
    order = ORDERS.get(order_id)
    if not order:
        return {"success": False, "reason": f"Order {order_id} not found."}

    if order["status"] not in ("pending", "processing"):
        return {
            "success": False,
            "reason": f"Order cannot be cancelled — current status is '{order['status']}'. "
                      "Only pending or processing orders can be cancelled.",
        }

    order["status"] = "cancelled"
    return {
        "success": True,
        "reason": f"Order {order_id} has been cancelled. "
                  "A full refund will be issued within 3-5 business days.",
    }

@tool
def create_replacement_order(
    order_id: str,
    item_skus: list[str],
    reason_type: Literal["company", "customer_exchange"],
) -> dict:
    """Create a replacement shipment for specific items in a delivered order.

    item_skus: list of SKUs to replace — only the affected items, not the whole order.

    reason_type:
    - 'company': free replacement — wrong item sent, item damaged, or lost (retailer's fault).
      Customer is not charged. Retailer absorbs the cost.
    - 'customer_exchange': customer is charged at original unit price — size swap,
      color preference change, or other customer-initiated exchange.
    """
    order = ORDERS.get(order_id)
    if not order:
        return {"success": False, "reason": f"Order {order_id} not found."}

    if order["status"] != "delivered":
        return {
            "success": False,
            "reason": f"Replacement can only be created for delivered orders. "
                      f"Current status: '{order['status']}'.",
        }

    # Resolve requested SKUs against the order's line items
    order_items = {i["sku"]: i for i in order["items"]}
    matched, missing = [], []
    charge_usd = 0.0

    for sku in item_skus:
        if sku in order_items:
            item = order_items[sku]
            matched.append(item["name"])
            if reason_type == "customer_exchange":
                charge_usd += item["unit_price_usd"] * item["qty"]
        else:
            missing.append(sku)

    if not matched:
        return {
            "success": False,
            "reason": f"None of the requested SKUs {item_skus} were found in order {order_id}.",
        }

    replacement_id = f"ORD-RPL-{order_id}"
    result = {
        "success": True,
        "replacement_order_id": replacement_id,
        "items_replaced": matched,
        "reason_type": reason_type,
        "charge_usd": charge_usd if reason_type == "customer_exchange" else 0.0,
        "reason": (
            f"Replacement order {replacement_id} created for: {', '.join(matched)}. "
            f"Expected delivery in 3-5 business days. "
            + (f"Amount charged: ${charge_usd:.2f}."
               if reason_type == "customer_exchange"
               else "No charge — retailer is covering this replacement.")
        ),
    }

    if missing:
        result["skus_not_found"] = missing

    return result

@tool
def lookup_orders_by_customer(customer_id: str) -> dict:
    """Fetch all orders for a given customer ID.
    Returns customer profile and their full order history with status summaries.
    Used when the specific order ID is not yet known."""
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found."}

    orders = []
    for order_id in customer["order_history"]:
        order = ORDERS.get(order_id)
        if order:
            orders.append({
                "order_id": order_id,
                "status": order["status"],
                "items": [i["name"] for i in order["items"]],
                "value_usd": order["value_usd"],
                "days_since_order": order["days_since_order"],
            })

    return {
        "customer": customer,
        "orders": orders,
    }