# WorkflowEngine — Product Reference

## Overview

WorkflowEngine is a no-code/low-code automation platform that connects triggers (events from integrated apps) to actions (operations in internal or external systems). It is designed for operations, RevOps, and engineering teams who need reliable, observable automation without building custom integrations.

**Current stable version:** 3.1.2  
**Previous stable version:** 3.0.5

---

## Core Modules

### Triggers

Events that start a workflow. Supported trigger types:

- **Webhook** — HTTP POST to a unique workflow URL
- **Schedule** — cron expression (e.g., `0 9 * * 1` = every Monday at 09:00)
- **App event** — native events from connected apps (e.g., "new Jira ticket created", "Salesforce deal closed")
- **Manual** — triggered by a user via the UI or API

Trigger reliability: Webhook triggers have an at-least-once delivery guarantee. Idempotency keys (`X-Workflow-Idempotency-Key` header) prevent duplicate execution.

### Actions

Operations performed when a workflow runs. Each action connects to an integration and performs a specific operation (create record, send message, update field, call API endpoint, etc.).

- Actions execute sequentially by default. Parallel branches available on Professional+.
- Maximum actions per workflow: 50 (Starter), 200 (Professional), unlimited (Business/Enterprise).
- Action timeout: 30 seconds per action. Use async actions for long-running operations.

### Scheduling

Cron-based and interval-based scheduling.

- Timezone support: all IANA timezones. Configure in workflow Settings → Schedule → Timezone.
- Missed executions: if a scheduled workflow fails to run (e.g., during maintenance), it will execute once on recovery — it does not back-fill all missed runs.
- If scheduled jobs are not executing, check: workflow is enabled, schedule is valid (use the cron validator in the UI), and the workflow has not exceeded the error threshold (3 consecutive failures pauses the workflow).

### Error Handling

- **Retry policy:** configurable per workflow. Default: 3 retries with exponential backoff.
- **Dead-letter queue (DLQ):** failed executions after all retries are stored for 7 days. Review at Workflows → [workflow] → Execution History → Failed.
- **Error notifications:** configure email/Slack alerts when a workflow enters error state.
- **Circuit breaker:** after 10 consecutive failures, the workflow is automatically paused to prevent cascading errors.

### Templates

Pre-built workflow templates for common use cases:

- Ticket-to-task sync (Zendesk ↔ Jira)
- New customer onboarding sequence
- SLA breach alert escalation
- Nightly data export to Snowflake
- Salesforce deal won → Slack announcement

Templates are available at: Workflows → New → Browse Templates.

---

## Common Support Scenarios

### Scheduled workflow not running

1. Confirm the workflow is **enabled** (green status indicator).
2. Validate the cron expression using Workflows → [workflow] → Schedule → Validate.
3. Check if the workflow was auto-paused: 3 consecutive failures trigger an automatic pause.
4. Review Execution History for the last attempted run and its error.
5. Check timezone — a workflow scheduled for "09:00" in a UTC workflow running in a US timezone will appear to run at unexpected local times.

### Workflow runs but changes don't persist

This is usually an action configuration issue:

1. Open the execution log for the failed run: Execution History → [run] → Action Detail.
2. Look for `200 OK` responses with empty bodies — some APIs return success but don't apply the change if required fields are missing.
3. Verify the action's field mapping: the correct record ID field must be mapped from a previous step.
4. Enable "Strict mode" on the action to surface silent failures.

### Duplicate workflow executions

If a webhook trigger is causing duplicate executions:

1. Enable idempotency: add `X-Workflow-Idempotency-Key` to webhook calls (typically the source event ID).
2. WorkflowEngine deduplicates identical idempotency keys within a 24-hour window.
3. If duplicates persist, check if the source system is retrying failed webhook deliveries — configure the source to check for `200 OK` before retrying.

---

## Pricing & Limits by Plan

| Feature | Starter | Professional | Business | Enterprise |
| --------- | --------- | -------------- | ---------- | ------------ |
| Active workflows | 10 | 100 | 1,000 | Unlimited |
| Executions/month | 1,000 | 50,000 | 500,000 | Unlimited |
| Actions per workflow | 50 | 200 | 500 | Unlimited |
| Parallel branches | No | Yes | Yes | Yes |
| Support SLA | 48h | 24h | 8h | 2h |
