# Billing & Plans — Reference Guide

## Plan Overview

| | Starter | Professional | Business | Enterprise |
| -- | --------- | -------------- | ---------- | ------------ |
| **Price (per seat/month)** | $15 | $45 | $90 | Custom |
| **Minimum seats** | 1 | 5 | 20 | 50 |
| **Billing cycle** | Monthly | Monthly or Annual | Annual | Annual |
| **Support SLA** | 48h | 24h | 8h | 2h (dedicated TAM) |
| **SSO / SAML** | No | No | Yes | Yes |
| **Audit logs retention** | 30 days | 90 days | 1 year | 7 years |
| **Customer-managed keys** | No | No | Yes | Yes |
| **Dedicated TAM** | No | No | No | Yes |

Annual billing includes a 20% discount vs monthly.

---

## How Seat Billing Works

A **seat** is any user account that was active (logged in or made an API call) at least once during the billing period.

- Seats are counted at the end of each billing month.
- Adding users mid-month is prorated to the day.
- Deactivating a user does **not** immediately free the seat — the account is counted until the billing month closes.
- **Overage:** if active users exceed the purchased seat count, overage is billed at 1.5× the per-seat rate.

**Common billing query:** "We're being charged for N seats but only have M active users."

Resolution steps:

1. Export the active user list: Settings → Users → Export → filter "Active in last 30 days".
2. Compare against the invoice seat count.
3. Check for service accounts and API users — these count as seats.
4. If a discrepancy remains after this check, raise a billing dispute with the exported list attached.

---

## Invoices & Payment

- Invoices are generated on the 1st of each month (monthly) or on the annual renewal date.
- Payment methods: credit card, ACH (US), SEPA (EU), wire transfer (Enterprise only).
- Invoices are available at Settings → Billing → Invoices.
- Invoice disputes must be raised within 30 days of issue date.

---

## Upgrading Plans

### Self-serve upgrade (Starter → Professional → Business)

1. Settings → Billing → Change Plan.
2. Select new plan and confirm seat count.
3. Prorated charge applied immediately; new features available within minutes.

### Enterprise upgrade

Enterprise plans require a sales conversation for custom pricing, SLA negotiation, and TAM assignment.

1. Submit upgrade interest at Settings → Billing → Contact Sales, or email your current TAM.
2. Sales will respond within 1 business day.
3. Enterprise onboarding includes a kick-off call, dedicated Slack channel, and a 30-day parallel support period.

---

## Cancellation & Downgrade Policy

- **Monthly plans:** cancel at any time. Access continues until end of the current billing month. No refunds for partial months.
- **Annual plans:** cancel within 30 days for a full refund. After 30 days, no refunds — access continues until the annual period ends.
- **Downgrade:** if downgrading to a lower plan, data exceeding the new plan's limits is read-only until reduced below the limit.

---

## Common Billing FAQs

**Q: Can I get a credit for service downtime?**  
A: Yes, for incidents breaching the plan's SLA uptime guarantee. Submit a credit request within 30 days of the incident at Settings → Billing → Request Credit, citing the incident ID from the status page.

**Q: Are there discounts for non-profits or education?**  
A: Yes — 30% discount for verified non-profits and educational institutions. Apply at <billing@yourplatform.com> with your charity registration or .edu domain verification.

**Q: What happens to my data if I cancel?**  
A: Data is retained in a read-only state for 90 days after cancellation. You can export all data during this window. After 90 days, data is permanently deleted.
