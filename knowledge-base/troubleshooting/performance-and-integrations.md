# Troubleshooting: Performance Issues

This guide covers performance degradation, timeouts, and slow response issues across all products.

---

## Error Reference

| Error | Likely Cause | Resolution |
| ------- | ------------- | ------------ |
| `ERR_CONNECTION_TIMEOUT after 30s` | Network or source unreachable | Check firewall, VPN, and source availability |
| `PIPELINE_STALLED: no heartbeat for 15 minutes` | Pipeline worker crashed or source blocked | Restart pipeline; check source credentials |
| `RATE_LIMIT_EXCEEDED: retry after 60s` | API quota hit on source or destination | Reduce batch size or add retry backoff |
| `QUOTA_EXCEEDED: storage limit reached` | Plan storage limit hit | Archive old data or upgrade plan |
| `DEPENDENCY_UNAVAILABLE` | Downstream service unreachable | Check status page; retry after resolution |

---

## Diagnosing Slow Performance

### Step 1 — Identify where the slowness is

- **UI slow (all pages):** likely a client-side network issue or a platform-wide incident. Check the status page at `status.yourplatform.com`.
- **Specific page/feature slow:** usually a heavy query or a missing cache.
- **API slow:** check response headers for `X-Processing-Time`. If > 2000ms, open a support ticket with the request ID.

### Step 2 — Check for active incidents

Always check `status.yourplatform.com` before investigating further. Many performance reports resolve automatically when an incident clears.

### Step 3 — Query and data volume

For AnalyticsHub and DataBridge Pro, large data volumes are the most common cause:

- Narrow the date range or add filters.
- Enable query caching.
- For DataBridge Pro: reduce `batch_size` and enable `exponential` retry policy.

---

## AnalyticsHub: Dashboard Timeout

**Symptom:** Dashboard fails to load; spinner runs indefinitely or "Query timed out" appears.

**Resolution:**

1. Edit the slowest widget and open the Query Profiler.
2. Look for full-table scans (no `WHERE` clause or no index hit).
3. Add a date filter: even `WHERE created_at > NOW() - INTERVAL '90 days'` dramatically reduces scan size.
4. Enable query caching: Data Sources → [source] → Enable Query Cache (5-minute TTL default).
5. If the query is optimised and still slow, raise query timeout limit: Settings → Data Sources → [source] → Timeout → increase to 300s.

---

## DataBridge Pro: Pipeline Throughput Degradation

**Symptom:** Records processed per second drops significantly; backlog grows.

**Resolution:**

1. Check Monitoring → Pipelines → [pipeline] → Throughput graph for when degradation started.
2. Common causes at this timestamp:
   - Source API started rate-limiting (look for `RATE_LIMIT_EXCEEDED` in logs)
   - Connector version was auto-updated (check connector changelog)
   - Network latency increase to source
3. Reduce `batch_size` to 100 temporarily — smaller batches are less likely to be rate-limited.
4. Switch `retry_policy` to `exponential` if not already set.

---

# Troubleshooting: Integration Issues

---

## Common Integration Errors

| Error | Integration | Cause | Fix |
| ------- | ------------ | ------- | ----- |
| `403 Forbidden` | Salesforce | OAuth token lacks `api` scope | Regenerate token with correct scopes |
| `404 Not Found` on valid endpoint | Any REST | API version mismatch | Confirm API version in connector config |
| Webhook not received | All | Endpoint not reachable from cloud | Whitelist platform IP ranges |
| `CHECKSUM_MISMATCH` | DataBridge Pro | Data corruption or wrong key | Verify encryption key; contact support |
| `INVALID_CONFIGURATION` | WorkflowEngine | Missing required field in action | Review action field mapping |

---

## Platform IP Ranges for Webhook Allowlisting

If your infrastructure requires inbound IP allowlisting, add the following ranges:

```
US-East:  203.0.113.0/24
US-West:  198.51.100.0/24
EU-West:  192.0.2.0/24
APAC:     203.0.114.0/24
```

These ranges are static and change only with 30-day advance notice on the status page.

---

## Salesforce Integration: Common Issues

1. **`refresh_token` scope missing** — the Connected App must have `api`, `refresh_token`, and `offline_access` scopes. Scopes cannot be added to an existing OAuth token; revoke and re-authorise.
2. **Field API name vs label** — integrations use API field names (e.g., `AccountNumber`), not display labels (e.g., "Account Number"). Use Salesforce's Object Manager to find the API name.
3. **Sandbox vs Production URLs** — confirm the integration is pointed to the correct Salesforce instance URL (`login.salesforce.com` for production, `test.salesforce.com` for sandbox).

---

## Snowflake Integration: Common Issues

1. **Warehouse suspended** — Snowflake auto-suspends idle warehouses. The first query after suspension includes a cold-start delay (5–60s). Enable auto-resume on the warehouse.
2. **Role permissions** — the Snowflake role used by the integration must have `USAGE` on the database and schema, and `SELECT` (or `INSERT`/`UPDATE` as needed) on the tables.
3. **IP allowlisting** — if Snowflake is configured with a network policy, add the platform IP ranges above.
