"""Phase 1 demo: the Resolution Copilot recommends, a human approves."""

from control_tower.copilot.copilot import ResolutionCopilot, _apply_window, CONVERSATION_WINDOW_SIZE
from control_tower.schemas import CopilotResult


def _print_result(r: CopilotResult) -> None:
    c, rec = r.classification, r.recommendation
    print(f"Ticket {r.ticket_id}")
    print(f"  Classified : {c.issue_type} (urgency: {c.urgency})")
    print(f"  Recommends : {rec.recommended_action}  [confidence: {rec.confidence}, fraud: {rec.fraud_risk}]")
    print(f"  Policy     : {', '.join(rec.policy_citations) or '(none)'}")
    print(f"  Cost est.  : ${rec.estimated_cost_usd:.2f}")
    print(f"  Gate       : {r.gate_reason}")
    print(f"  Draft      : {rec.customer_message_draft}")


def main() -> None:
    bot = ResolutionCopilot()

    tickets = [
        {"ticket_id": "T-1", "order_id": "ORD-5001",
         "message": "My package says delivered, but I never received it."},
        {"ticket_id": "T-2", "order_id": "ORD-5002",
         "message": "Tracking shows delivered but the monitor isn't here. I want a refund."},
        {"ticket_id": "T-3", "order_id": "ORD-5003",
         "message": "My keyboard is super late, it's been 9 days. What's going on?"},
        # Edge case: unknown order → should degrade gracefully and escalate.
        {"ticket_id": "T-X", "order_id": "ORD-DOES-NOT-EXIST",
         "message": "Where is my stuff??"},
    ]

    print("=" * 64)
    print("RESOLUTION COPILOT — PHASE 1 DEMO (recommend, don't act)")
    print("=" * 64)

    results = []
    for t in tickets:
        r = bot.recommend(**t)
        results.append(r)
        print("-" * 64)
        _print_result(r)

    # Multi-turn memory sanity check — same ticket_id as T-1, sent as a follow-up.
    print("\n" + "-" * 64)
    print("MULTI-TURN MEMORY CHECK (follow-up on T-1)")
    r_followup = bot.recommend(
        ticket_id="T-1", order_id="ORD-5001",
        message="Actually never mind, I just found it — my neighbor had it.",
    )
    _print_result(r_followup)

    print("\nStored history for T-1:")
    for m in bot.conversation_history["T-1"]:
        print(f"  [{m.type}] {m.content}")

    # Simulate a human agent reviewing the queue.
    print("\n" + "-" * 64)
    print("HUMAN-IN-THE-LOOP: agent decisions")
    bot.record_decision(results[0], "accept")
    bot.record_decision(results[1], "accept")
    bot.record_decision(results[2], "edit", agent_action="offer_compensation", note="added store credit")
    print(f"  decisions logged: {len(bot.feedback_log)} | acceptance rate: {bot.accuracy()}")

    # Multi-session memory check: simulate a customer with a recent track record
    # of repeat delivery-not-received claims, then see if a new ticket reflects it.
    print("\n" + "-" * 64)
    print("MULTI-SESSION MEMORY CHECK (repeat-claim pattern for C-100)")
    bot.customer_memory["C-100"] = [
        {"ticket_id": "T-90", "issue_type": "delivery_not_received",
         "recommended_action": "send_replacement", "gate_reason": "model confidence is 'medium'"},
        {"ticket_id": "T-91", "issue_type": "delivery_not_received",
         "recommended_action": "issue_refund", "gate_reason": "model confidence is 'medium'"},
    ]
    r_repeat = bot.recommend(
        ticket_id="T-92", order_id="ORD-5001",
        message="My order never arrived again, please refund me.",
    )
    _print_result(r_repeat)

    # Windowed memory check: push T-1's history past the cap and confirm
    # the model only ever sees the most recent messages, even though the
    # full history keeps growing in storage.
    print("\n" + "-" * 64)
    print("WINDOWED MEMORY CHECK (push T-1 past the window cap)")
    bot.recommend(ticket_id="T-1", order_id="ORD-5001",
                  message="Wait, actually it's missing after all, sorry for the confusion.")
    bot.recommend(ticket_id="T-1", order_id="ORD-5001",
                  message="Can you just send a replacement instead of a refund?")

    full_history = bot.conversation_history["T-1"]
    windowed = _apply_window(full_history)
    print(f"  Full stored history : {len(full_history)} messages")
    print(f"  Windowed view       : {len(windowed)} messages (cap = {CONVERSATION_WINDOW_SIZE})")
    print("  Windowed messages sent to the model:")
    for m in windowed:
        print(f"    [{m.type}] {m.content}")

    print("\n" + "=" * 64)
    print("Phase 1 Complete.")
    print("=" * 64)


if __name__ == "__main__":
    main()