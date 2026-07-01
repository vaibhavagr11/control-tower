from control_tower.copilot.chains import clarification_chain, simulate_response_chain
from control_tower.copilot.state import CopilotState

MAX_CLARIFICATIONS = 2


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
    In production this node pauses and waits for the real customer reply."""
    response = simulate_response_chain.invoke({
        "original_message": state["message"],
        "clarification_question": state["clarification_question"],
    })
    augmented_message = (
        f"{state['message']}\n"
        f"[Customer follow-up]: {response.content}"
    )
    return {"message": augmented_message}