from pydantic import BaseModel, Field
from typing import List, Literal

class IssueClassification(BaseModel):
    issue_type: Literal[
        "delivery_not_received", "delivery_delayed", "damaged_item",
        "wrong_item", "refund_request", "payment_problem", "other",
    ] = Field(description="The single best-fit category for the customer's issue.")
    urgency: Literal[
        "low", "medium", "high"
    ] = Field(description="Defines how urgently the issue needs to be resolved.")
    reasoning: str = Field(
        description="Brief explanation for the chosen issue_type and urgency."
        )


class ResolutionRecommendation(BaseModel):
    recommended_action: Literal[
        "issue_refund", "send_replacement", "generate_return_label",
        "offer_compensation", "escalate_to_human", "request_more_info",
    ] = Field(description="The single best-fit action to take for the customer's issue.")
    rationale: str = Field(
        description="Brief explanation for the chosen recommended_action."
        )
    confidence: Literal[
        "high", "medium", "low"
    ] = Field(description="Defines how confident we are about the recommended_action.")
    policy_citations: List[str] = Field(
        default_factory=list, 
        description="IDs of the policy rules supporting this recommendation."
        )
    fraud_risk: Literal["low", "medium", "high"] = Field(
        default="low", 
        description="Probability of this issue being a fraud."
        )
    estimated_cost_usd: float = Field(
        default=0.0, 
        description="What would be the estimated cost in USD for the recommended action."
        )
    
class CopilotResult(BaseModel):
    ticket_id: str
    classification: IssueClassification
    recommendation: ResolutionRecommendation
    customer_message: str
    requires_human_approval: bool
    gate_reason: str