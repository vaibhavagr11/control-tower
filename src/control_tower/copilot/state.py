from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage
from control_tower.schemas import IssueClassification, ResolutionRecommendation


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
    action_result: dict          # {"success": bool, "reason": str, ...}
    retry_count: int             # action retry counter, max 3
    clarification_count: int     # clarification loop counter, max 2
    clarification_question: str  # what we asked the customer