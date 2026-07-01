from langgraph.graph import StateGraph, START, END

from control_tower.copilot.state import CopilotState
from control_tower.copilot.nodes.triage import triage_node
from control_tower.copilot.nodes.investigation import investigation_node
from control_tower.copilot.nodes.policy import policy_node
from control_tower.copilot.nodes.resolution import resolution_node
from control_tower.copilot.nodes.communication import communication_node
from control_tower.copilot.nodes.escalation import escalation_node
from control_tower.copilot.nodes.actions import (
    action_router_node,
    refund_node,
    replacement_node,
    return_label_node,
    verify_node,
)
from control_tower.copilot.nodes.clarification import (
    clarification_node,
    simulate_response_node,
)
from control_tower.copilot.routing import (
    route_by_tier,
    route_by_action,
    route_verify,
    route_after_clarification,
)

# ─── Build graph ───────────────────────────────────────────────────────────────

graph_builder = StateGraph(CopilotState)

# Register nodes
graph_builder.add_node("triage",            triage_node)
graph_builder.add_node("investigation",     investigation_node)
graph_builder.add_node("policy",            policy_node)
graph_builder.add_node("resolution",        resolution_node)
graph_builder.add_node("communication",     communication_node)
graph_builder.add_node("escalation",        escalation_node)
graph_builder.add_node("action_router",     action_router_node)
graph_builder.add_node("refund",            refund_node)
graph_builder.add_node("replacement",       replacement_node)
graph_builder.add_node("return_label",      return_label_node)
graph_builder.add_node("verify",            verify_node)
graph_builder.add_node("clarification",     clarification_node)
graph_builder.add_node("simulate_response", simulate_response_node)

# Main pipeline
graph_builder.add_edge(START,          "triage")
graph_builder.add_edge("triage",       "investigation")
graph_builder.add_edge("investigation","policy")
graph_builder.add_edge("policy",       "resolution")

# Branch by autonomy tier
graph_builder.add_conditional_edges(
    "resolution", route_by_tier,
    {"assisted": "communication", "autonomous": "action_router", "escalate": "escalation"},
)

# Action dispatch
graph_builder.add_conditional_edges(
    "action_router", route_by_action,
    {
        "issue_refund":          "refund",
        "send_replacement":      "replacement",
        "generate_return_label": "return_label",
        "request_more_info":     "clarification",
    },
)

# Action nodes → verify
graph_builder.add_edge("refund",        "verify")
graph_builder.add_edge("replacement",   "verify")
graph_builder.add_edge("return_label",  "verify")

# Verify: retry loop or proceed
graph_builder.add_conditional_edges(
    "verify", route_verify,
    {"retry": "action_router", "success": "communication"},
)

# Clarification loop
graph_builder.add_edge("clarification", "simulate_response")
graph_builder.add_conditional_edges(
    "simulate_response", route_after_clarification,
    {"retriage": "triage", "handoff": "communication"},
)

# Terminal edges
graph_builder.add_edge("communication", END)
graph_builder.add_edge("escalation",    END)

recommend_graph = graph_builder.compile()