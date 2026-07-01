from typing import Literal

from control_tower.copilot.nodes.actions import MAX_ACTION_RETRIES
from control_tower.copilot.nodes.clarification import MAX_CLARIFICATIONS
from control_tower.copilot.state import CopilotState


def route_by_tier(state: CopilotState) -> Literal["autonomous", "assisted", "escalate"]:
    """Read autonomy_tier from state and return the next node name."""
    return state["autonomy_tier"]


def route_by_action(state: CopilotState) -> str:
    """Route to the appropriate action node based on recommended_action.
    Falls back to clarification for any unmapped action."""
    action = state["recommendation"].recommended_action
    valid = {
        "issue_refund",
        "send_replacement",
        "generate_return_label",
        "request_more_info",
    }
    return action if action in valid else "request_more_info"


def route_verify(state: CopilotState) -> Literal["retry", "success"]:
    """After verify_node updates retry_count, decide: retry action or proceed.
    Falls through to communication if max retries exceeded."""
    action_failed = not state["action_result"].get("success", False)
    under_limit = state["retry_count"] < MAX_ACTION_RETRIES
    if action_failed and under_limit:
        return "retry"
    return "success"


def route_after_clarification(state: CopilotState) -> Literal["retriage", "handoff"]:
    """Re-triage with augmented message if under the clarification limit.
    Fall back to communication once the limit is hit."""
    if state["clarification_count"] < MAX_CLARIFICATIONS:
        return "retriage"
    return "handoff"