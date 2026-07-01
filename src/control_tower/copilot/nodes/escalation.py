from control_tower.copilot.state import CopilotState


def escalation_node(state: CopilotState) -> dict:
    """Fast-path for tickets that need specialist handling.

    Deterministic template message — not LLM-generated, so tone and content
    never leak internal fraud or risk reasoning to the customer.

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