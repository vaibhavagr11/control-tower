from typing import TypedDict
from langchain_core.messages import BaseMessage
from control_tower.schemas import IssueClassification, ResolutionRecommendation
from control_tower.copilot.chains import classify_chain, resolve_chain
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


def _format_customer_history(history: list[dict]) -> str:
    """Render past-ticket summaries into a short, readable block for the resolver prompt."""
    if not history:
        return "(no prior tickets on file)"
    lines = [
        f"- {h['ticket_id']}: {h['issue_type']} -> {h['recommended_action']} ({h['gate_reason']})"
        for h in history
    ]
    return "/n".join(lines)

def classify_node(state: CopilotState) -> dict:
    """Classify the issue type and urgency from the customer's message."""
    classification = classify_chain.invoke(
        {
            "message": state["message"],
            "chat_history": state["chat_history"],
        }
    )
    return {"classification": classification}

def retrieve_context_node(state: CopilotState) -> dict:
    """Look up the order + customer record."""
    return {"context": retrieve_context(state["order_id"])}

def retrieve_policy_node(state: CopilotState) -> dict:
    """Retrieve the policy rules relevant to the classified issue."""
    classification = state["classification"]
    policies = retrieve_policies(f"{classification.issue_type}: {state['message']}")
    return {"policies": policies}

def resolve_node(state: CopilotState) -> dict:
    """Recommend a resolution, grounded in context + policy + history."""
    classifiction = state["classification"]
    recommendation = resolve_chain.invoke(
        {
            "issue_type": classifiction.issue_type,
            "urgency": classifiction.urgency,
            "context": state["context"],
            "policies": state["policies"],
            "message": state["message"],
            "chat_history": state["chat_history"],
            "customer_history": _format_customer_history(state["customer_history"]),
        }
    )
    return {"recommendation": recommendation}

def gate_node(state : CopilotState) -> dict:
    """Decide why this recommendation needs human approval (Phase 1: always)."""
    gate_reason = evaluate_gate(state["context"], state["recommendation"])
    return {"gate_reason": gate_reason}


graph_builder = StateGraph(CopilotState)

graph_builder.add_node("classify", classify_node)
graph_builder.add_node("retrieve_context", retrieve_context_node)
graph_builder.add_node("retrieve_policy", retrieve_policy_node)
graph_builder.add_node("resolve", resolve_node)
graph_builder.add_node("gate", gate_node)

graph_builder.add_edge(START, "classify")
graph_builder.add_edge("classify", "retrieve_context")
graph_builder.add_edge("retrieve_context", "retrieve_policy")
graph_builder.add_edge("retrieve_policy", "resolve")
graph_builder.add_edge("resolve", "gate")
graph_builder.add_edge("gate", END)

recommend_graph = graph_builder.compile()
