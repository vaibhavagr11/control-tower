from langsmith import traceable

from control_tower.copilot.chains import classify_chain, resolve_chain
from control_tower.copilot.guardrails import evaluate_gate
from control_tower.datalayer.mock_store import retrieve_context
from control_tower.policies.repository import retrieve_policies
from control_tower.schemas import (
    CopilotResult,
    IssueClassification,
    ResolutionRecommendation,
)
from typing import Literal, Optional
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

def _build_resolve_input(state: dict) -> dict:
    """Map the accumulated state into the keys resolve_chain expects."""
    c = state["classification"]
    return {
        "issue_type": c.issue_type,
        "urgency": c.urgency,
        "context": state["context"],
        "policies": state["policies"],
        "message": state["message"],
        "chat_history": state.get("chat_history", []),
        "customer_history": _format_customer_history(state.get("customer_history", [])),
    }

def _format_customer_history(history: list[dict]) -> str:
    """Render past-ticket summaries into a short, readable block for the resolver prompt."""
    if not history:
        return "(no prior tickets on file)"
    lines = [
        f"- {h['ticket_id']}: {h['issue_type']} -> {h['recommended_action']} ({h['gate_reason']})"
        for h in history
    ]
    return "\n".join(lines)

# The Phase 1 reasoning flow as a single composable Runnable.
# Input: {"order_id", "message"} → output: a state dict with everything assembled.
recommend_pipeline = (
    RunnablePassthrough.assign(
        classification = classify_chain,
        context = RunnableLambda(lambda s: retrieve_context(s["order_id"])),
    )
    | RunnablePassthrough.assign(
        policies=RunnableLambda(lambda s: retrieve_policies(f"{s['classification'].issue_type}: {s['message']}")),
    )
    | RunnablePassthrough.assign(
        recommendation=RunnableLambda(_build_resolve_input) | resolve_chain,
    )
)


class ResolutionCopilot:
    """Phase 1: classify → investigate → recommend. A human approves every action."""

    def __init__(self):
        # In-memory ledger now; a database in production.
        self.feedback_log: list[dict] = []
        self.conversation_history: dict[str, list[BaseMessage]] = {}
        self.customer_memory: dict[str, list[dict]] = {}


    @traceable(name="recommend_resolution", run_type="chain")
    def recommend(self, ticket_id: str, order_id: str, message: str) -> CopilotResult:
        history = self.conversation_history.get(ticket_id, [])

        # Look up which customer this order belongs to, then pull their past-ticket history.
        customer_id = retrieve_context(order_id).get("order", {}).get("customer_id")
        customer_history = self.customer_memory.get(customer_id, []) if customer_id else []

        try:
            state = recommend_pipeline.invoke({
                "order_id": order_id, 
                "message": message, 
                "chat_history": history, 
                "customer_history": customer_history
            })
            return_result = CopilotResult(
                ticket_id=ticket_id,
                classification=state["classification"],
                recommendation=state["recommendation"],
                requires_human_approval=True,   # Phase 1: always
                gate_reason=evaluate_gate(state["context"], state["recommendation"]),
            )

            history.append(HumanMessage(content= message))
            history.append(AIMessage(content= return_result.recommendation.customer_message_draft))
            self.conversation_history[ticket_id] = history

            if customer_id:
                self.customer_memory.setdefault(customer_id, []).append(
                    {
                        "ticket_id": ticket_id,
                        "issue_type": return_result.classification.issue_type,
                        "recommended_action": return_result.recommendation.recommended_action,
                        "gate_reason": return_result.gate_reason
                    }
                )

            return return_result
        
        except Exception as e:
            # Graceful degradation: hand the ticket to a human instead of crashing.
            return CopilotResult(
                ticket_id=ticket_id,
                classification=IssueClassification(
                    issue_type="other", urgency="medium",
                    reasoning=f"Classification failed: {e}",
                ),
                recommendation=ResolutionRecommendation(
                    recommended_action="escalate_to_human",
                    rationale=f"The copilot could not process this ticket: {e}",
                    confidence="low",
                    customer_message_draft="Thanks for reaching out — a specialist will follow up shortly.",
                ),
                requires_human_approval=True,
                gate_reason="copilot error; escalated to human",
            )
        
    
    @traceable(name="record_decision", run_type="tool")
    def record_decision(
        self,
        result: CopilotResult,
        agent_decision: Literal["accept", "edit", "reject"],
        agent_action: Optional[str] = None,
        note: str = "",
    ) -> dict:
        """An agent approves/edits/rejects the recommendation. The Phase 1 accuracy ledger."""
        entry = {
            "ticket_id": result.ticket_id,
            "recommended_action": result.recommendation.recommended_action,
            "agent_decision": agent_decision,
            "agent_action": agent_action or result.recommendation.recommended_action,
            "matched": agent_decision == "accept",
            "note": note,
        }
        self.feedback_log.append(entry)
        return entry
    
    def accuracy(self) -> Optional[float]:
        """Acceptance rate so far — the gate metric for progressing to Phase 2."""
        if not self.feedback_log:
            return None
        accepted = sum(1 for e in self.feedback_log if e["matched"])
        return round(accepted / len(self.feedback_log), 3)