from typing import TypedDict, Annotated, Literal
from langchain_core.messages import BaseMessage
from control_tower.schemas import IssueClassification, ResolutionRecommendation
from control_tower.copilot.chains import classify_chain, resolve_chain, communication_chain, clarification_chain, simulate_response_chain
from control_tower.copilot.guardrails import evaluate_gate
from control_tower.datalayer.mock_store import retrieve_context, process_refund, create_replacement_order, apply_compensation
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

    # Autonomous action execution
    action_result: dict          # {"success": bool, "details": str}
    retry_count: int             # action retry counter, max 3
    clarification_count: int     # clarification loop counter, max 2
    clarification_question: str  # what we asked the customer


def _format_customer_history(history: list[dict]) -> str:
    """Render past-ticket summaries into a short, readable block for the resolver prompt."""
    if not history:
        return "(no prior tickets on file)"
    lines = [
        f"- {h['ticket_id']}: {h['issue_type']} -> {h['recommended_action']} ({h['gate_reason']})"
        for h in history
    ]
    return "\n".join(lines)

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

    order_value = order.get("value_usd", 0)
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

    # Autonomous: high confidence, low fraud, low-value order
    if (
        rec.confidence == "high"
        and rec.fraud_risk == "low"
        and order_value < 100
    ):
        return "autonomous"
     
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
    Adjusts tone based on whether the action was actually taken (autonomous)
    or is pending human approval (assisted)."""
    context = state["context"]
    customer_name = context.get("customer", {}).get("name", "")
    classification = state["classification"]
    recommendation = state["recommendation"]
    action_result = state.get("action_result", {})

    action_taken = action_result.get("success", False)
    action_details = action_result.get("details", "") if action_taken else ""

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

def route_by_tier(state: CopilotState) -> str:
    """Read autonomy_tier from state and return the next node name."""
    return state["autonomy_tier"]

def escalation_node(state: CopilotState) -> dict:
    """Fast-path for tickets that need specialist handling.

    Produces a consistent, deterministic escalation message — intentionally
    not LLM-generated, so tone and content stay predictable and never leak
    internal fraud/risk reasoning to the customer.

    Phase 2.1: will also create a ticket in the specialist queue."""

    context = state["context"]
    customer_name = context.get("customer", {}).get("name", "")
    greeting = f"Hi {customer_name} — " if customer_name else ""
    customer_message = (
        f"{greeting}I'm sorry for the trouble. "
        "Your case needs a specialist's review and someone from our team "
        "will follow up with you shortly with next steps."
    )
    return {"customer_message": customer_message}

def route_by_action(state: CopilotState) -> str:
    """Route to the appropriate action node based on recommended_action.
    Falls back to clarification for any unmapped action rather than crashing."""
    action = state["recommendation"].recommended_action
    valid = {
        "issue_refund", "send_replacement", "offer_compensation",
        "generate_return_label", "request_more_info",
    }
    return action if action in valid else "request_more_info"


def return_label_node(state: CopilotState) -> dict:
    """Generate a return shipping label for the customer."""
    order = state["context"].get("order", {})
    result = {
        "success": True,
        "details": f"Return label generated for {order.get('item', 'item')} — check your email.",
    }
    return {"action_result": result}

def action_router_node(state: CopilotState) -> dict:
    """No-op routing hub — conditional edge decides which action node runs next.
    Also serves as the retry target when an action fails and needs to re-run."""
    return {}

def refund_node(state: CopilotState) -> dict:
    """Execute a refund. Passes retry_count so the mock knows if this is a retry."""
    result = process_refund(state["order_id"], attempt=state["retry_count"])
    return {"action_result": result}

def replacement_node(state: CopilotState) -> dict:
    """Execute a replacement shipment."""
    result = create_replacement_order(state["order_id"], attempt=state["retry_count"])
    return {"action_result": result}

def compensation_node(state: CopilotState) -> dict:
    """Apply store credit compensation."""
    result = apply_compensation(state["order_id"], attempt=state["retry_count"])
    return {"action_result": result}

MAX_ACTION_RETRIES = 3   # max total attempts (initial + 2 retries)
MAX_CLARIFICATIONS = 2

def verify_node(state: CopilotState) -> dict:
    """Check if the action succeeded.
    On failure, increments retry_count so action nodes know this is a retry."""
    if not state["action_result"].get("success", False):
        return {"retry_count": state["retry_count"] + 1}
    return {}


def route_verify(state: CopilotState) -> str:
    """After verify_node updates retry_count, decide: retry action or proceed.
    Falls through to communication if max retries exceeded (action_result will
    carry success=False so communication can adjust its message)."""
    action_failed = not state["action_result"].get("success", False)
    under_limit = state["retry_count"] < MAX_ACTION_RETRIES
    if action_failed and under_limit:
        return "retry"
    return "success"

def clarification_node(state: CopilotState) -> dict:
    """Ask the customer for the one most important missing piece of information.
    Increments clarification_count and sets customer_message to the question."""
    question = clarification_chain.invoke({
        "issue_type": state["classification"].issue_type,
        "message": state["message"],
    })
    return {
        "clarification_question": question.content,
        "customer_message": question.content,
        "clarification_count": state["clarification_count"] + 1,
    }


def simulate_response_node(state: CopilotState) -> dict:
    """Simulate a realistic customer reply to the clarification question.
    Appends the response to state['message'] so re-triage has full context.
    In production this node would pause and wait for the real customer reply."""
    response = simulate_response_chain.invoke({
        "original_message": state["message"],
        "clarification_question": state["clarification_question"],
    })
    augmented_message = (
        f"{state['message']}\n"
        f"[Customer follow-up]: {response.content}"
    )
    return {"message": augmented_message}


def route_after_clarification(state: CopilotState) -> str:
    """Re-triage with the augmented message if under the clarification limit.
    Fall back to communication once we've hit the limit — human takes over."""
    if state["clarification_count"] < MAX_CLARIFICATIONS:
        return "retriage"
    return "handoff"

graph_builder = StateGraph(CopilotState)

# Register all nodes
graph_builder.add_node("triage", triage_node)
graph_builder.add_node("investigation", investigation_node)
graph_builder.add_node("policy", policy_node)
graph_builder.add_node("resolution", resolution_node)
graph_builder.add_node("action_router", action_router_node)
graph_builder.add_node("refund", refund_node)
graph_builder.add_node("replacement", replacement_node)
graph_builder.add_node("compensation", compensation_node)
graph_builder.add_node("return_label", return_label_node)
graph_builder.add_node("verify", verify_node)
graph_builder.add_node("clarification", clarification_node)
graph_builder.add_node("simulate_response", simulate_response_node)
graph_builder.add_node("communication", communication_node)
graph_builder.add_node("escalation", escalation_node)

# Main pipeline — always sequential
graph_builder.add_edge(START, "triage")
graph_builder.add_edge("triage", "investigation")
graph_builder.add_edge("investigation", "policy")
graph_builder.add_edge("policy", "resolution")

# Branch by autonomy tier
graph_builder.add_conditional_edges(
    "resolution",
    route_by_tier,
    {
        "assisted":   "communication",
        "autonomous": "action_router",
        "escalate":   "escalation",
    },
)

# Action router → individual action nodes
graph_builder.add_conditional_edges(
    "action_router",
    route_by_action,
    {
        "issue_refund":          "refund",
        "send_replacement":      "replacement",
        "offer_compensation":    "compensation",
        "generate_return_label": "return_label",
        "request_more_info":     "clarification",
    },
)

# Action nodes → verify (all four feed into the same verify node)
graph_builder.add_edge("refund", "verify")
graph_builder.add_edge("replacement", "verify")
graph_builder.add_edge("compensation", "verify")
graph_builder.add_edge("return_label", "verify")

# Verify: retry loop or proceed
graph_builder.add_conditional_edges(
    "verify",
    route_verify,
    {
        "retry":   "action_router",
        "success": "communication",
    },
)

# Clarification loop
graph_builder.add_edge("clarification", "simulate_response")
graph_builder.add_conditional_edges(
    "simulate_response",
    route_after_clarification,
    {
        "retriage": "triage",
        "handoff":  "communication",
    },
)

# Terminal edges
graph_builder.add_edge("communication", END)
graph_builder.add_edge("escalation", END)

recommend_graph = graph_builder.compile()
