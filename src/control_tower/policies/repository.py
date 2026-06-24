POLICIES = {
    "REFUND-LOWVAL": "Orders under $100 marked 'delivered' but reported not received may be "
                     "refunded or replaced automatically when the customer has a clean claim history.",
    "REPLACE-PREFERRED": "For 'delivered not received' on items under $150, a replacement is "
                         "preferred over a refund to preserve revenue.",
    "FRAUD-REVIEW": "Orders over $150, OR customers with 3+ prior refund claims, OR accounts younger "
                    "than 30 days must be escalated to a human for fraud review before any refund.",
    "DELAY-COMP": "For carrier delays beyond 7 days, offer goodwill store credit and a proactive "
                  "status update; do not refund unless the customer requests cancellation.",
}


def retrieve_policies(issue_type: str) -> dict:
    """Return the policy rules relevant to a given issue type."""
    relevant = {
        "delivery_not_received": ["REFUND-LOWVAL", "REPLACE-PREFERRED", "FRAUD-REVIEW"],
        "delivery_delayed":      ["DELAY-COMP", "FRAUD-REVIEW"],
        "refund_request":        ["REFUND-LOWVAL", "FRAUD-REVIEW"],
    }.get(issue_type, ["FRAUD-REVIEW"])
    return {rule_id: POLICIES[rule_id] for rule_id in relevant if rule_id in POLICIES}