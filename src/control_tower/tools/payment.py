import uuid
from typing import Literal
from langchain_core.tools import tool
from control_tower.tools.data import ORDERS, REFUND_LOG


@tool
def process_refund(
    order_id: str,
    item_skus: list[str],
    refund_type: Literal["standard", "forced"],
) -> dict:
    """Process a refund for specific items in an order.

    item_skus: list of SKUs to refund — only the affected items, not the whole order.

    refund_type:
    - 'standard': return required before refund is issued. Used when the customer
      is shipping items back (company or customer reason). Refund is triggered
      once the return is received at the warehouse.
    - 'forced': refund issued immediately, no return required. Used when the item
      is damaged beyond use, lost by the carrier, or it is not cost-effective
      to require a return.
    """
    order = ORDERS.get(order_id)
    if not order:
        return {"success": False, "reason": f"Order {order_id} not found."}

    if order_id in REFUND_LOG:
        return {
            "success": False,
            "reason": f"A refund has already been processed for order {order_id}. "
                      f"Transaction ID: {REFUND_LOG[order_id]['transaction_id']}.",
        }

    # Resolve requested SKUs against the order's line items
    order_items = {i["sku"]: i for i in order["items"]}
    matched, missing = [], []
    refund_amount = 0.0

    for sku in item_skus:
        if sku in order_items:
            item = order_items[sku]
            matched.append(item["name"])
            refund_amount += item["unit_price_usd"] * item["qty"]
        else:
            missing.append(sku)

    if not matched:
        return {
            "success": False,
            "reason": f"None of the requested SKUs {item_skus} were found in order {order_id}.",
        }

    transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"

    if refund_type == "forced":
        REFUND_LOG[order_id] = {
            "transaction_id": transaction_id,
            "refund_type": "forced",
            "items": matched,
            "amount_usd": refund_amount,
            "status": "processed",
        }
        result = {
            "success": True,
            "transaction_id": transaction_id,
            "refund_type": "forced",
            "items_refunded": matched,
            "amount_usd": refund_amount,
            "reason": (
                f"Forced refund of ${refund_amount:.2f} issued immediately for: "
                f"{', '.join(matched)}. No return required. "
                f"Transaction ID: {transaction_id}. "
                "Amount will appear in the customer's account within 3-5 business days."
            ),
        }
    else:
        REFUND_LOG[order_id] = {
            "transaction_id": transaction_id,
            "refund_type": "standard",
            "items": matched,
            "amount_usd": refund_amount,
            "status": "pending_return",
        }
        result = {
            "success": True,
            "transaction_id": transaction_id,
            "refund_type": "standard",
            "items_refunded": matched,
            "amount_usd": refund_amount,
            "reason": (
                f"Standard refund of ${refund_amount:.2f} queued for: "
                f"{', '.join(matched)}. "
                f"Refund will be triggered once the return is received at our warehouse. "
                f"Transaction ID: {transaction_id}."
            ),
        }

    if missing:
        result["skus_not_found"] = missing

    return result