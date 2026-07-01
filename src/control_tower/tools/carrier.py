from typing import Literal
from langchain_core.tools import tool
from control_tower.tools.data import ORDERS, TRACKING_EVENTS


@tool
def get_tracking_status(order_id: str) -> dict:
    """Get the latest carrier tracking status for an order.
    Returns current location, status, full event history, estimated delivery,
    and delay reason if applicable."""
    order = ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found."}

    if not order.get("tracking_number"):
        return {
            "error": f"Order {order_id} has no tracking number — "
                     f"current status is '{order['status']}'."
        }

    tracking = TRACKING_EVENTS.get(order["tracking_number"])
    if not tracking:
        return {"error": f"No tracking data found for tracking number {order['tracking_number']}."}

    return {
        "order_id": order_id,
        "carrier": order["carrier"],
        "tracking_number": order["tracking_number"],
        "status": tracking["status"],
        "location": tracking["location"],
        "last_updated": tracking["timestamp"],
        "estimated_delivery": tracking["estimated_delivery"],
        "delay_reason": tracking["delay_reason"],
        "events": tracking["events"],
    }


@tool
def generate_return_label(
    order_id: str,
    item_skus: list[str],
    return_reason_type: Literal["company", "customer"],
) -> dict:
    """Generate a return shipping label for specific items in a delivered order.

    item_skus: list of SKUs the customer is returning.

    return_reason_type:
    - 'company': wrong item sent, item damaged/defective, or carrier lost it —
      retailer's fault. Prepaid label generated, customer pays nothing.
    - 'customer': changed mind, ordered wrong size, preference change —
      customer's decision. Return instructions provided but customer
      arranges and pays for their own shipping.
    """
    order = ORDERS.get(order_id)
    if not order:
        return {"success": False, "reason": f"Order {order_id} not found."}

    if order["status"] not in ("delivered",):
        return {
            "success": False,
            "reason": f"Return labels can only be generated for delivered orders. "
                      f"Current status: '{order['status']}'.",
        }

    # Resolve requested SKUs against the order's line items
    order_items = {i["sku"]: i for i in order["items"]}
    matched, missing = [], []

    for sku in item_skus:
        if sku in order_items:
            matched.append(order_items[sku]["name"])
        else:
            missing.append(sku)

    if not matched:
        return {
            "success": False,
            "reason": f"None of the requested SKUs {item_skus} were found in order {order_id}.",
        }

    # Simulate label/instructions generation
    if return_reason_type == "company":
        result = {
            "success": True,
            "return_reason_type": "company",
            "prepaid": True,
            "label_url": f"https://returns.example.com/label/{order_id}-PREPAID",
            "items_returning": matched,
            "instructions": (
                f"A prepaid {order['carrier']} return label has been emailed to the customer. "
                "No cost to the customer. Items must be returned within 30 days."
            ),
        }
    else:
        result = {
            "success": True,
            "return_reason_type": "customer",
            "prepaid": False,
            "return_address": "Returns Center, 123 Warehouse Ave, Newark, NJ 07102",
            "items_returning": matched,
            "instructions": (
                "Customer is responsible for return shipping costs. "
                "Items should be sent to our returns center within 30 days. "
                "Refund will be processed within 5-7 business days of receipt."
            ),
        }

    if missing:
        result["skus_not_found"] = missing

    return result