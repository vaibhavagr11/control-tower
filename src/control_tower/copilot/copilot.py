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

class ResolutionCopilot:
    """Phase 1: classify → investigate → recommend. A human approves every action."""

    def __init__(self):
        # In-memory ledger now; a database in production.
        self.feedback_log: list[dict] = []


    @traceable(name="recommend_resolution", run_type="chain")
    def recommend(self, ticket_id: str, order_id: str, message: str) -> CopilotResult:
        try:
            classification = classify_chain.invoke({"message": message})

            context = retrieve_context(order_id)
            policies = retrieve_policies(classification.issue_type)

            recommendation = resolve_chain.invoke(
                {
                    "issue_type": classification.issue_type,
                    "urgency": classification.urgency,
                    "context": context,
                    "policies": policies,
                    "message": message,
                }
            )

            return CopilotResult(
                ticket_id=ticket_id,
                classification=classification,
                recommendation=recommendation,
                requires_human_approval=True,   # Phase 1: always
                gate_reason=evaluate_gate(context, recommendation),
            )
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