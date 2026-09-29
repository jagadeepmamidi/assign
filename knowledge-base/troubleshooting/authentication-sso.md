# Troubleshooting: Authentication & SSO

This guide covers the most common authentication and single sign-on issues across all products.

---

## Error Reference

| Error Code | Product(s) | Meaning | First Action |
| ------------ | ----------- | --------- | ------------- |
| `AUTH_TOKEN_EXPIRED` | All | Token TTL exceeded | Re-authenticate or rotate service token |
| `403 Forbidden: insufficient_scope` | All | Token lacks required permission scope | Review and update token scopes |
| `SAML_ASSERTION_EXPIRED` | SecureVault, CloudSync | Clock skew > 5 min between IDP and SP | Sync NTP on both systems |
| `AUDIENCE_MISMATCH` | SecureVault | Entity ID mismatch in SAML config | Correct Entity ID in IDP to match SP URL |
| `GROUP_NOT_MAPPED` | SecureVault, CloudSync | IDP group has no role mapping | Add group mapping in SSO settings |
| `SESSION_INVALID` | All | Concurrent session limit reached | Sign out other sessions or increase limit |
| `SSO_GROUP_NOT_FOUND` | CloudSync | Group name case mismatch | Verify exact group name including case |

---

## SSO Setup Checklist

Before opening a support ticket for SSO issues, confirm all of the following:

- [ ] SAML metadata XML is current (not expired)
- [ ] ACS URL in IDP matches exactly: `https://[product].yourdomain.com/sso/saml/callback`
- [ ] Entity ID in IDP matches exactly: `https://[product].yourdomain.com`
- [ ] At least one group mapping exists in the product SSO settings
- [ ] System clocks on IDP and service provider are synchronised (NTP)
- [ ] The user's IDP group is mapped to a product role
- [ ] Password login fallback is enabled for emergency admin access

---

## New Users Cannot Authenticate via SSO

**Symptom:** Existing users log in fine; new joiners get an error.

**Most common cause:** The new user's IDP group has not been mapped to a product role.

**Resolution:**

1. Log in to the product as an admin.
2. Navigate to Settings → SSO → Group Mapping.
3. Verify the user's primary IDP group appears in the list with a role assigned.
4. If the group is missing, add it with the appropriate role.
5. Ask the user to retry — no reprovisioning needed after mapping is added.

---

## Service Account Token Expired

**Symptom:** Automated jobs or API integrations return `AUTH_TOKEN_EXPIRED`.

**Resolution:**

1. Log in as an admin.
2. Navigate to Settings → API Keys → [service account].
3. Click Rotate to generate a new token.
4. Update the token in the downstream service (environment variable, secret manager, etc.).
5. Consider enabling auto-rotation: Settings → API Keys → [key] → Auto-rotate → Every 90 days.

---

## Concurrent Session Limit

**Symptom:** `SESSION_INVALID` error on second device login.

**Resolution:**

- Starter plan: 1 concurrent session per user.
- Professional+: configurable up to 10 concurrent sessions.
- Admin override: Settings → Security → Session Policy → Max Concurrent Sessions.

---

## Scope Errors (`403 Forbidden: insufficient_scope`)

Tokens are scoped at creation time. Common missing scopes:

| Product | Operation | Required Scope |
| --------- | ----------- | --------------- |
| DataBridge Pro | Write pipeline config | `pipelines:write` |
| DataBridge Pro | Read audit logs | `audit:read` |
| CloudSync | Manage permissions | `permissions:admin` |
| AnalyticsHub | Export data | `exports:read` |
| SecureVault | Rotate keys | `keys:rotate` |
| WorkflowEngine | Trigger workflow | `workflows:execute` |

To add scopes to an existing token: tokens are **immutable** — create a new token with the required scopes and revoke the old one.
