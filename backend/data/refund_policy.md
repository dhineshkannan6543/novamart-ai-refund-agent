# NovaMart Refund Policy (Strict)

**Effective Date:** January 1, 2026  
**Policy Version:** 2.4

## 1. Eligibility Window

- Standard customers: refunds must be requested within **30 days** of delivery.
- Gold loyalty tier: **45 days**.
- Platinum loyalty tier: **60 days**.
- Requests outside the window are **automatically denied** unless a documented shipping delay of 7+ days is verified.

## 2. Product Condition Requirements

| Category        | Condition Required                          | Partial Refund Allowed |
|-----------------|---------------------------------------------|------------------------|
| Electronics     | Unopened, factory sealed                    | No                     |
| Apparel         | Unworn, tags attached, no odors            | Yes (50% if worn once) |
| Home & Kitchen  | Unused, original packaging intact           | No                     |
| Digital Goods   | **Non-refundable** after download/access  | No                     |
| Final Sale      | **Non-refundable** under all circumstances  | No                     |

## 3. Order Value Thresholds

- Orders under **$25**: auto-approved if all other criteria met.
- Orders **$25–$200**: agent review required.
- Orders over **$200**: requires manager escalation flag (tool: `escalate_to_human`).

## 4. Refund Limits & Abuse Prevention

- Maximum **3 refunds per customer per rolling 90-day period**.
- Customers with `refund_abuse_flag: true` in CRM are **denied** unless order is under $25 and within 14 days.
- Duplicate refund requests for the same order are **denied**.

## 5. Shipping & Restocking

- Free return shipping provided for defective items only (must attach defect note).
- 15% restocking fee applies to opened electronics and home goods.
- Customer pays return shipping for change-of-mind returns on apparel.

## 6. Required Verification Steps (Agent Must Complete)

Before approving ANY refund, the agent **must** call these tools in order:

1. `lookup_customer` — verify identity and loyalty tier
2. `get_order_details` — confirm order exists, delivery date, items, final-sale flags
3. `check_refund_eligibility` — run automated policy check
4. `process_refund` — only if eligibility returns `eligible: true`

Skipping steps or approving when `eligible: false` is a **policy violation**.

## 7. Denial Response Guidelines

When denying a refund, agents must:

- Cite the specific policy section violated
- Offer alternatives (store credit, exchange) when applicable
- Remain firm but empathetic — **do not override policy** for emotional appeals

## 8. Voice & Chat Channel Parity

All rules above apply equally to voice and text channels. Verbal confirmation of order number is required for voice interactions.
