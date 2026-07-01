from datetime import date
from typing import Literal

from control_tower.copilot.chains import resolve_chain
from control_tower.copilot.guardrails import evaluate_gate
from control_tower.copilot.state import CopilotState
from control_tower.schemas import ResolutionRecommendation


def _format_customer_history(history: list[dict]) -> str:
    if not history:
        return "(no prior tickets on file)"
    lines = [
        f"- {h['ticket_id']}: {h['issue_type']} -> {h['recommended_action']} ({h['gate_reason']})"
        for h in history
    ]
    return "\n".join(lines)


def _compute_account_age_days(member_since: str) -> int:
    """Compute account age in days from member_since date string."""
    if not member_since:
        return 999
    try:
        joined = date.fromisoformat(member_since)
        return (date.today() - joined).days
    except ValueError:
        return 999


def _determine_autonomy_tier(
    context: dict,
    rec: ResolutionRecommendation,
) -> Literal["autonomous", "assisted", "escalate"]:
    order = context.get("order", {})
    customer = context.get("customer", {})

    order_value = order.get("value_usd", 0)
    prior_claims = len(customer.get("return_history", []))
    account_age = _compute_account_age_days(customer.get("member_since", ""))

    if (
        rec.fraud_risk == "high"
        or rec.confidence == "low"
        or order_value > 300
        or (prior_claims >= 3 and account_age < 30)
        or rec.recommended_action == "escalate_to_human"
    ):
        return "escalate"

    if (
        rec.confidence == "high"
        and rec.fraud_risk == "low"
        and order_value < 100
    ):
        return "autonomous"

    return "assisted"


def resolution_node(state: CopilotState) -> dict:
    """Pure judgment: determine the right action given facts + policy + risk.
    Does not draft the customer message — that's communication_node's job."""
    classification = state["classification"]
    recommendation = resolve_chain.invoke({
        "issue_type": classification.issue_type,
        "urgency": classification.urgency,
        "context": state["context"],
        "policies": state["policies"],
        "message": state["message"],
        "chat_history": state["chat_history"],
        "customer_history": _format_customer_history(state["customer_history"]),
    })
    gate_reason = evaluate_gate(state["context"], recommendation)
    autonomy_tier = _determine_autonomy_tier(state["context"], recommendation)
    return {
        "recommendation": recommendation,
        "gate_reason": gate_reason,
        "autonomy_tier": autonomy_tier,
    }