# AnalyticsHub — Product Reference

## Overview

AnalyticsHub is a self-serve business intelligence platform that connects to live data sources, enables drag-and-drop dashboard creation, and delivers scheduled reports via email, Slack, or webhook. It is designed for both technical and non-technical users.

**Current stable version:** 3.0.0  
**Previous stable version:** 2.9.4

---

## Core Modules

### Dashboard

Interactive visualisation canvas. Supports charts (line, bar, scatter, pie, heatmap), KPI tiles, data tables, and embedded SQL views.

- **Performance note:** dashboards with more than 20 widgets or queries spanning > 12 months of data may load slowly. Use the Query Optimiser (Settings → Performance → Optimise) before publishing.
- Auto-refresh interval: configurable from 1 minute to 24 hours.
- Sharing: dashboards can be shared as view-only links (no login required) or embedded via iframe.

### Reports

Scheduled PDF/CSV/Excel exports delivered on a cron schedule.

- Maximum report size: 50 MB. Reports exceeding this are split into parts automatically.
- Exports are retained for 30 days in Settings → Reports → Archive.
- If an export is truncated at 1000 rows, check the plan limit (Starter: 1000 rows, Professional: 100,000 rows, Business/Enterprise: unlimited).

### Data Sources

Connectors to databases (PostgreSQL, MySQL, Snowflake, BigQuery, Redshift), APIs (REST/GraphQL with OAuth), and file uploads (CSV, Excel, JSON).

- Data source credentials are encrypted at rest with AES-256 and in transit with TLS 1.3.
- Connection test available before saving: Settings → Data Sources → [source] → Test Connection.
- Query timeout: 120 seconds (configurable up to 600s for Business/Enterprise).

### Alerts

Threshold-based alerts that fire when a metric crosses a defined boundary.

- Alert channels: email, Slack, PagerDuty, webhook.
- Alert suppression: set a cool-down period to avoid alert storms (minimum 5 minutes).
- If alerts are not firing, verify the channel token is valid: Settings → Alerts → [alert] → Test Alert.

### Exports

On-demand data export from any dashboard widget or underlying query.

- Supported formats: CSV, Excel (.xlsx), JSON, Parquet.
- Row limit by plan: Starter 1,000 | Professional 100,000 | Business 1,000,000 | Enterprise unlimited.

---

## Common Support Scenarios

### Dashboard loads slowly or times out

1. Open the Query Profiler: Dashboard → [widget] → Edit → Profiler.
2. Look for full-table scans or missing indexes on the source database.
3. Add date range filters to limit the data window.
4. Enable caching for the data source: Settings → Data Sources → [source] → Enable Query Cache.
5. If the issue persists after caching, contact support — the team can review query plans.

### Report exports truncated at 1000 rows

This is a plan limit, not a bug.

- Starter plan: 1,000 rows per export.
- Upgrade to Professional or above for higher limits.
- Workaround (Starter): split the export into multiple date ranges.

### Alert not triggering

1. Confirm the alert condition is actually met by running the underlying query manually.
2. Check the cool-down period — the alert may be suppressed.
3. Verify the notification channel token: Settings → Alerts → [alert] → Test Alert.
4. Check email spam folder or Slack app permissions if the alert fires (visible in alert history) but messages are not received.

---

## Pricing & Limits by Plan

| Feature | Starter | Professional | Business | Enterprise |
| --------- | --------- | -------------- | ---------- | ------------ |
| Dashboards | 5 | 50 | 500 | Unlimited |
| Scheduled reports | 2 | 20 | 100 | Unlimited |
| Export row limit | 1,000 | 100,000 | 1,000,000 | Unlimited |
| Data source connections | 2 | 10 | 50 | Unlimited |
| Support SLA | 48h | 24h | 8h | 2h |
