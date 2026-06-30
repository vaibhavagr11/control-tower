from langsmith import traceable
from control_tower.copilot import storage
from control_tower.copilot.chains import summarize_chain
from control_tower.copilot.graph import recommend_graph
from control_tower.datalayer.mock_store import retrieve_context
from control_tower.schemas import (
    CopilotResult,
    IssueClassification,
    ResolutionRecommendation,
)
from typing import Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, trim_messages, SystemMessage

CONVERSATION_WINDOW_SIZE = 6    # keep the last 6 messages (~3 user/AI turn pairs)

def _apply_window(history: list[BaseMessage]) -> list[BaseMessage]:
    """Cap how much chat history reaches the model — keep only the most recent turns."""
    return trim_messages(
        history,
        strategy= "last",
        token_counter=len,
        max_tokens=CONVERSATION_WINDOW_SIZE,
        start_on="human",
    )

def _split_window(history: list[BaseMessage]) -> tuple[list[BaseMessage], list[BaseMessage]]:
    """Split history into (overflow, windowed) — what ages out vs. what the model sees raw."""
    windowed = _apply_window(history)
    overflow = history[: len(history) - len(windowed)]
    return overflow, windowed

def _summarize_overflow(overflow: list[BaseMessage]) -> str:
    """Condense the messages that fell out of the window into a short blurb."""
    conversation_text = "\n".join(f"{m.type}: {m.content}" for m in overflow)
    summary = summarize_chain.invoke({"conversation": conversation_text})
    return summary.content

def _build_history_for_model(history: list[BaseMessage]) -> list[BaseMessage]:
    """What actually reaches the model: a short summary of older turns (if any) + the recent window, raw."""
    overflow, windowed = _split_window(history)
    if not overflow:
        return windowed
    summary_text = _summarize_overflow(overflow)
    return [SystemMessage(content=f"Summary of earlier conversation: {summary_text}")] + windowed
class ResolutionCopilot:
    """Phase 1: classify → investigate → recommend. A human approves every action."""

    def __init__(self):
        storage._init_db()
        # Hydrate from disk so a restart doesn't wipe out what the copilot has learned.
        self.feedback_log: list[dict] = storage.load_feedback_log()
        self.conversation_history: dict[str, list[BaseMessage]] = storage.load_conversation_history()
        self.customer_memory: dict[str, list[dict]] = storage.load_customer_memory()


    @traceable(name="recommend_resolution", run_type="chain")
    def recommend(self, ticket_id: str, order_id: str, message: str) -> CopilotResult:
        history = self.conversation_history.get(ticket_id, [])
        windowed_history = _build_history_for_model(history)

        # Look up which customer this order belongs to, then pull their past-ticket history.
        customer_id = retrieve_context(order_id).get("order", {}).get("customer_id")
        customer_history = self.customer_memory.get(customer_id, []) if customer_id else []

        try:
            state = recommend_graph.invoke({
                "order_id": order_id, 
                "message": message, 
                "chat_history": windowed_history, 
                "customer_history": customer_history,
                "retry_count": 0,
                "clarification_count": 0,
                "action_result": {},
                "clarification_question": "",
            })
            return_result = CopilotResult(
                ticket_id=ticket_id,
                classification=state["classification"],
                recommendation=state["recommendation"],
                requires_human_approval=True,   # Phase 1: always
                gate_reason=state["gate_reason"],
                customer_message=state["customer_message"],
            )

            history.append(HumanMessage(content= message))
            history.append(AIMessage(content= return_result.customer_message))
            self.conversation_history[ticket_id] = history
            storage.save_message(ticket_id, "human", message)
            storage.save_message(ticket_id, "ai", return_result.customer_message)

            if customer_id:
                customer_entry = {
                    "ticket_id": ticket_id,
                    "issue_type": return_result.classification.issue_type,
                    "recommended_action": return_result.recommendation.recommended_action,
                    "gate_reason": return_result.gate_reason,
                }
                self.customer_memory.setdefault(customer_id, []).append(customer_entry)
                storage.save_customer_entry(customer_id, customer_entry)

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
        storage.save_feedback_entry(entry)
        return entry
    
    def accuracy(self) -> Optional[float]:
        """Acceptance rate so far — the gate metric for progressing to Phase 2."""
        if not self.feedback_log:
            return None
        accepted = sum(1 for e in self.feedback_log if e["matched"])
        return round(accepted / len(self.feedback_log), 3)