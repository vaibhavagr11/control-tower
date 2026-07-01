from control_tower.copilot.state import CopilotState
from control_tower.copilot.nodes.investigation_agent import investigation_agent

def investigation_node(state: CopilotState) -> dict:
    """Run the Investigation Agent subgraph.
    Fetches order + customer (OMS), live tracking (carrier),
    and computes fraud risk signals — then packages everything
    into context for the policy and resolution nodes."""
    result = investigation_agent.invoke({"order_id": state["order_id"]})
    context = {
        "order_id": state["order_id"],
        "order": result["order"],
        "customer": result["customer"],
        "tracking": result["tracking"],
        "risk": result["risk"],
    }
    return {"context": context}