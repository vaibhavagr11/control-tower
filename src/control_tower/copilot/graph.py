from typing import TypedDict, Annotated, Literal
from langchain_core.messages import BaseMessage
from control_tower.schemas import IssueClassification, ResolutionRecommendation
from control_tower.copilot.chains import classify_chain, resolve_chain, communication_chain
from control_tower.copilot.guardrails import evaluate_gate
from control_tower.datalayer.mock_store import retrieve_context
from control_tower.policies.repository import retrieve_policies
from langgraph.graph import StateGraph, START, END

class CopilotState(TypedDict):
    # Inputs — supplied when the graph is invoked
    order_id: str
    message: str
    chat_history: list[BaseMessage]
    customer_history: list[dict]

    # Populated by nodes as the graph runs
    classification: IssueClassification
    context: dict
    policies: str
    recommendation: ResolutionRecommendation
    gate_reason: str
    autonomy_tier: Literal["autonomous", "assisted", "escalate"]
    customer_message: str


def _format_customer_history(history: list[dict]) -> str:
    """Render past-ticket summaries into a short, readable block for the resolver prompt."""
    if not history:
        return "(no prior tickets on file)"
    lines = [
        f"- {h['ticket_id']}: {h['issue_type']} -> {h['recommended_action']} ({h['gate_reason']})"
        for h in history
    ]
    return "/n".join(lines)

def triage_node(state: CopilotState) -> dict:
    """First contact: classify the issue type and urgency.
    The classification drives all downstream routing decisions."""
    classification = classify_chain.invoke(
        {
            "message": state["message"],
            "chat_history": state["chat_history"],
        }
    )
    return {"classification": classification}

def investigation_node(state: CopilotState) -> dict:
    """Gather all facts needed to resolve this ticket:
    order details, customer profile, account history, prior claims.
    Tool-heavy by design — no LLM reasoning here, just data retrieval.
    Phase 2 will extend this with carrier APIs, fraud checks, inventory lookups."""
    context = retrieve_context(state["order_id"])
    return {"context": context}

def policy_node(state: CopilotState) -> dict:
    """Retrieve policy rules relevant to this classified issue.

    Owns all retrieval and policy grounding — the resolution node
    does no retrieval of its own, only judgment on what this node surfaces."""

    classification = state["classification"]

    query = f"{classification.issue_type} {classification.urgency}: {state['message']}"
    policies = retrieve_policies(query)
    return {"policies": policies}

def _determine_autonomy_tier(context: dict, rec: ResolutionRecommendation,) -> Literal["autonomous", "assisted", "escalate"]:
    """Determine how much autonomy the resolution warrants.

    Phase 1: mostly 'assisted' — sets up the routing structure for Phase 2.
    The 'autonomous' lane is stubbed but not yet active."""
    order = context.get("order", {})
    customer = context.get("customer", {})

    order_value = order.get("order_value_usd", 0)
    prior_claims = customer.get("prior_refund_claims", 0)
    account_age = customer.get("account_age_days", 999)

    # Clear escalation signals — goes straight to a human specialist
    if (
        rec.fraud_risk == "high"
        or rec.confidence == "low"
        or order_value > 300
        or (prior_claims >= 3 and account_age < 30)
        or rec.recommended_action == "escalate_to_human"
    ):
        return "escalate"

    # Phase 2 will activate this lane for low-risk, high-confidence, low-value cases:
    # if rec.confidence == "high" and rec.fraud_risk == "low" and order_value < 50:
    #     return "autonomous"

    return "assisted"

def resolution_node(state: CopilotState) -> dict:
    """Pure judgment: determine the right action given facts + policy + risk.

    Does not draft the customer message — that's the communication node's job.
    Produces gate_reason (why approval is needed) and autonomy_tier (what kind)."""
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

def communication_node(state: CopilotState) -> dict:
    """Draft the customer-facing message.

    Pure generation — no judgment or retrieval here.
    Takes the resolution decision and produces a warm, clear message."""
    context = state["context"]
    customer_name = context.get("customer", {}).get("name", "")
    classification = state["classification"]
    recommendation = state["recommendation"]

    result = communication_chain.invoke({
        "message": state["message"],
        "customer_name": customer_name,
        "issue_type": classification.issue_type,
        "urgency": classification.urgency,
        "recommended_action": recommendation.recommended_action,
        "rationale": recommendation.rationale,
    })
    return {"customer_message": result.content}

graph_builder = StateGraph(CopilotState)

graph_builder.add_node("triage", triage_node)
graph_builder.add_node("investigation", investigation_node)
graph_builder.add_node("policy", policy_node)
graph_builder.add_node("resolution", resolution_node)
graph_builder.add_node("communication", communication_node)

graph_builder.add_edge(START, "triage")
graph_builder.add_edge("triage", "investigation")
graph_builder.add_edge("investigation", "policy")
graph_builder.add_edge("policy", "resolution")
graph_builder.add_edge("resolution", "communication")
graph_builder.add_edge("communication", END)

recommend_graph = graph_builder.compile()
