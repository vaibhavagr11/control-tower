"""
Generate a realistic, ENTERPRISE-LENGTH NorthStar Commerce policy corpus.

Each of 25 policies is rendered as a full multi-section manual (varied 3-20 pages
via length tiers), wrapping its specific rules in realistic enterprise structure:
purpose/scope, definitions, detailed rules, worked examples, exceptions,
escalation matrix, FAQ, related policies, revision history.

Long docs => many child chunks per parent => Parent Document Retriever, chunking,
compression, and reranking all get a real test. Specific rule codes / exact tokens
(POL-CX-###, ERR-PAY-002, CLR-) are preserved for keyword/hybrid testing.

Run:  uv run python scripts/generate_policies.py
"""

import json
import random
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

random.seed(42)
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "policies"

S = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=S["Title"], fontSize=18, spaceAfter=4)
SUB = ParagraphStyle("SUB", parent=S["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=14)
H2 = ParagraphStyle("H2", parent=S["Heading2"], fontSize=13, spaceBefore=12, spaceAfter=4)
H3 = ParagraphStyle("H3", parent=S["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=2)
BODY = ParagraphStyle("BODY", parent=S["Normal"], fontSize=10.5, leading=15, spaceAfter=7)

# Length tiers -> (num worked examples, num FAQ entries)
TIERS = {"small": (4, 4), "medium": (14, 10), "large": (95, 40)}

# (doc_id, title, type, version, status, tier, [ (heading, body | ("TABLE", rows)) ])
POLICIES = [
    ("POL-CX-001", "Refund & Replacement Policy", "refund", "1.0", "active", "large", [
        ("REFUND-LOWVAL — Low-Value Delivered-Not-Received",
         "Orders under $100 marked delivered by the carrier but reported as not received may be refunded or replaced automatically when the customer has a clean claim history. No manager approval is required."),
        ("REPLACE-PREFERRED — Replacement Preferred Over Refund",
         "For delivered-not-received claims on items under $150, a replacement order is preferred over a cash refund to preserve revenue. Offer a refund only if the item is out of stock or the customer explicitly requests one."),
    ]),
    ("POL-CX-002", "Shipping Delay & Compensation Policy", "delay", "1.0", "active", "medium", [
        ("DELAY-COMP — Carrier Delay Goodwill",
         "When a shipment is delayed beyond 7 days at the carrier, proactively send a status update and offer goodwill store credit. Do not refund a delay unless the customer requests cancellation."),
        ("Goodwill Credit Schedule",
         ("TABLE", [["Delay Window", "Goodwill Store Credit"], ["7 to 14 days", "$10"], ["15 to 21 days", "$20"], ["22+ days", "$30 or cancellation"]])),
    ]),
    ("POL-CX-003", "Fraud Review Policy", "fraud", "1.0", "active", "large", [
        ("FRAUD-REVIEW — Mandatory Human Escalation",
         "Escalate to a human for fraud review before any refund or replacement when: order value is above $150; the customer has 3 or more prior refund claims; or the account is younger than 30 days."),
        ("Review Procedure",
         "Verify delivery details and signature data, compare shipping address against account history, and check payment and chargeback signals. Record every outcome for pattern analysis."),
    ]),
    ("POL-CX-004", "Returns & Exchanges Policy", "returns", "2.1", "active", "large", [
        ("RETURN-WINDOW — Standard Return Window",
         "Most items may be returned within 30 days of delivery in original condition. Final-sale and clearance items (SKU prefix CLR-) are not returnable."),
        ("EXCHANGE-FLOW — Size and Color Exchanges",
         "Exchanges ship once the original return is scanned by the carrier. Price differences are charged or refunded to the original payment method."),
    ]),
    ("POL-CX-005", "Damaged & Defective Items Policy", "damaged", "1.3", "active", "medium", [
        ("DAMAGE-CLAIM — Reporting Window",
         "Damaged or defective items must be reported within 14 days with photos. Approved claims receive a replacement or full refund including original shipping."),
        ("NO-RETURN-LOWVAL", "For damaged items under $25, no physical return is required; dispose locally."),
    ]),
    ("POL-CX-006", "Wrong Item Received Policy", "wrong_item", "1.0", "active", "small", [
        ("WRONG-ITEM — Fulfillment Error",
         "If the customer received the wrong SKU, send the correct item immediately at no cost and generate a prepaid return label for the incorrect item."),
    ]),
    ("POL-CX-007", "Missing Parts & Accessories Policy", "missing_parts", "1.0", "active", "small", [
        ("MISSING-PARTS — Partial Shipment",
         "For missing components, ship the missing part rather than replacing the whole order. Whole-order replacement requires supervisor approval."),
    ]),
    ("POL-CX-008", "Warranty Coverage Policy", "warranty", "3.0", "active", "large", [
        ("WARRANTY-STD — Standard Coverage",
         "Electronics carry a 12-month limited warranty from delivery covering manufacturing defects, not accidental damage."),
        ("WARRANTY-CLAIM — Claim Process",
         "Warranty claims require proof of purchase and a defect description. Out-of-warranty repairs are quoted before work begins."),
    ]),
    ("POL-CX-009", "Payment Failure & Declines Policy", "payment", "1.2", "active", "medium", [
        ("PAY-DECLINE — Failed Authorization",
         "On a declined payment (error ERR-PAY-002), the order is held 48 hours for re-authorization before automatic cancellation. Advise the customer to verify card details and billing address."),
    ]),
    ("POL-CX-010", "Chargeback Handling Policy", "payment", "1.1", "active", "medium", [
        ("CHARGEBACK — Dispute Response",
         "On a chargeback, freeze related refunds and submit delivery evidence within the processor SLA. Repeat chargeback accounts are flagged for fraud review under FRAUD-REVIEW."),
    ]),
    ("POL-CX-011", "Subscription Billing Policy", "subscription", "1.0", "active", "medium", [
        ("SUB-BILL — Renewal Charges",
         "Subscriptions renew automatically on the billing date. A failed renewal retries for 5 days (error ERR-PAY-002) before the subscription is paused."),
    ]),
    ("POL-CX-012", "Subscription Cancellation Policy", "subscription", "1.0", "active", "small", [
        ("SUB-CANCEL — Cancellation & Proration",
         "Customers may cancel anytime; access continues to the period end. Annual plans cancelled within 14 days are eligible for a prorated refund."),
    ]),
    ("POL-CX-013", "Order Cancellation Policy", "cancellation", "1.0", "active", "small", [
        ("ORDER-CANCEL — Pre-Shipment Window",
         "Orders can be cancelled for a full refund before they enter fulfillment. Once shipped, treat as a return under RETURN-WINDOW."),
    ]),
    ("POL-CX-014", "Price Match Policy", "price_match", "1.0", "active", "medium", [
        ("PRICE-MATCH — Competitor Matching",
         "Match a lower advertised price from an approved competitor within 7 days of purchase. Marketplace third-party sellers and clearance (CLR-) are excluded."),
    ]),
    ("POL-CX-015", "Promotional Code & Discount Policy", "promotions", "1.4", "active", "medium", [
        ("PROMO-STACK — Code Stacking Rules",
         "Only one promotional code applies per order unless explicitly marked stackable. Expired or invalid codes return error ERR-PROMO-014."),
    ]),
    ("POL-CX-016", "Gift Card Policy", "gift_card", "1.0", "active", "small", [
        ("GIFTCARD — Issuance & Redemption",
         "Gift cards do not expire and are non-refundable for cash. A lost card is replaced only with proof of purchase."),
    ]),
    ("POL-CX-017", "Loyalty Points Policy", "loyalty", "2.0", "active", "medium", [
        ("LOYALTY-EARN — Points Accrual",
         "Members earn 1 point per dollar; points post after the return window closes. Points have no cash value and expire after 18 months of inactivity."),
    ]),
    ("POL-CX-018", "International Shipping Policy", "international", "1.1", "active", "large", [
        ("INTL-SHIP — Eligible Destinations",
         "International orders ship to supported countries only. Delivery estimates exclude customs processing time."),
    ]),
    ("POL-CX-019", "Customs & Duties Policy", "international", "1.0", "active", "medium", [
        ("DUTIES — Customer Responsibility",
         "Import duties and taxes are the customer's responsibility and are non-refundable on returns. Refused international parcels are refunded less shipping and duties."),
    ]),
    ("POL-CX-020", "Address Change & Reshipment Policy", "shipping", "1.0", "active", "small", [
        ("ADDRESS-CHANGE — Pre-Shipment Edits",
         "Address changes are allowed before shipment. After shipment, a reship requires return-to-sender confirmation and may incur a reshipping fee."),
    ]),
    ("POL-CX-021", "Lost in Transit Policy", "delivery", "1.0", "active", "medium", [
        ("LOST-TRANSIT — No Movement",
         "If tracking shows no movement for 10 days, treat the parcel as lost: reship the item or refund, and open a carrier investigation."),
    ]),
    ("POL-CX-022", "Delivered Not Received Policy", "delivery", "1.0", "active", "large", [
        ("DNR-INVESTIGATE — Porch & Carrier Checks",
         "For delivered-not-received reports, ask the customer to check with neighbors and confirm the address. Low-value clean-history claims resolve under REFUND-LOWVAL; high-risk claims go to FRAUD-REVIEW."),
    ]),
    ("POL-CX-023", "B2B & Bulk Order Policy", "b2b", "1.0", "active", "medium", [
        ("B2B-TERMS — Bulk Orders",
         "Bulk orders over 50 units require a purchase order and may carry net-30 terms. Returns on custom bulk orders are not accepted."),
    ]),
    ("POL-CX-024", "Holiday & Peak Season Policy", "seasonal", "1.0", "active", "small", [
        ("PEAK-RETURNS — Extended Window",
         "Items purchased Nov 1 to Dec 24 may be returned through Jan 31. Peak-season carrier delays under 5 days are not eligible for DELAY-COMP."),
    ]),
    ("POL-CX-025", "Legacy Refund Policy (Superseded)", "refund", "0.9", "deprecated", "small", [
        ("LEGACY-REFUND — Superseded",
         "This policy is superseded by POL-CX-001. Retained for audit only; do not apply to new claims."),
    ]),
]

GLOSSARY = [
    ("Claim", "A customer-reported issue requiring a resolution decision."),
    ("Resolution", "The action taken to close a claim: refund, replacement, credit, or escalation."),
    ("Clean claim history", "An account with no prior refund abuse flags in the trailing 12 months."),
    ("Goodwill credit", "Discretionary store credit issued to preserve customer satisfaction."),
    ("Escalation", "Routing a claim to a human agent or specialist team for review."),
    ("SLA", "Service-level agreement defining the maximum time to act on a claim."),
    ("Carrier signal", "Tracking event reported by the shipping carrier (e.g., delivered, in transit)."),
]
CHANNELS = ["web", "mobile app", "phone", "email", "partner marketplace"]
SEGMENTS = ["first-time buyer", "loyalty member", "high-value account", "new account", "B2B account"]


def _para(text):
    return Paragraph(text, BODY)


def purpose(title, ptype):
    return (f"This {title} ('the Policy') governs how NorthStar Commerce Customer Operations identifies, "
            f"investigates, and resolves {ptype}-related situations across all sales channels "
            f"({', '.join(CHANNELS)}). It applies to all consumer and small-business orders fulfilled through "
            f"NorthStar distribution centers and approved third-party carriers. The Policy is binding on all "
            f"customer-operations agents, team leads, quality reviewers, and automated resolution systems. Any "
            f"deviation requires documented approval from the CX Policy Team and is logged for audit. The Policy "
            f"is reviewed quarterly and supersedes any prior guidance on the same subject matter.")


def example(i, doc_id, ptype, codes):
    seg = random.choice(SEGMENTS)
    ch = random.choice(CHANNELS)
    code = random.choice(codes) if codes else doc_id
    val = random.choice([29, 49, 89, 119, 175, 240, 410])
    days = random.choice([2, 5, 8, 11, 16, 23])
    return (f"<b>Example {i}.</b> A {seg} contacts support via {ch} regarding a {ptype} issue on an order valued "
            f"at ${val}, {days} days after the order date. The agent confirms the account standing, reviews the "
            f"carrier signal, and applies rule {code} from this Policy. If the conditions in {code} are met, the "
            f"agent resolves in the customer's favor and records the outcome; otherwise the case is routed per the "
            f"escalation matrix below. Document {doc_id} reference {code}-{i:03d} is attached to the case for audit.")


def faq(i, ptype, codes):
    code = random.choice(codes) if codes else "the applicable rule"
    qs = [
        (f"Does this {ptype} policy apply to clearance (CLR-) items?",
         "Clearance and final-sale items follow the exclusions stated in the Detailed Rules; agents should confirm the SKU prefix before acting."),
        (f"What if the customer disputes the {ptype} outcome?",
         f"Re-review the case against {code}. If the customer remains dissatisfied, escalate per the matrix; do not exceed the goodwill caps without approval."),
        (f"How is this logged?",
         "Every decision is recorded in the case management system with the rule code applied and the agent identifier, for quality and pattern analysis."),
        (f"Can automated systems apply this {ptype} policy?",
         "Automated resolution may apply this Policy only within the confidence and value thresholds defined in the governing risk policy; otherwise a human approves."),
    ]
    q, a = qs[i % len(qs)]
    return f"<b>Q{i}. {q}</b><br/>{a}"


def build_pdf(doc_id, title, ptype, version, status, tier, core):
    n_ex, n_faq = TIERS[tier]
    codes = [h.split(" — ")[0] for h, b in core if " — " in h] or [doc_id]
    fname = f"{doc_id}_{title.split(' (')[0].replace(' ', '_').replace('&', 'and')}.pdf"
    path = OUT_DIR / fname
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, topMargin=0.9 * inch,
                            bottomMargin=0.9 * inch, leftMargin=1 * inch, rightMargin=1 * inch)
    st = [Paragraph(title, H1),
          Paragraph(f"NorthStar Commerce — Customer Operations &nbsp;|&nbsp; {doc_id} &nbsp;|&nbsp; "
                    f"type={ptype} &nbsp;|&nbsp; v{version} &nbsp;|&nbsp; status={status}", SUB)]

    st += [Paragraph("1. Purpose & Scope", H2), _para(purpose(title, ptype))]

    st += [Paragraph("2. Definitions", H2)]
    for term, d in GLOSSARY:
        st.append(_para(f"<b>{term}.</b> {d}"))

    st += [Paragraph("3. Detailed Rules", H2)]
    for heading, body in core:
        st.append(Paragraph(heading, H3))
        if isinstance(body, tuple) and body[0] == "TABLE":
            t = Table(body[1], colWidths=[2.6 * inch, 3.2 * inch])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f3e4e")),
                                   ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                                   ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc"))]))
            st += [t, Spacer(1, 8)]
        else:
            st.append(_para(body))

    st += [Paragraph("4. Procedures", H2),
           _para(f"Agents follow these steps for {ptype} claims: (1) verify the customer's identity and account "
                 f"standing; (2) retrieve the order and carrier signal; (3) confirm the claim against the Detailed "
                 f"Rules above; (4) check the Exceptions section; (5) apply the resolution or escalate; (6) record "
                 f"the rule code and outcome. Steps must be completed within the SLA defined for this policy type.")]

    st += [Paragraph("5. Worked Examples", H2)]
    for i in range(1, n_ex + 1):
        st.append(_para(example(i, doc_id, ptype, codes)))

    st += [Paragraph("6. Exceptions & Edge Cases", H2)]
    for ex in [
        "Orders flagged by the fraud system are always escalated regardless of value.",
        "Clearance (CLR-) and final-sale items are excluded from standard resolutions.",
        "International orders are additionally subject to the Customs & Duties Policy (POL-CX-019).",
        "Repeated claims from the same account within 30 days trigger a manual review.",
        "Gift-card-funded orders are refunded to store credit, not the original tender.",
    ]:
        st.append(_para(f"• {ex}"))

    st += [Paragraph("7. Escalation Matrix", H2)]
    em = [["Condition", "Route To", "SLA"],
          ["Within thresholds, high confidence", "Auto / Agent resolve", "Immediate"],
          ["Value over $150", "Team Lead", "4 hours"],
          ["Fraud signals present", "Fraud Review (POL-CX-003)", "24 hours"],
          ["Customer dispute after resolution", "Senior Agent", "1 business day"]]
    t = Table(em, colWidths=[2.7 * inch, 1.9 * inch, 1.2 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f3e4e")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc"))]))
    st += [t, Spacer(1, 8)]

    st += [Paragraph("8. Frequently Asked Questions", H2)]
    for i in range(1, n_faq + 1):
        st.append(_para(faq(i, ptype, codes)))

    st += [Paragraph("9. Related Policies", H2),
           _para("This Policy operates alongside the Refund & Replacement Policy (POL-CX-001), the Fraud Review "
                 "Policy (POL-CX-003), the Returns & Exchanges Policy (POL-CX-004), and the Shipping Delay & "
                 "Compensation Policy (POL-CX-002). Where guidance conflicts, the more specific policy governs.")]

    st += [Paragraph("10. Revision History", H2)]
    rh = [["Version", "Date", "Summary"],
          ["0.9", "2024-03-01", "Initial draft"],
          ["1.0", "2025-01-15", "First approved release"],
          [version, "2026-01-01", "Current effective version"]]
    t = Table(rh, colWidths=[1.0 * inch, 1.3 * inch, 3.5 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f3e4e")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc"))]))
    st.append(t)

    doc.build(st)
    return fname


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for doc_id, title, ptype, version, status, tier, core in POLICIES:
        fname = build_pdf(doc_id, title, ptype, version, status, tier, core)
        catalog[fname] = {"doc_id": doc_id, "policy_type": ptype, "version": version,
                          "status": status, "title": title, "tier": tier}
    (OUT_DIR / "catalog.json").write_text(json.dumps(catalog, indent=2))
    print(f"Generated {len(catalog)} enterprise-length policy PDFs + catalog.json in {OUT_DIR}")


if __name__ == "__main__":
    main()
