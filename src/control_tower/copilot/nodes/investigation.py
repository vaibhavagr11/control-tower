from control_tower.copilot.state import CopilotState
from control_tower.tools.oms import lookup_order


def investigation_node(state: CopilotState) -> dict:
    """Gather all facts needed to resolve this ticket.
    Calls the OMS to retrieve the full order and customer profile.
    Phase 2 will extend this with parallel carrier and fraud checks."""
    result = lookup_order.invoke({"order_id": state["order_id"]})
    return {"context": result}