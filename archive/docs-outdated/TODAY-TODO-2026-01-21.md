# TODAY TODO - January 21, 2026

**For Lukas:** What's NOT implemented yet based on all documentation analysis.

---

## STATUS SUMMARY

| Category | Implemented | Not Implemented |
|----------|-------------|-----------------|
| **Single Proxy Demo** | ✅ 100% | - |
| **OAuth Settings** | ✅ 100% | - |
| **Arguments Docs** | ✅ 100% | - |
| **Kubernetes Files** | ⚠️ 80% | Missing Open WebUI deployment |
| **Azure Portal Setup** | ❌ 0% | Lukas must do |
| **API Keys** | ❌ ~20% | Most missing |
| **MCP Servers** | ⚠️ 26% | 18/70 configured |

---

## ✅ ALREADY DONE (No Action Needed)

### Single Proxy Demo Files
- [x] `mcp-proxy/config/mcp-servers.json` - Server definitions
- [x] `mcp-proxy/scripts/seed_mcp_servers.py` - Database seeder
- [x] `mcp-proxy/scripts/generate_webui_tools.py` - Export generator
- [x] `mcp-proxy/scripts/demo_single_proxy.py` - All-in-one demo
- [x] `kubernetes/init-mcp-servers-job.yaml` - Deploy-time init job

### OAuth Settings (in values-production.yaml)
- [x] `ENABLE_OAUTH_SIGNUP=true`
- [x] `ENABLE_OAUTH_GROUP_MANAGEMENT=true`
- [x] `ENABLE_OAUTH_GROUP_CREATION=true`
- [x] `OAUTH_GROUP_CLAIM=groups`
- [x] `ENABLE_OAUTH_ROLE_MANAGEMENT=true`
- [x] `OAUTH_ADMIN_ROLES=MCP-Admin`

### Documentation
- [x] `docs/ARGUMENTS-AGAINST-REMOTE-APPROACH.md` - Arguments for meetings
- [x] `docs/OPTIONAL-ARGUMENTS-SUMMARY.md` - Open WebUI optional arguments
- [x] `docs/DEPLOYMENT-READINESS-2026-01-19.md` - Deployment status
- [x] `docs/MISSING-KUBERNETES-ITEMS-2026-01-19.md` - Gap analysis

### Security
- [x] `.env` is gitignored (no secrets in GitHub)
- [x] `kubernetes/secrets.yaml` is gitignored
- [x] Only placeholder templates in git

---

## ❌ NOT IMPLEMENTED - LUKAS MUST DO IN AZURE

### 1. Create Entra ID Groups in Azure Portal
**Location:** portal.azure.com → Microsoft Entra ID → Groups

| Group Name | Purpose | Priority |
|------------|---------|----------|
| `MCP-Admin` | Full access to ALL MCP servers | HIGH |
| `MCP-GitHub` | Access to GitHub MCP | HIGH |
| `MCP-Filesystem` | Access to Filesystem MCP | HIGH |
| `MCP-Atlassian` | Access to Atlassian MCP | MEDIUM |
| `Tenant-Google` | Multi-server access for Google employees | MEDIUM |
| `Tenant-Microsoft` | Multi-server access for Microsoft employees | MEDIUM |
| `Tenant-AcmeCorp` | Multi-server access for AcmeCorp employees | MEDIUM |

**Status:** ❌ NOT DONE

---

### 2. Configure Token Claims
**Location:** Azure Portal → App Registrations → Your App → Token Configuration

Steps:
1. Click "Add groups claim"
2. Select:
   - ✅ Security groups
   - ✅ Groups assigned to the application
3. For ID token & Access token:
   - ✅ Emit groups as role claims
4. Save

**Status:** ❌ NOT DONE

---

### 3. Provide API Keys
**Location:** `kubernetes/mcp-secrets.yaml` or `.env`

| Service | Key Name | Get From | Priority |
|---------|----------|----------|----------|
| Linear | `LINEAR_API_KEY` | linear.app/settings/api | HIGH |
| Notion | `NOTION_API_KEY` | notion.so/my-integrations | HIGH |
| Datadog | `DATADOG_API_KEY` | app.datadoghq.com | HIGH |
| Grafana | `GRAFANA_API_KEY` | grafana.com | HIGH |
| Snyk | `SNYK_TOKEN` | snyk.io | MEDIUM |
| HubSpot | `HUBSPOT_API_KEY` | developers.hubspot.com | MEDIUM |
| GitLab | `GITLAB_TOKEN` | gitlab.com | MEDIUM |
| Sentry | `SENTRY_AUTH_TOKEN` | sentry.io | MEDIUM |

**Status:** ❌ MOST NOT PROVIDED

---

### 4. Create Enterprise Test Accounts
Personal Microsoft accounts don't have Entra groups.

**Need:** Enterprise accounts in Lukas's Azure AD tenant

**Status:** ❌ NOT DONE

---

## ❌ NOT IMPLEMENTED - CODE/CONFIG WORK

### High Priority

| # | Item | File/Location | Notes |
|---|------|---------------|-------|
| 1 | **Open WebUI Deployment** | `kubernetes/open-webui-deployment.yaml` | ❌ MISSING FILE - Using Helm instead? |
| 2 | **WEBUI_URL env var** | Set at deploy time | Needs actual domain |
| 3 | **Azure Container Registry** | Azure Portal | Local images won't work on AKS |
| 4 | **Fix image references** | `kubernetes/*.yaml` | Change from `mcp-proxy:local` to ACR URL |

### Medium Priority

| # | Item | File/Location | Notes |
|---|------|---------------|-------|
| 5 | **Ingress configuration** | `kubernetes/ingress.yaml` | ❌ MISSING FILE |
| 6 | **TLS/SSL Certificate** | cert-manager or Azure | For HTTPS |
| 7 | **Scale mcpo-sse** | `kubectl scale` | Currently 0/0, needs 1 for Atlassian |
| 8 | **Groups overage handling** | `mcp-proxy/auth.py` | For tenants with >150 groups |
| 9 | **Fix production CORS** | `mcp-proxy/main.py` | Change from `*` to specific origins |

### Low Priority

| # | Item | File/Location | Notes |
|---|------|---------------|-------|
| 10 | **Database migration scripts** | `mcp-proxy/migrations/` | For production deploys |
| 11 | **More MCP servers** | `mcp-proxy/config/mcp-servers.json` | Only 18/70 (26%) configured |
| 12 | **Observability dashboards** | Grafana | Lukas said "do after usefulness" |

---

## BLOCKING EVERYTHING

```
┌─────────────────────────────────────────────────────────────────┐
│  LUKAS MUST DO THESE BEFORE PRODUCTION DEPLOYMENT:              │
│                                                                  │
│  1. Create Entra ID groups in Azure Portal                      │
│  2. Configure token claims to include groups                    │
│  3. Provide API keys for MCP servers                            │
│  4. Set up Azure Container Registry (for AKS)                   │
│                                                                  │
│  WITHOUT THESE, MULTI-TENANT AUTH CANNOT BE TESTED!             │
└─────────────────────────────────────────────────────────────────┘
```

---

## QUICK WIN - LOCAL DEMO WORKS NOW

The local demo with Docker Compose is ready:

```bash
# Windows
.\scripts\start-local-demo.ps1

# Linux/Mac
./scripts/start-local-demo.sh
```

This proves the single proxy approach works!

---

## SINGLE PROXY ARGUMENT (Ready to Use)

When someone asks "why not use remote MCP servers directly?", Lukas can say:

> "With single proxy, I edit ONE config file (`mcp-servers.json`), run `kubectl apply`, and:
> - Database permissions are configured automatically
> - Open WebUI tool configuration is set up automatically
> - All requests go through ONE audit log
> - ONE place to debug permission issues
>
> With remote approach, I have to:
> 1. Configure Open WebUI tool permissions
> 2. Configure Azure Key Vault access
> 3. Keep them in sync
> 4. Debug across multiple systems
>
> Single proxy = ONE source of truth."

Full arguments: `docs/ARGUMENTS-AGAINST-REMOTE-APPROACH.md`

---

## SUMMARY FOR TONIGHT

| Task | Owner | Priority |
|------|-------|----------|
| Create Entra ID groups | Lukas | 🔴 HIGH |
| Configure token claims | Lukas | 🔴 HIGH |
| Get API keys for Datadog/Grafana/Snyk | Lukas | 🟠 MEDIUM |
| Set up Azure Container Registry | Lukas | 🟡 For AKS deploy |
| Test local demo works | Dev Team | ✅ DONE |

---

*Generated: January 21, 2026*
*Based on analysis of all .md files in docs/*
