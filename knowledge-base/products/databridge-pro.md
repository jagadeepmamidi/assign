# DataBridge Pro — Product Reference

## Overview

DataBridge Pro is a managed data integration platform that enables organisations to ingest, transform, and route data between internal systems and third-party services. It supports batch and streaming pipelines, schema validation, and a connector marketplace with 80+ pre-built integrations.

**Current stable version:** 3.1.2  
**Previous stable version:** 2.6.0  
**Deprecated (EOL 2025-12-31):** 2.3.x and below

---

## Core Modules

### Data Ingestion

Handles raw data intake from sources including REST APIs, databases, file uploads (CSV, JSON, Parquet), and message queues (Kafka, SQS).

**Key configuration fields:**

- `source_type` — one of `rest_api`, `database`, `file`, `queue`
- `batch_size` — records per batch (default: 1000, max: 50000)
- `retry_policy` — `none`, `linear`, or `exponential` (recommended: `exponential`)
- `schema_enforcement` — `strict`, `loose`, or `off`

**Common errors:**

- `ERR_CONNECTION_TIMEOUT` — Source unreachable. Check network rules and firewall allowlist.
- `SCHEMA_MISMATCH` — Incoming record does not match registered schema. Review schema version in Schema Management.
- `RATE_LIMIT_EXCEEDED` — Source API has throttled requests. Reduce `batch_size` or add delay between batches.

### Schema Management

Maintains versioned schemas for all data streams. Schemas are defined in JSON Schema draft-07 format.

- **Schema registry URL:** `https://registry.databridge.yourdomain.com`
- Schema versions are immutable once published. Create a new version to make changes.
- Breaking changes (field removal, type change) require a new major version and a migration plan.

**Tip:** Use `schema_enforcement: loose` during initial onboarding, then tighten to `strict` once the pipeline is stable.

### Pipeline Monitoring

Real-time and historical visibility into pipeline health.

- **Heartbeat interval:** every 60 seconds. If no heartbeat for 15 minutes, alert fires.
- **Dashboard path:** Settings → Monitoring → Pipelines
- **Key metrics:** records_processed, error_rate, lag_seconds, throughput_rps

**Alert thresholds (defaults):**

| Metric | Warning | Critical |
| -------- | --------- | ---------- |
| Error rate | > 1% | > 5% |
| Lag | > 30s | > 300s |
| Heartbeat | missed 1 | missed 3 |

### Connectors

Pre-built connectors are available for Salesforce, Snowflake, BigQuery, Jira, HubSpot, Slack, and 75+ others.

- Connector versions are pinned per pipeline. Update connectors explicitly — they do not auto-update.
- OAuth connectors require token refresh every 60 days. Set calendar reminders or enable auto-refresh in Settings → Connectors → [connector name] → Auto-refresh.

### API

Full REST API available at `https://api.databridge.yourdomain.com/v3/`.

- Authentication: Bearer token (API key from Settings → API Keys)
- Rate limit: 1000 req/min (Enterprise), 200 req/min (Professional), 60 req/min (Starter)
- Webhook delivery: HMAC-SHA256 signature in `X-DataBridge-Signature` header

---

## Common Support Scenarios

### Pipeline stopped processing

1. Check Pipeline Monitoring dashboard for last heartbeat.
2. Review error logs under Monitoring → Logs → filter by pipeline ID.
3. Check if source credentials have expired (common after 90 days).
4. Restart the pipeline from the UI: Pipelines → [pipeline] → Actions → Restart.
5. If restart fails, check downstream quota: `QUOTA_EXCEEDED` error indicates storage limit reached.

### Schema mismatch errors flooding logs

1. Identify the field causing the mismatch in the error detail.
2. In Schema Management, compare the registered schema version vs the incoming payload.
3. Either update the source to match the schema, or publish a new schema version.
4. Do **not** set `schema_enforcement: off` in production — this bypasses all validation.

### Connector authentication failure

1. Regenerate the OAuth token from the connector settings page.
2. Ensure the redirect URI matches exactly (including trailing slash).
3. For Salesforce: confirm the Connected App has `api`, `refresh_token`, and `offline_access` scopes.
4. For BigQuery: the service account must have `roles/bigquery.dataEditor` on the target dataset.

---

## Pricing & Limits by Plan

| Feature | Starter | Professional | Business | Enterprise |
| --------- | --------- | -------------- | ---------- | ------------ |
| Pipelines | 5 | 25 | 100 | Unlimited |
| Records/month | 5M | 50M | 500M | Unlimited |
| Connectors | 10 | 40 | 80 | All |
| API rate limit | 60/min | 200/min | 500/min | 1000/min |
| Support SLA | 48h | 24h | 8h | 2h |
