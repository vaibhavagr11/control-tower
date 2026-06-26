"""
Generate a realistic, larger NorthStar Commerce policy corpus for RAG testing.

Produces ~25 multi-section policy PDFs in data/policies/ plus a catalog.json
manifest (filename -> metadata). Deliberately includes:
  - overlapping topics (e.g. "delivered not received" appears in refund, fraud,
    and a dedicated delivery policy) so retrieval gets genuinely ambiguous
  - exact-match tokens (rule IDs, SKUs, error codes) that favor keyword search,
    so hybrid (BM25 + dense) becomes measurable

Run:  uv run python scripts/generate_policies.py
"""

import json
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "policies"

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=17, spaceAfter=4)
SUB = ParagraphStyle("SUB", parent=styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=12)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=3)
BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontSize=10.5, leading=15, spaceAfter=7)

# Each policy: doc_id, title, policy_type, version, status, [ (heading, body|("TABLE", rows)) ]
POLICIES = [
    ("POL-CX-001", "Refund & Replacement Policy", "refund", "1.0", "active", [
        ("REFUND-LOWVAL — Low-Value Delivered-Not-Received",
         "Orders under $100 marked delivered by the carrier but reported as not received may be refunded or replaced automatically when the customer has a clean claim history. No manager approval is required."),
        ("REPLACE-PREFERRED — Replacement Preferred Over Refund",
         "For delivered-not-received claims on items under $150, a replacement order is preferred over a cash refund to preserve revenue. Offer a refund only if the item is out of stock or the customer explicitly requests one."),
    ]),
    ("POL-CX-002", "Shipping Delay & Compensation Policy", "delay", "1.0", "active", [
        ("DELAY-COMP — Carrier Delay Goodwill",
         "When a shipment is delayed beyond 7 days at the carrier, proactively send a status update and offer goodwill store credit. Do not refund a delay unless the customer requests cancellation."),
        ("Goodwill Credit Schedule",
         ("TABLE", [["Delay Window", "Goodwill Store Credit"], ["7 to 14 days", "$10"], ["15 to 21 days", "$20"], ["22+ days", "$30 or cancellation"]])),
    ]),
    ("POL-CX-003", "Fraud Review Policy", "fraud", "1.0", "active", [
        ("FRAUD-REVIEW — Mandatory Human Escalation",
         "Escalate to a human for fraud review before any refund or replacement when: order value is above $150; the customer has 3 or more prior refund claims; or the account is younger than 30 days."),
        ("Review Procedure",
         "Verify delivery details and signature data, compare shipping address against account history, and check payment and chargeback signals. Record every outcome for pattern analysis."),
    ]),
    ("POL-CX-004", "Returns & Exchanges Policy", "returns", "2.1", "active", [
        ("RETURN-WINDOW — Standard Return Window",
         "Most items may be returned within 30 days of delivery in original condition. Final-sale and clearance items (SKU prefix CLR-) are not returnable."),
        ("EXCHANGE-FLOW — Size and Color Exchanges",
         "Exchanges ship once the original return is scanned by the carrier. Price differences are charged or refunded to the original payment method."),
    ]),
    ("POL-CX-005", "Damaged & Defective Items Policy", "damaged", "1.3", "active", [
        ("DAMAGE-CLAIM — Reporting Window",
         "Damaged or defective items must be reported within 14 days with photos. Approved claims receive a replacement or full refund including original shipping."),
        ("NO-RETURN-LOWVAL", "For damaged items under $25, no physical return is required; dispose locally."),
    ]),
    ("POL-CX-006", "Wrong Item Received Policy", "wrong_item", "1.0", "active", [
        ("WRONG-ITEM — Fulfillment Error",
         "If the customer received the wrong SKU, send the correct item immediately at no cost and generate a prepaid return label for the incorrect item."),
    ]),
    ("POL-CX-007", "Missing Parts & Accessories Policy", "missing_parts", "1.0", "active", [
        ("MISSING-PARTS — Partial Shipment",
         "For missing components, ship the missing part rather than replacing the whole order. Whole-order replacement requires supervisor approval."),
    ]),
    ("POL-CX-008", "Warranty Coverage Policy", "warranty", "3.0", "active", [
        ("WARRANTY-STD — Standard Coverage",
         "Electronics carry a 12-month limited warranty from delivery covering manufacturing defects, not accidental damage."),
        ("WARRANTY-CLAIM — Claim Process",
         "Warranty claims require proof of purchase and a defect description. Out-of-warranty repairs are quoted before work begins."),
    ]),
    ("POL-CX-009", "Payment Failure & Declines Policy", "payment", "1.2", "active", [
        ("PAY-DECLINE — Failed Authorization",
         "On a declined payment (error ERR-PAY-002), the order is held 48 hours for re-authorization before automatic cancellation. Advise the customer to verify card details and billing address."),
    ]),
    ("POL-CX-010", "Chargeback Handling Policy", "payment", "1.1", "active", [
        ("CHARGEBACK — Dispute Response",
         "On a chargeback, freeze related refunds and submit delivery evidence within the processor SLA. Repeat chargeback accounts are flagged for fraud review under FRAUD-REVIEW."),
    ]),
    ("POL-CX-011", "Subscription Billing Policy", "subscription", "1.0", "active", [
        ("SUB-BILL — Renewal Charges",
         "Subscriptions renew automatically on the billing date. A failed renewal retries for 5 days (error ERR-PAY-002) before the subscription is paused."),
    ]),
    ("POL-CX-012", "Subscription Cancellation Policy", "subscription", "1.0", "active", [
        ("SUB-CANCEL — Cancellation & Proration",
         "Customers may cancel anytime; access continues to the period end. Annual plans cancelled within 14 days are eligible for a prorated refund."),
    ]),
    ("POL-CX-013", "Order Cancellation Policy", "cancellation", "1.0", "active", [
        ("ORDER-CANCEL — Pre-Shipment Window",
         "Orders can be cancelled for a full refund before they enter fulfillment. Once shipped, treat as a return under RETURN-WINDOW."),
    ]),
    ("POL-CX-014", "Price Match Policy", "price_match", "1.0", "active", [
        ("PRICE-MATCH — Competitor Matching",
         "Match a lower advertised price from an approved competitor within 7 days of purchase. Marketplace third-party sellers and clearance (CLR-) are excluded."),
    ]),
    ("POL-CX-015", "Promotional Code & Discount Policy", "promotions", "1.4", "active", [
        ("PROMO-STACK — Code Stacking Rules",
         "Only one promotional code applies per order unless explicitly marked stackable. Expired or invalid codes return error ERR-PROMO-014."),
    ]),
    ("POL-CX-016", "Gift Card Policy", "gift_card", "1.0", "active", [
        ("GIFTCARD — Issuance & Redemption",
         "Gift cards do not expire and are non-refundable for cash. A lost card is replaced only with proof of purchase."),
    ]),
    ("POL-CX-017", "Loyalty Points Policy", "loyalty", "2.0", "active", [
        ("LOYALTY-EARN — Points Accrual",
         "Members earn 1 point per dollar; points post after the return window closes. Points have no cash value and expire after 18 months of inactivity."),
    ]),
    ("POL-CX-018", "International Shipping Policy", "international", "1.1", "active", [
        ("INTL-SHIP — Eligible Destinations",
         "International orders ship to supported countries only. Delivery estimates exclude customs processing time."),
    ]),
    ("POL-CX-019", "Customs & Duties Policy", "international", "1.0", "active", [
        ("DUTIES — Customer Responsibility",
         "Import duties and taxes are the customer's responsibility and are non-refundable on returns. Refused international parcels are refunded less shipping and duties."),
    ]),
    ("POL-CX-020", "Address Change & Reshipment Policy", "shipping", "1.0", "active", [
        ("ADDRESS-CHANGE — Pre-Shipment Edits",
         "Address changes are allowed before shipment. After shipment, a reship requires return-to-sender confirmation and may incur a reshipping fee."),
    ]),
    ("POL-CX-021", "Lost in Transit Policy", "delivery", "1.0", "active", [
        ("LOST-TRANSIT — No Movement",
         "If tracking shows no movement for 10 days, treat the parcel as lost: reship the item or refund, and open a carrier investigation."),
    ]),
    ("POL-CX-022", "Delivered Not Received Policy", "delivery", "1.0", "active", [
        ("DNR-INVESTIGATE — Porch & Carrier Checks",
         "For delivered-not-received reports, ask the customer to check with neighbors and confirm the address. Low-value clean-history claims resolve under REFUND-LOWVAL; high-risk claims go to FRAUD-REVIEW."),
    ]),
    ("POL-CX-023", "B2B & Bulk Order Policy", "b2b", "1.0", "active", [
        ("B2B-TERMS — Bulk Orders",
         "Bulk orders over 50 units require a purchase order and may carry net-30 terms. Returns on custom bulk orders are not accepted."),
    ]),
    ("POL-CX-024", "Holiday & Peak Season Policy", "seasonal", "1.0", "active", [
        ("PEAK-RETURNS — Extended Window",
         "Items purchased Nov 1 to Dec 24 may be returned through Jan 31. Peak-season carrier delays under 5 days are not eligible for DELAY-COMP."),
    ]),
    ("POL-CX-025", "Legacy Refund Policy (Superseded)", "refund", "0.9", "deprecated", [
        ("LEGACY-REFUND — Superseded",
         "This policy is superseded by POL-CX-001. Retained for audit only; do not apply to new claims."),
    ]),
]


def build_pdf(doc_id, title, ptype, version, status, sections):
    fname = f"{doc_id}_{title.split(' (')[0].replace(' ', '_').replace('&', 'and')}.pdf"
    path = OUT_DIR / fname
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, topMargin=0.9 * inch,
                            bottomMargin=0.9 * inch, leftMargin=1 * inch, rightMargin=1 * inch)
    story = [
        Paragraph(title, H1),
        Paragraph(f"NorthStar Commerce — Customer Operations &nbsp;|&nbsp; {doc_id} &nbsp;|&nbsp; "
                  f"type={ptype} &nbsp;|&nbsp; v{version} &nbsp;|&nbsp; status={status}", SUB),
    ]
    for heading, body in sections:
        story.append(Paragraph(heading, H2))
        if isinstance(body, tuple) and body[0] == "TABLE":
            t = Table(body[1], colWidths=[2.6 * inch, 3.2 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f3e4e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph(body, BODY))
    doc.build(story)
    return fname


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for doc_id, title, ptype, version, status, sections in POLICIES:
        fname = build_pdf(doc_id, title, ptype, version, status, sections)
        catalog[fname] = {"doc_id": doc_id, "policy_type": ptype, "version": version,
                          "status": status, "title": title}
    (OUT_DIR / "catalog.json").write_text(json.dumps(catalog, indent=2))
    print(f"Generated {len(catalog)} policy PDFs + catalog.json in {OUT_DIR}")


if __name__ == "__main__":
    main()
