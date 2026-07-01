from control_tower.copilot.state import CopilotState
from control_tower.policies.repository import retrieve_policies


def policy_node(state: CopilotState) -> dict:
    """Retrieve policy rules relevant to this classified issue.
    Owns all retrieval and policy grounding — the resolution node
    does no retrieval of its own, only judgment on what this node surfaces."""
    classification = state["classification"]
    query = f"{classification.issue_type} {classification.urgency}: {state['message']}"
    policies = retrieve_policies(query)
    return {"policies": policies}