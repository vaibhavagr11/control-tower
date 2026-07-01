from typing import Literal

from control_tower.copilot.state import CopilotState
from control_tower.tools.carrier import generate_return_label
from control_tower.tools.oms import create_replacement_order
from control_tower.tools.payment import process_refund

MAX_ACTION_RETRIES = 3

# Issue types where the fault is the retailer's — company pays for return
_COMPANY_FAULT_ISSUES = {
    "wrong_item",
    "damaged_item",
    "delivery_not_received",
}


def _get_return_reason_type(issue_type: str) -> Literal["company", "customer"]:
    return "company" if issue_type in _COMPANY_FAULT_ISSUES else "customer"


def _get_all_skus(context: dict) -> list[str]:
    """Default to all SKUs in the order — refined per-item logic comes in Phase 2.3."""
    items = context.get("order", {}).get("items", [])
    return [i["sku"] for i in items]


def action_router_node(state: CopilotState) -> dict:
    """No-op routing hub — conditional edge decides which action node runs next.
    Also serves as the retry target when an action fails."""
    return {}


def refund_node(state: CopilotState) -> dict:
    """Issue a refund for the order.
    Forced if the fault is the retailer's, standard if customer-initiated."""
    issue_type = state["classification"].issue_type
    refund_type = "forced" if issue_type in _COMPANY_FAULT_ISSUES else "standard"
    item_skus = _get_all_skus(state["context"])

    result = process_refund.invoke({
        "order_id": state["order_id"],
        "item_skus": item_skus,
        "refund_type": refund_type,
    })
    return {"action_result": result}


def replacement_node(state: CopilotState) -> dict:
    """Create a replacement shipment.
    Free if retailer's fault, charged at original price if customer exchange."""
    issue_type = state["classification"].issue_type
    reason_type = "company" if issue_type in _COMPANY_FAULT_ISSUES else "customer_exchange"
    item_skus = _get_all_skus(state["context"])

    result = create_replacement_order.invoke({
        "order_id": state["order_id"],
        "item_skus": item_skus,
        "reason_type": reason_type,
    })
    return {"action_result": result}


def return_label_node(state: CopilotState) -> dict:
    """Generate a return shipping label.
    Prepaid if retailer's fault, customer pays if customer-initiated."""
    issue_type = state["classification"].issue_type
    return_reason_type = _get_return_reason_type(issue_type)
    item_skus = _get_all_skus(state["context"])

    result = generate_return_label.invoke({
        "order_id": state["order_id"],
        "item_skus": item_skus,
        "return_reason_type": return_reason_type,
    })
    return {"action_result": result}


def verify_node(state: CopilotState) -> dict:
    """Check if the action succeeded.
    On failure, increments retry_count so the router knows this is a retry."""
    if not state["action_result"].get("success", False):
        return {"retry_count": state["retry_count"] + 1}
    return {}