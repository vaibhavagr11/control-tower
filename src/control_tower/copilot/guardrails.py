from control_tower.config import HIGH_VALUE_THRESHOLD_USD
from control_tower.schemas import ResolutionRecommendation


def evaluate_gate(context: dict, rec: ResolutionRecommendation) -> str:
    """Return the reason a human must approve this recommendation.

    Phase 1 ALWAYS requires approval; this explains *why* it would gate,
    which is exactly the logic Phase 2 will use to grant scoped autonomy.
    """
    order = context.get("order", {})
    customer = context.get("customer", {})
    reasons = []

    if order.get("value_usd", 0) > HIGH_VALUE_THRESHOLD_USD:
        reasons.append(f"order value ${order.get('value_usd')} exceeds ${HIGH_VALUE_THRESHOLD_USD}")
    if customer.get("prior_refund_claims", 0) >= 3:
        reasons.append("customer has 3+ prior refund claims")
    if customer.get("account_age_days", 9999) < 30:
        reasons.append("account younger than 30 days")
    if rec.confidence != "high":
        reasons.append(f"model confidence is '{rec.confidence}'")
    if rec.fraud_risk != "low":
        reasons.append(f"fraud risk is '{rec.fraud_risk}'")

    return "; ".join(reasons) if reasons else "Phase 1 policy: all actions require approval"