from control_tower.copilot.state import CopilotState
from control_tower.copilot.chains import classify_chain


def triage_node(state: CopilotState) -> dict:
    """First contact: classify the issue type and urgency.
    The classification drives all downstream routing decisions."""
    classification = classify_chain.invoke({
        "message": state["message"],
        "chat_history": state["chat_history"],
    })
    return {"classification": classification}