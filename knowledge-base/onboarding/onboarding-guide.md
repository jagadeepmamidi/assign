# Onboarding Guide — New Customers & Users

## New Organisation Onboarding Checklist

Complete these steps within the first 7 days to ensure a smooth rollout.

### Step 1: Account setup (Day 1)

- [ ] Verify the admin email and accept the invitation
- [ ] Set organisation name and region: Settings → Organisation → General
- [ ] Configure SSO if on Business/Enterprise plan: Settings → SSO (see [Authentication & SSO guide](../troubleshooting/authentication-sso.md))
- [ ] Set the default session timeout: Settings → Security → Session Timeout (recommended: 8 hours)
- [ ] Enable MFA requirement for all users: Settings → Security → Require MFA

### Step 2: User provisioning (Days 1–3)

**Option A — Bulk CSV import:**

1. Download the template: Settings → Users → Import → Download Template.
2. Fill in: email, first name, last name, role (`admin`, `editor`, `viewer`).
3. Upload and confirm. Invitation emails are sent automatically.

**Option B — SSO auto-provisioning (Business/Enterprise):**

1. Configure your IDP to send SCIM provisioning events to the platform.
2. SCIM endpoint: `https://[product].yourdomain.com/scim/v2/`
3. Bearer token: generate at Settings → SSO → SCIM → Generate Token.
4. New IDP users are provisioned automatically within 5 minutes of their first SSO login.

**Option C — Manual invite:**
Settings → Users → Invite User → enter email and role.

### Step 3: Product configuration (Days 2–5)

Refer to the relevant product guide for initial setup:

- [DataBridge Pro](../products/databridge-pro.md) — configure first data source and pipeline
- [CloudSync](../products/cloudsync.md) — set up first sync job
- [AnalyticsHub](../products/analyticshub.md) — connect first data source and create a dashboard
- [SecureVault](../products/securevault.md) — import first secrets and configure key rotation
- [WorkflowEngine](../products/workflowengine.md) — create first workflow from a template

### Step 4: Notifications & alerting (Day 3–5)

- Configure Slack or email notifications: Settings → Notifications.
- Set up at least one admin alert for service errors and billing thresholds.
- For Enterprise: your dedicated TAM will schedule a kick-off call in the first 5 days.

### Step 5: Training (Days 5–7)

- Self-paced courses: Help → Learning Centre.
- Live onboarding webinar: runs every Tuesday at 10:00 AM ET — register at help.yourplatform.com/webinars.
- Enterprise: schedule a bespoke training session with your TAM.

---

## Role Reference

| Role | Can do | Cannot do |
| ------ | -------- | ----------- |
| **Admin** | Everything | — |
| **Editor** | Create/edit all objects, run workflows, export data | Manage billing, manage users, change SSO config |
| **Viewer** | Read-only access to all objects | Create, edit, delete, or export |
| **API User** | Programmatic access per assigned token scopes | UI login |

---

## Bulk User Provisioning FAQ

**Q: How many users can I import at once?**  
A: CSV import supports up to 500 users per file. For larger imports, use SCIM or split into multiple CSVs.

**Q: What if an invited user doesn't receive the invitation email?**  
A: Check spam folders. If not found, resend from Settings → Users → [user] → Resend Invite. Invitations expire after 7 days.

**Q: Can I set different product access per user?**  
A: Yes — on Business/Enterprise, product-level permissions can be configured per user or per group: Settings → Users → [user] → Product Access.

---

## Recommended Training Path by Role

### Technical users (engineers, IT admins)

1. Platform architecture overview (30 min) — Learning Centre
2. API & authentication (45 min) — Learning Centre
3. Product-specific deep dive (1–2 hours each) — Learning Centre
4. Office hours: Thursdays 2:00 PM ET — register at help.yourplatform.com/office-hours

### Business users (analysts, operations, RevOps)

1. Getting started with dashboards — AnalyticsHub (20 min)
2. Building your first workflow — WorkflowEngine (30 min)
3. Self-serve reporting guide (25 min)
4. Webinar: Data for non-technical teams — every second Wednesday

### Admins

1. Security & compliance configuration (45 min)
2. User management & SSO (30 min)
3. Billing & plan management (20 min)
4. Audit logging best practices (30 min)
