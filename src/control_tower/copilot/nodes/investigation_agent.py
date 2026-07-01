from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from control_tower.tools.carrier import get_tracking_status
from control_tower.tools.oms import lookup_order


# ─── Agent-local state ────────────────────────────────────────────────────────
# Separate from CopilotState — the subgraph owns its own state.
# Only what it needs as input and what it produces as output.

class InvestigationState(TypedDict):
    order_id: str
    order: dict
    customer: dict
    tracking: dict
    risk: dict


# ─── Nodes ────────────────────────────────────────────────────────────────────

def fetch_order_node(state: InvestigationState) -> dict:
    """Call the OMS to retrieve the full order and customer profile."""
    result = lookup_order.invoke({"order_id": state["order_id"]})
    return {
        "order": result.get("order", {}),
        "customer": result.get("customer", {}),
    }


def fetch_tracking_node(state: InvestigationState) -> dict:
    """Call the carrier API for live tracking data.
    Skipped (returns empty dict) if the order has no tracking number
    — e.g. cancelled or not yet shipped."""
    tracking_number = state["order"].get("tracking_number")
    if not tracking_number:
        return {"tracking": {}}

    result = get_tracking_status.invoke({"order_id": state["order_id"]})
    return {"tracking": result}


def assess_risk_node(state: InvestigationState) -> dict:
    """Compute fraud risk signals from customer history.
    Pure logic — no LLM, fast, auditable.

    Signals:
    - claim_count: number of prior returns/refunds
    - account_age_days: how long the account has existed
    - high_frequency: 3+ claims in the last 30 days
    - new_account: account less than 30 days old
    - risk_level: low / medium / high
    """
    from datetime import date

    customer = state["customer"]
    return_history = customer.get("return_history", [])
    member_since = customer.get("member_since", "")

    # Account age
    try:
        account_age_days = (date.today() - date.fromisoformat(member_since)).days
    except (ValueError, TypeError):
        account_age_days = 999

    # Claim frequency — count claims in the last 30 days
    recent_claims = [
        r for r in return_history
        if r.get("date") and
        (date.today() - date.fromisoformat(r["date"])).days <= 30
    ]

    claim_count = len(return_history)
    high_frequency = len(recent_claims) >= 3
    new_account = account_age_days < 30

    if high_frequency or (new_account and claim_count >= 2):
        risk_level = "high"
    elif claim_count >= 2 or new_account:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk": {
            "claim_count": claim_count,
            "account_age_days": account_age_days,
            "recent_claims": len(recent_claims),
            "high_frequency": high_frequency,
            "new_account": new_account,
            "risk_level": risk_level,
        }
    }


# ─── Build subgraph ───────────────────────────────────────────────────────────

_builder = StateGraph(InvestigationState)

_builder.add_node("fetch_order",    fetch_order_node)
_builder.add_node("fetch_tracking", fetch_tracking_node)
_builder.add_node("assess_risk",    assess_risk_node)

_builder.add_edge(START,           "fetch_order")
_builder.add_edge("fetch_order",   "fetch_tracking")
_builder.add_edge("fetch_tracking","assess_risk")
_builder.add_edge("assess_risk",    END)

investigation_agent = _builder.compile()