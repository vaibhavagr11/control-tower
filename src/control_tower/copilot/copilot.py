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

class ResolutionCopilot:
    """Phase 1: classify → investigate → recommend. A human approves every action."""

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