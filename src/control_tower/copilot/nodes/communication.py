from control_tower.copilot.chains import communication_chain
from control_tower.copilot.state import CopilotState


def communication_node(state: CopilotState) -> dict:
    """Draft the customer-facing message.
    Adjusts tone based on whether the action was actually taken (autonomous)
    or is pending human approval (assisted)."""
    context = state["context"]
    customer_name = context.get("customer", {}).get("name", "")
    classification = state["classification"]
    recommendation = state["recommendation"]
    action_result = state.get("action_result", {})

    action_taken = action_result.get("success", False)
    action_details = action_result.get("reason", "") if action_taken else ""

    result = communication_chain.invoke({
        "message": state["message"],
        "customer_name": customer_name,
        "issue_type": classification.issue_type,
        "urgency": classification.urgency,
        "recommended_action": recommendation.recommended_action,
        "rationale": recommendation.rationale,
        "action_taken": "YES — already executed" if action_taken else "NO — pending human approval",
        "action_details": action_details,
    })
    return {"customer_message": result.content}