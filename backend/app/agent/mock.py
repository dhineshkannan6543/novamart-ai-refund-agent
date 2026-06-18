"""Rule-based fallback agent when OPENAI_API_KEY is not configured."""

from __future__ import annotations

import re
import uuid

from app.models import LogLevel, log_broadcaster
from app.tools import (
    check_refund_eligibility,
    get_order_details,
    lookup_customer,
    process_refund,
)


def _extract_order_id(text: str) -> str | None:
    match = re.search(r"ORD-\d+", text.upper())
    return match.group(0) if match else None


async def run_mock_agent(
    user_message: str,
    session_id: str | None = None,
    customer_email: str | None = None,
) -> tuple[str, str, str | None]:
    sid = session_id or str(uuid.uuid4())[:8]

    await log_broadcaster.emit(
        sid,
        LogLevel.INFO,
        "Running deterministic fallback agent",
        {"message": user_message},
    )

    order_id = _extract_order_id(user_message)
    identifier = customer_email or user_message

    if customer_email:
        await log_broadcaster.emit(sid, LogLevel.REASONING, "Looking up customer...")
        customer = lookup_customer(customer_email)
        await log_broadcaster.emit(
            sid, LogLevel.TOOL, "lookup_customer", {"result": customer}
        )
        if not customer.get("found") and not order_id:
            return sid, f"I couldn't find an account for {customer_email}. Please verify your email.", None

    if not order_id:
        return (
            sid,
            "I'd be happy to help with your refund. Could you provide your order number (e.g., ORD-10012)?",
            None,
        )

    await log_broadcaster.emit(sid, LogLevel.REASONING, f"Fetching order {order_id}...")
    order = get_order_details(order_id)
    await log_broadcaster.emit(sid, LogLevel.TOOL, "get_order_details", {"result": order})

    if not order.get("found"):
        return sid, f"I couldn't find order {order_id}. Please double-check the number.", None

    condition = "unknown"
    lower = user_message.lower()
    if "sealed" in lower or "unopened" in lower:
        condition = "sealed"
    elif "tag" in lower:
        condition = "tags_attached"
    elif "worn" in lower:
        condition = "worn_once"
    elif "opened" in lower:
        condition = "opened"

    await log_broadcaster.emit(sid, LogLevel.REASONING, "Running policy eligibility check...")
    eligibility = check_refund_eligibility(order_id, user_message, condition)
    await log_broadcaster.emit(
        sid, LogLevel.TOOL, "check_refund_eligibility", {"result": eligibility}
    )

    if not eligibility["eligible"]:
        await log_broadcaster.emit(
            sid,
            LogLevel.DENIAL,
            f"Policy denial: {'; '.join(eligibility['reasons'])}",
            eligibility,
        )
        reasons = "; ".join(eligibility["reasons"])
        sections = ", ".join(eligibility.get("policy_sections_violated", []))
        return (
            sid,
            f"I understand your frustration, but I'm unable to approve this refund. "
            f"Reason: {reasons} (Policy {sections}). "
            f"I can offer a store credit or exchange as an alternative. Would that work for you?",
            "denied",
        )

    if eligibility.get("requires_escalation"):
        await log_broadcaster.emit(
            sid, LogLevel.INFO, "High-value order — escalation required", eligibility
        )
        return (
            sid,
            f"Your order {order_id} (${order['amount']:.2f}) qualifies for a refund, but orders over $200 "
            f"require manager approval. I've flagged case ESC-{order_id[-5:]} for review within 24 hours.",
            "denied",
        )

    await log_broadcaster.emit(sid, LogLevel.REASONING, "Processing approved refund...")
    result = process_refund(order_id)
    await log_broadcaster.emit(sid, LogLevel.TOOL, "process_refund", {"result": result})

    if result.get("approved"):
        await log_broadcaster.emit(sid, LogLevel.SUCCESS, result["message"], result)
        return (
            sid,
            f"Great news! Your refund of ${result['refund_amount']:.2f} for order {order_id} has been approved. "
            f"Confirmation: {result['confirmation_id']}. You'll see it in 3–5 business days.",
            "approved",
        )

    await log_broadcaster.emit(sid, LogLevel.DENIAL, result.get("message", "Denied"), result)
    return sid, result.get("message", "Refund could not be processed."), "denied"
