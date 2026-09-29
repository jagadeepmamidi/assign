# Data Schema Reference

Full field-level documentation with example records for both datasets.

---

## tickets.json — Example Record

```json
{
  "ticket_id": "TKT-10042",
  "account_id": "ACC-3847",
  "company": "Initech",
  "subject": "Unable to connect DataBridge Pro to Connectors",
  "body": "Hi team,\n\nWe're experiencing a critical issue with DataBridge Pro. Our Connectors pipeline has been failing since approximately yesterday morning. Error message: 'ERR_CONNECTION_TIMEOUT after 30s'\n\nThis is impacting 47 users in our Engineering team. We've tried restarting the service and clearing the cache but the issue persists.\n\nEnvironment: Production\nVersion: 3.1.2\n\nPlease advise urgently.",
  "product": "DataBridge Pro",
  "product_area": "Connectors",
  "category": "Bug",
  "urgency": "P2",
  "status": "In Progress",
  "plan_tier": "Enterprise",
  "assigned_agent": "Sarah Chen",
  "created_at": "2025-04-15T09:23:11Z",
  "updated_at": "2025-04-15T11:47:03Z",
  "tags": ["databridge-pro", "connectors", "p2"],
  "channel": "portal",
  "satisfaction_score": null
}
```

### Field Enum Values

**`category`**

- `Bug` — product defect or unexpected behaviour
- `Feature Request` — request for new functionality
- `How-To` — guidance or documentation request
- `Performance` — slowness, timeouts, throughput issues
- `Billing` — invoice, payment, or plan questions
- `Integration` — third-party integration issues
- `Onboarding` — new user or new organisation setup
- `Data Loss` — missing, corrupted, or inaccessible data

**`urgency`**

- `P1` — critical, business stopped (~5% of tickets)
- `P2` — major impact, significant workaround needed (~20%)
- `P3` — moderate impact, workaround available (~45%)
- `P4` — low impact, cosmetic or minor (~30%)

**`status`**

- `Open` — newly created, not yet assigned
- `In Progress` — agent is actively working
- `Pending Customer` — awaiting customer response
- `Resolved` — fix applied, pending customer confirmation
- `Closed` — confirmed resolved or auto-closed after 7 days

**`channel`**

- `email` — submitted via support email address
- `portal` — submitted via the self-service support portal
- `chat` — submitted via in-app live chat
- `phone` — phone call, transcribed to ticket by agent

**`plan_tier`**

- `Starter`, `Professional`, `Business`, `Enterprise`

---

## accounts.json — Example Record

```json
{
  "account_id": "ACC-3847",
  "company": "Initech",
  "tam": "Olivia Grant",
  "plan_tier": "Enterprise",
  "arr_usd": 240000,
  "seats_licensed": 350,
  "seats_active": 298,
  "products": ["DataBridge Pro", "AnalyticsHub", "WorkflowEngine"],
  "health_status": "At Risk",
  "usage_trend": "Declining",
  "open_tickets": 7,
  "p1_tickets_last_30d": 2,
  "customer_since": "2021-03-12",
  "renewal_date": "2025-12-31",
  "last_qbr_date": "2025-02-18",
  "primary_contact": {
    "name": "Alex Morgan",
    "title": "VP Engineering"
  },
  "escalation_notes": [
    "Customer expressed frustration with response times in last sync",
    "Decision maker considering competing vendor evaluation",
    "Champion left the company — no replacement identified yet"
  ],
  "nps_score": 4,
  "last_login_days_ago": 2,
  "integrations_active": ["Salesforce", "Snowflake", "Slack"],
  "region": "US-East",
  "industry": "Financial Services"
}
```

### Field Enum Values

**`health_status`**

- `Healthy` — stable usage, positive sentiment (~50% of accounts)
- `At Risk` — declining usage or negative signals (~25%)
- `Churning` — explicit churn signals or cancellation intent (~10%)
- `New` — onboarded within last 90 days (~15%)

**`usage_trend`**

- `Increasing` — active seat count and/or feature usage growing
- `Stable` — no significant change over 60 days
- `Declining` — seat usage or feature adoption dropping
- `Inactive` — no logins in last 30 days

**`region`**

- `US-East`, `US-West`, `US-Central`, `EU-West`, `APAC`

**`industry`**

- Financial Services, Healthcare, Retail, Manufacturing, Technology,
  Media, Education, Government, Logistics, Energy

---

## Joining Tickets to Accounts

Tickets reference accounts via `account_id`. Note:

- Not every `account_id` in `tickets.json` will have a matching record in `accounts.json`. This reflects real-world data gaps — handle gracefully.
- One account can have many tickets (one-to-many relationship).
- Use the last 90 days of tickets for account health analysis (filter by `created_at`).

```python
import json

tickets  = json.load(open("data/tickets.json"))
accounts = json.load(open("data/accounts.json"))

# Build account lookup
account_map = {a["account_id"]: a for a in accounts}

# Get tickets for a specific account
def get_account_tickets(account_id, tickets, days=90):
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [
        t for t in tickets
        if t["account_id"] == account_id
        and datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) > cutoff
    ]
```

---

## Knowledge Base Structure

```
knowledge-base/
├── products/           # One file per product — features, config, error codes
├── troubleshooting/    # Cross-product troubleshooting guides
├── billing/            # Plan details, seat billing, invoicing
└── onboarding/         # New user and new organisation setup
```

Each knowledge-base document is standard Markdown. For RAG implementations, recommended chunking strategy:

- Split on `---` horizontal rules (major section boundaries)
- Preserve heading hierarchy as metadata for retrieval filtering
- Table rows make good atomic chunks for error code lookups
