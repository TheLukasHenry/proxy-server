# Remaining Tasks for Lukas

**Date:** January 15, 2026
**Status:** Post-PR Review
**PR:** https://github.com/TheLukasHenry/ai_ui/pull/5

---

## BLOCKED - Needs Lukas Action

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | **Create Entra ID groups in Azure Portal** | ❌ Not done | MCP-GitHub, MCP-Filesystem, MCP-Admin |
| 2 | **Provide enterprise test accounts** | ❌ Not done | Personal Microsoft accounts don't have Entra groups |
| 3 | **API keys for remaining MCP servers** | ❌ Pending | See list below |

---

## MCP Servers Installation Status

### Currently Enabled (18 servers - 26%)

| Server | Status | Tools |
|--------|--------|-------|
| GitHub (local) | ✅ Working | 40 tools |
| Filesystem | ✅ Working | 14 tools |
| Atlassian | ✅ Working | SSE proxy |
| Linear | ✅ Configured | Needs API key |
| Notion | ✅ Configured | Needs API key |
| GitLab | ✅ Configured | Needs API key |
| Pulumi | ✅ Configured | Needs API key |
| HubSpot | ✅ Configured | Needs API key |
| Sentry | ✅ Configured | Needs API key |
| SonarQube | ✅ Configured | Needs API key |
| Asana | ✅ Configured | Needs API key |
| + 7 more | ✅ Configured | Various |

### TO INSTALL - Tier 1: HTTP (Quick Wins - Easiest)

These work **immediately** with Open WebUI - no proxy needed.

| # | Service | Endpoint | Auth | Priority |
|---|---------|----------|------|----------|
| 1 | **dbt** | Remote MCP (GA) | OAuth | HIGH |
| 2 | **Snowflake** | Snowflake-managed | PAT | HIGH |
| 3 | **GitHub Remote** | `https://api.githubcopilot.com/mcp/` | OAuth | MEDIUM |

### TO INSTALL - Tier 2: SSE (Needs mcpo proxy)

| # | Service | Endpoint | Auth | Priority |
|---|---------|----------|------|----------|
| 4 | **Slack** | Official (beta 2026) | OAuth | HIGH |

### TO INSTALL - Tier 3: stdio (Needs mcpo proxy)

#### Monitoring & Observability
| # | Service | Package | Auth | Priority |
|---|---------|---------|------|----------|
| 5 | **Datadog** | shelfio/datadog-mcp | API Key | HIGH |
| 6 | **Grafana** | Grafana Cloud MCP | API Key | HIGH |
| 7 | **Snyk** | Official MCP | API Key | MEDIUM |

#### Project Management
| # | Service | Package | Auth | Priority |
|---|---------|---------|------|----------|
| 8 | **ClickUp** | taazkareem/clickup-mcp-server | API Key | MEDIUM |
| 9 | **Trello** | v4lheru-trello | API Key | LOW |
| 10 | **Airtable** | Composio MCP | API Key | LOW |
| 11 | **Monday.com** | Community | API Key | LOW |

#### Cloud Platforms
| # | Service | Package | Auth | Priority |
|---|---------|---------|------|----------|
| 12 | **Terraform** | severity1-terraform-cloud | API Key | MEDIUM |
| 13 | **Kubernetes** | Community packages | Kubeconfig | MEDIUM |
| 14 | **Docker** | Community packages | Daemon | LOW |

#### Databases
| # | Service | Package | Auth | Priority |
|---|---------|---------|------|----------|
| 15 | **PostgreSQL** | modelcontextprotocol-postgres | Connection | HIGH |
| 16 | **MongoDB** | Community packages | Connection | MEDIUM |
| 17 | **MySQL** | legion-mcp (universal) | Connection | LOW |
| 18 | **BigQuery** | LucasHild/mcp-server-bigquery | OAuth | MEDIUM |

#### File Storage
| # | Service | Package | Auth | Priority |
|---|---------|---------|------|----------|
| 19 | **Google Drive** | modelcontextprotocol-gdrive | OAuth | HIGH |
| 20 | **OneDrive** | microsoft/files-mcp-server | OAuth | HIGH |
| 21 | **SharePoint** | microsoft/files-mcp-server | OAuth | HIGH |

#### Communication
| # | Service | Package | Auth | Priority |
|---|---------|---------|------|----------|
| 22 | **Microsoft Teams** | Teams AI Library (preview) | OAuth | HIGH |
| 23 | **Zoom** | Community | OAuth | LOW |

#### Development & Code
| # | Service | Package | Auth | Priority |
|---|---------|---------|------|----------|
| 24 | **Git** | cyanheads/git-mcp-server | N/A | MEDIUM |
| 25 | **Bitbucket** | Composio MCP | API Key | LOW |

### TO INSTALL - Tier 4: API-Only (Need to Build MCP)

These have REST APIs but no MCP server yet.

| # | Service | API | Auth | Effort |
|---|---------|-----|------|--------|
| 26 | **Salesforce** | REST API | OAuth | HIGH |
| 27 | **ProductBoard** | REST API | API Key | MEDIUM |
| 28 | **New Relic** | GraphQL API | API Key | MEDIUM |
| 29 | **Splunk** | REST API | API Key | MEDIUM |
| 30 | **Fivetran** | REST API | API Key | LOW |
| 31 | **Jenkins** | REST API | API Key | MEDIUM |
| 32 | **Segment** | REST API | API Key | MEDIUM |

---

## Implementation Priority Matrix

### This Week (Quick Wins)

| Priority | Service | Why |
|----------|---------|-----|
| 1 | **Datadog** | Monitoring, Lukas mentioned |
| 2 | **Grafana** | Monitoring, Lukas mentioned |
| 3 | **Snyk** | Security, Lukas mentioned |
| 4 | **dbt** | Data transformation, native HTTP |
| 5 | **Snowflake** | Data warehouse, native HTTP |

### Next Week (With mcpo Proxy)

| Priority | Service | Why |
|----------|---------|-----|
| 6 | **Google Drive** | File storage |
| 7 | **OneDrive/SharePoint** | Microsoft integration |
| 8 | **Microsoft Teams** | Communication |
| 9 | **PostgreSQL MCP** | Database access |
| 10 | **Slack** | Wait for GA or use proxy |

---

## Ready To Do - Dev Team

| # | Task | Effort |
|---|------|--------|
| 1 | **Implement groups overage handling** (Graph API) | Medium |
| 2 | **Fix production CORS** (change from `*`) | 30 min |
| 3 | **Add database migration scripts** | 1-2 hours |
| 4 | **Fix K8s MCP Proxy connectivity** | 1 hour |

---

## Deferred (Per Lukas's Request)

| # | Task | Notes |
|---|------|-------|
| 1 | Observability/logging dashboards | "Do after usefulness" |
| 2 | Structured logging | Later |
| 3 | Usage metrics for leadership | Later |

---

## Progress Summary

| Category | Status |
|----------|--------|
| **MCP Servers** | 18/70 (26%) enabled |
| **Tier 1 HTTP** | 8/12 configured |
| **Tier 2 SSE** | 2/8 configured |
| **Tier 3 stdio** | 8/25+ configured |
| **Authentication** | 95% done (needs Entra groups) |
| **Infrastructure** | 100% complete |

---

## API Keys Needed from Lukas

| Service | Required | Notes |
|---------|----------|-------|
| Datadog | API Key + App Key | Monitoring |
| Grafana | API Key | Monitoring |
| Snyk | API Token | Security scanning |
| dbt | OAuth credentials | Data transformation |
| Snowflake | PAT | Data warehouse |
| Slack | OAuth (when GA) | Communication |
| Google Drive | OAuth credentials | File storage |
| OneDrive/SharePoint | OAuth credentials | Microsoft files |
| ClickUp | API Key | Project management |
| Terraform | API Token | IaC |

---

## Blocking Everything

```
┌─────────────────────────────────────────────┐
│  LUKAS MUST DO THESE IN AZURE PORTAL:       │
│                                             │
│  1. Create groups:                          │
│     - MCP-GitHub                            │
│     - MCP-Filesystem                        │
│     - MCP-Admin                             │
│     - Tenant-Google, Tenant-AcmeCorp, etc.  │
│                                             │
│  2. Assign employees to groups              │
│                                             │
│  3. Configure token claims to include       │
│     "groups" in JWT                         │
│                                             │
│  Until this is done, we can't test          │
│  multi-tenant access control!               │
└─────────────────────────────────────────────┘
```

---

*Generated: January 15, 2026*
