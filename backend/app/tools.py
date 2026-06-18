"""CRM data access and refund policy enforcement tools."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CRM_PATH = DATA_DIR / "crm.json"
POLICY_PATH = DATA_DIR / "refund_policy.md"

TIER_WINDOWS = {"standard": 30, "gold": 45, "platinum": 60}


def _load_crm() -> dict:
    with open(CRM_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_crm(data: dict) -> None:
    with open(CRM_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_policy_text() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def lookup_customer(identifier: str) -> dict:
    """Look up customer by email or customer_id."""
    data = _load_crm()
    identifier_lower = identifier.strip().lower()
    for customer in data["customers"]:
        if (
            customer["email"].lower() == identifier_lower
            or customer["customer_id"].lower() == identifier_lower
        ):
            return {
                "found": True,
                "customer_id": customer["customer_id"],
                "name": customer["name"],
                "email": customer["email"],
                "loyalty_tier": customer["loyalty_tier"],
                "refund_count_90d": customer["refund_count_90d"],
                "refund_abuse_flag": customer["refund_abuse_flag"],
                "order_ids": [o["order_id"] for o in customer["orders"]],
            }
    return {"found": False, "message": f"No customer found for '{identifier}'"}


def get_order_details(order_id: str) -> dict:
    """Retrieve full order details from CRM."""
    data = _load_crm()
    order_id_upper = order_id.strip().upper()
    for customer in data["customers"]:
        for order in customer["orders"]:
            if order["order_id"].upper() == order_id_upper:
                return {
                    "found": True,
                    "customer_id": customer["customer_id"],
                    "customer_name": customer["name"],
                    "customer_email": customer["email"],
                    "loyalty_tier": customer["loyalty_tier"],
                    **order,
                }
    return {"found": False, "message": f"Order '{order_id}' not found"}


def _days_since_delivery(delivery_date: str) -> int:
    delivered = datetime.strptime(delivery_date, "%Y-%m-%d").date()
    return (date(2026, 6, 18) - delivered).days


def check_refund_eligibility(
    order_id: str,
    reason: str,
    item_condition: str = "unknown",
) -> dict:
    """Run strict policy checks against an order."""
    order = get_order_details(order_id)
    if not order.get("found"):
        return {"eligible": False, "reasons": [order.get("message", "Order not found")]}

    data = _load_crm()
    customer = next(
        c for c in data["customers"] if c["customer_id"] == order["customer_id"]
    )
    reasons: list[str] = []
    warnings: list[str] = []
    policy_sections: list[str] = []

    if order.get("refund_status") == "approved":
        reasons.append("Duplicate refund: this order was already refunded (Policy §4)")
        policy_sections.append("§4")

    if order.get("final_sale"):
        reasons.append("Final sale item — non-refundable (Policy §2)")
        policy_sections.append("§2")

    if order.get("digital"):
        reasons.append("Digital goods are non-refundable after access (Policy §2)")
        policy_sections.append("§2")

    tier = customer["loyalty_tier"]
    window = TIER_WINDOWS.get(tier, 30)
    days = _days_since_delivery(order["delivery_date"])
    if days > window:
        reasons.append(
            f"Outside {window}-day window for {tier} tier ({days} days elapsed, Policy §1)"
        )
        policy_sections.append("§1")

    if customer["refund_abuse_flag"]:
        if not (order["amount"] < 25 and days <= 14):
            reasons.append(
                "Customer flagged for refund abuse — denied unless order <$25 within 14 days (Policy §4)"
            )
            policy_sections.append("§4")

    if customer["refund_count_90d"] >= 3:
        reasons.append(
            f"Customer has {customer['refund_count_90d']} refunds in 90 days (max 3, Policy §4)"
        )
        policy_sections.append("§4")

    category = order["category"]
    condition = item_condition.lower().replace(" ", "_")

    if category == "electronics" and condition not in ("sealed", "unopened", "unknown"):
        if condition == "opened":
            reasons.append("Electronics must be unopened/sealed (Policy §2)")
            policy_sections.append("§2")
        else:
            warnings.append("15% restocking fee applies for opened electronics (Policy §5)")

    if category == "home_kitchen" and condition == "opened":
        reasons.append("Home & Kitchen items must be unused with packaging intact (Policy §2)")
        policy_sections.append("§2")

    if category == "apparel" and condition == "worn_once":
        warnings.append("Partial refund (50%) applies — item worn once (Policy §2)")

    requires_escalation = order["amount"] > 200
    partial_refund_pct = 50 if condition == "worn_once" and category == "apparel" else 100
    restocking_fee_pct = 15 if category in ("electronics", "home_kitchen") and condition == "opened" else 0

    eligible = len(reasons) == 0
    refund_amount = order["amount"] * (partial_refund_pct / 100)
    if restocking_fee_pct:
        refund_amount *= 1 - restocking_fee_pct / 100

    return {
        "eligible": eligible,
        "order_id": order_id,
        "order_amount": order["amount"],
        "estimated_refund": round(refund_amount, 2),
        "requires_escalation": requires_escalation and eligible,
        "partial_refund_pct": partial_refund_pct,
        "restocking_fee_pct": restocking_fee_pct,
        "days_since_delivery": days,
        "loyalty_tier": tier,
        "reasons": reasons,
        "warnings": warnings,
        "policy_sections_violated": list(set(policy_sections)),
        "customer_reason": reason,
    }


def process_refund(order_id: str, force: bool = False) -> dict:
    """Process refund if eligible. Returns approval or denial."""
    eligibility = check_refund_eligibility(order_id, reason="processing")
    if not eligibility["eligible"] and not force:
        return {
            "approved": False,
            "order_id": order_id,
            "message": "Refund denied per policy",
            "reasons": eligibility["reasons"],
            "policy_sections": eligibility.get("policy_sections_violated", []),
        }

    if eligibility.get("requires_escalation"):
        return {
            "approved": False,
            "order_id": order_id,
            "message": "Order value exceeds $200 — manager escalation required before approval",
            "requires_escalation": True,
        }

    data = _load_crm()
    for customer in data["customers"]:
        for order in customer["orders"]:
            if order["order_id"].upper() == order_id.strip().upper():
                order["refund_status"] = "approved"
                customer["refund_count_90d"] = customer.get("refund_count_90d", 0) + 1
                _save_crm(data)
                return {
                    "approved": True,
                    "order_id": order_id,
                    "refund_amount": eligibility["estimated_refund"],
                    "message": f"Refund of ${eligibility['estimated_refund']:.2f} approved for order {order_id}",
                    "confirmation_id": f"REF-{order_id[-5:]}-OK",
                }

    return {"approved": False, "message": "Order not found"}


def escalate_to_human(order_id: str, reason: str) -> dict:
    """Flag case for human manager review."""
    return {
        "escalated": True,
        "order_id": order_id,
        "case_id": f"ESC-{order_id[-5:]}",
        "reason": reason,
        "message": f"Case ESC-{order_id[-5:]} created. A manager will follow up within 24 hours.",
    }
