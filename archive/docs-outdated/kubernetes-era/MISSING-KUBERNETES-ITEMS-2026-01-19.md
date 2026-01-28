# What's MISSING in Our Kubernetes Setup

**Date:** January 19, 2026
**Source:** Official Open WebUI Documentation (https://docs.openwebui.com)

---

## 🔴 CRITICAL (Must Have)

| # | Missing Item | Purpose | Source |
|---|--------------|---------|--------|
| 1 | `kubernetes/open-webui-deployment.yaml` | Open WebUI itself not deployed! | Required for any deployment |
| 2 | `WEBUI_URL` env var | Required for OAuth callbacks | [SSO Docs](https://docs.openwebui.com/features/auth/sso/) |
| 3 | `ENABLE_OAUTH_SIGNUP=true` | Allow users to sign up via Microsoft | [SSO Docs](https://docs.openwebui.com/features/auth/sso/) |

---

## 🟠 IMPORTANT (For Entra ID Groups to Work)

| # | Missing Item | Purpose | Source |
|---|--------------|---------|--------|
| 4 | `ENABLE_OAUTH_GROUP_MANAGEMENT=true` | Sync Entra groups → Open WebUI groups | [SSO Docs](https://docs.openwebui.com/features/auth/sso/) |
| 5 | `ENABLE_OAUTH_GROUP_CREATION=true` | Auto-create groups from OAuth | [SSO Docs](https://docs.openwebui.com/features/auth/sso/) |
| 6 | `OAUTH_GROUP_CLAIM=groups` | Where to find groups in token | [SSO Docs](https://docs.openwebui.com/features/auth/sso/) |
| 7 | `ENABLE_OAUTH_ROLE_MANAGEMENT=true` | Manage admin/user roles from OAuth | [SSO Docs](https://docs.openwebui.com/features/auth/sso/) |
| 8 | `OAUTH_ADMIN_ROLES=MCP-Admin` | Which group = admin | [SSO Docs](https://docs.openwebui.com/features/auth/sso/) |

---

## 🟡 MEDIUM (For Production)

| # | Missing Item | Purpose | Source |
|---|--------------|---------|--------|
| 9 | `kubernetes/ingress.yaml` | External access with domain/SSL | Kubernetes best practice |
| 10 | `VECTOR_DB=pgvector` | Use PostgreSQL for RAG vectors | [Env Config Docs](https://docs.openwebui.com/getting-started/env-configuration) |
| 11 | `PGVECTOR_DB_URL` | Connection string for PGVector | [Env Config Docs](https://docs.openwebui.com/getting-started/env-configuration) |
| 12 | TLS/SSL Certificate | HTTPS for production | Security best practice |

---

## 🟢 NICE TO HAVE

| # | Missing Item | Purpose | Source |
|---|--------------|---------|--------|
| 13 | `ENABLE_DIRECT_CONNECTIONS=true` | Native MCP tool connections | [Features Docs](https://docs.openwebui.com/features/) |
| 14 | `ENABLE_CHANNELS=true` | Slack-style team channels | [Features Docs](https://docs.openwebui.com/features/) |
| 15 | `WEBHOOK_URL` | Notifications to Slack/Teams | [Webhook Docs](https://docs.openwebui.com/features/interface/webhooks/) |
| 16 | `ENABLE_CODE_EXECUTION=true` | Run code in chat | [Features Docs](https://docs.openwebui.com/features/) |

---

## 📋 QUICK SUMMARY

```
MISSING FILES:
├── kubernetes/open-webui-deployment.yaml  ❌
├── kubernetes/open-webui-service.yaml     ❌
└── kubernetes/ingress.yaml                ❌

ENV VARS STATUS (for Open WebUI):
├── WEBUI_URL                              ❌ (set at deploy time)
├── ENABLE_OAUTH_SIGNUP                    ✅ CONFIGURED
├── ENABLE_OAUTH_GROUP_MANAGEMENT          ✅ CONFIGURED
├── ENABLE_OAUTH_GROUP_CREATION            ✅ CONFIGURED
├── OAUTH_GROUP_CLAIM                      ✅ CONFIGURED
├── ENABLE_OAUTH_ROLE_MANAGEMENT           ✅ CONFIGURED (2026-01-21)
├── OAUTH_ADMIN_ROLES                      ✅ CONFIGURED (2026-01-21)
├── VECTOR_DB                              ✅ CONFIGURED (pgvector)
└── PGVECTOR_DB_URL                        ✅ CONFIGURED (same as DATABASE_URL)
```

---

## Totals

| Priority | Count |
|----------|-------|
| 🔴 Critical | 3 |
| 🟠 Important | 5 |
| 🟡 Medium | 4 |
| 🟢 Nice to have | 4 |
| **TOTAL** | **16** |

---

## Official Documentation Sources

1. **SSO/OAuth Configuration**
   https://docs.openwebui.com/features/auth/sso/

2. **Environment Variables**
   https://docs.openwebui.com/getting-started/env-configuration

3. **Features Overview**
   https://docs.openwebui.com/features/

4. **Webhooks**
   https://docs.openwebui.com/features/interface/webhooks/

5. **GitHub Discussion: Azure AD Groups**
   https://github.com/open-webui/open-webui/discussions/9275

6. **GitHub Discussion: OAuth Groups Permissioning**
   https://github.com/open-webui/open-webui/discussions/15727

---

## Notes

### Azure AD Groups Issue (From Docs)

> "Microsoft only has the option to send the group **IDs** (GUIDs), not display names. Open WebUI compares groups by **name**."

**Our Solution:** We built `mcp_entra_token_auth.py` with `GROUP_ID_MAPPING` config to map GUIDs → friendly names.

### What We Already Have ✅

- `kubernetes/mcp-proxy-deployment.yaml` - MCP Proxy gateway
- `kubernetes/postgresql-deployment.yaml` - PostgreSQL database
- `kubernetes/redis-deployment.yaml` - Redis for sessions
- `kubernetes/mcp-secrets.yaml` - API keys for MCP servers
- `kubernetes/secrets-template.yaml` - Template with Microsoft OAuth secrets
- `mcp-proxy/` - Full multi-tenant MCP implementation
- `open-webui-functions/mcp_entra_token_auth.py` - Entra ID token handler

---

*Generated: January 19, 2026*
