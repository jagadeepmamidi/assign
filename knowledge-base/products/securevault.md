# SecureVault — Product Reference

## Overview

SecureVault is an enterprise secrets and key management platform. It provides centralised storage for API keys, credentials, certificates, and encryption keys, with audit logging, role-based access control, and integrations with major cloud providers and CI/CD pipelines.

**Current stable version:** 2.6.0  
**Previous stable version:** 2.5.3

---

## Core Modules

### Authentication

SecureVault supports multiple authentication methods:

- **Username + password** with MFA (TOTP or hardware key)
- **SSO via SAML 2.0** (Okta, Azure AD, Google Workspace, Ping Identity)
- **Machine-to-machine:** service account tokens with scoped permissions

Token expiry defaults: user tokens 8 hours, service tokens 90 days.  
`AUTH_TOKEN_EXPIRED` errors indicate the token has exceeded its TTL — re-authenticate or rotate the service token.

### Encryption

All secrets are encrypted at rest using AES-256-GCM. In-transit encryption uses TLS 1.3 minimum.

- Customer-managed keys (CMK) available on Business and Enterprise plans.
- Key rotation: automatic 90-day rotation (configurable). Manual rotation available anytime.
- Hardware Security Module (HSM) backing available for Enterprise.

### Audit Logs

Immutable, tamper-evident log of all read, write, delete, and permission change events.

- Retention: 90 days (Starter/Professional), 1 year (Business), 7 years (Enterprise).
- Export: JSON or CSV, via UI or API.
- SIEM integration: Splunk, Datadog, and generic syslog supported.
- Searching logs: Audit → Logs → filter by user, resource, action, or time range.

### Key Management

Create, rotate, and retire encryption keys.

- **Key states:** `active`, `pending_rotation`, `retired`, `destroyed`
- Keys in `pending_rotation` state are still valid for decryption but cannot be used for new encryption.
- `CHECKSUM_MISMATCH` errors during decryption indicate the data was encrypted with a key that has since been destroyed. Contact support immediately — recovery may be possible within the 30-day soft-delete window.

### SSO Configuration

1. Obtain the SAML metadata XML from your IDP.
2. Upload in Settings → SSO → Configure → Upload Metadata.
3. Set the Assertion Consumer Service (ACS) URL to `https://vault.yourdomain.com/sso/saml/callback`.
4. Map IDP group attributes to SecureVault roles in Settings → SSO → Group Mapping.

**Common SSO errors:**

- `SAML_ASSERTION_EXPIRED` — clock skew between IDP and SecureVault exceeds 5 minutes. Sync NTP on both.
- `AUDIENCE_MISMATCH` — the Entity ID in the IDP config does not match `https://vault.yourdomain.com`.
- `GROUP_NOT_MAPPED` — IDP group has no corresponding SecureVault role assigned.

---

## Common Support Scenarios

### Users cannot log in after SSO migration

1. Verify ACS URL and Entity ID are correct in the IDP.
2. Check for clock skew: `SAML_ASSERTION_EXPIRED` in audit logs.
3. Confirm group mappings exist for all IDP groups users belong to.
4. Temporarily allow password login for admins: Settings → SSO → Fallback → Enable Password Login (Emergency).

### Secret rotation breaking downstream services

1. SecureVault supports **dual-active rotation**: the old and new secret are both valid during a transition window (default 24 hours).
2. Enable dual-active rotation: Key Management → [secret] → Rotate → Advanced → Enable Dual-Active.
3. Update downstream services to fetch the new secret during the window.
4. After confirmation, retire the old version.

### Audit log shows unauthorised access attempts

1. Identify the source IP and user from the log entry.
2. If the IP is unrecognised, immediately revoke the affected token: API Keys → [key] → Revoke.
3. Enable IP allowlisting: Settings → Security → IP Allowlist.
4. Review and tighten permissions for the affected role.
