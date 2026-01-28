# PRD: MCP Servers Multi-Tenant Deployment

## Introduction

Deploy additional MCP servers to the Hetzner infrastructure with proper API key management and multi-tenancy support. This enables team members to access specific tools based on group membership, with all authentication flowing through the MCP Proxy gateway.

## Goals

- Deploy proxy-based MCP servers (Atlassian, ClickUp, Trello, SonarQube) with secure API keys
- Add non-proxy MCP servers (Linear OAuth, GitHub, Notion) to Open WebUI
- Implement API gateway multi-tenancy with group-based access control
- Complete Microsoft OAuth configuration (add Azure callback URL)
- Create shared .env configuration for team development

## API Keys Provided

### Proxy MCP Servers (Routed through MCP Proxy)

| Server | Credentials |
|--------|-------------|
| **Atlassian** | Org ID, User email, Atlassian URL (see .env) |
| **ClickUp** | API Token (see .env) |
| **Trello** | API Key, Secret, Token (see .env) |
| **SonarQube** | Token (see .env) |

### Non-Proxy MCP Servers (Direct in Open WebUI)

| Server | Status |
|--------|--------|
| **GitHub** | Token available (see .env) |
| **Linear** | Needs OAuth setup (ask Lukas) |
| **Notion** | Needs API key (ask Lukas) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HETZNER DEPLOYMENT                           │
│                                                                  │
│  ┌──────────────┐     ┌──────────────────────────────────────┐  │
│  │   Traefik    │────▶│           MCP Proxy                  │  │
│  │   (OIDC)     │     │  ┌──────────┬──────────┬──────────┐ │  │
│  └──────────────┘     │  │Atlassian │ ClickUp  │  Trello  │ │  │
│         │             │  ├──────────┼──────────┼──────────┤ │  │
│         ▼             │  │SonarQube │ GitHub   │Filesystem│ │  │
│  ┌──────────────┐     │  └──────────┴──────────┴──────────┘ │  │
│  │  Open WebUI  │────▶│     Multi-tenant access control      │  │
│  │  (+ Linear,  │     └──────────────────────────────────────┘  │
│  │   Notion)    │              │                                │
│  └──────────────┘              ▼                                │
│         │             ┌──────────────┐                          │
│         └────────────▶│  PostgreSQL  │ (user groups, perms)     │
│                       └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## User Stories

### US-001: Add Atlassian MCP Server
**Description:** As a user, I want to access Atlassian (Jira/Confluence) tools through the MCP Proxy.

**Acceptance Criteria:**
- [ ] Atlassian credentials added to `.env` on Hetzner
- [ ] Atlassian server enabled in `tenants.py`
- [ ] Tools appear in `/openapi.json`: `atlassian_*`
- [ ] Test: Create/list Jira issues via MCP Proxy
- [ ] Group mapping: Assign to appropriate user groups

### US-002: Add ClickUp MCP Server
**Description:** As a user, I want to access ClickUp project management tools.

**Acceptance Criteria:**
- [ ] ClickUp API token added to `.env`
- [ ] ClickUp server enabled in `tenants.py`
- [ ] Tools appear: `clickup_*` (tasks, lists, spaces)
- [ ] Test: List workspaces/tasks via MCP Proxy
- [ ] Group mapping configured

### US-003: Add Trello MCP Server
**Description:** As a user, I want to access Trello boards and cards.

**Acceptance Criteria:**
- [ ] Trello API key, secret, token added to `.env`
- [ ] Trello server enabled in `tenants.py`
- [ ] Tools appear: `trello_*` (boards, cards, lists)
- [ ] Test: List boards via MCP Proxy
- [ ] Group mapping configured

### US-004: Add SonarQube MCP Server
**Description:** As a user, I want to access SonarQube code quality tools.

**Acceptance Criteria:**
- [ ] SonarQube token added to `.env`
- [ ] SonarQube server enabled in `tenants.py`
- [ ] Tools appear: `sonarqube_*` (projects, issues, metrics)
- [ ] Test: List projects via MCP Proxy
- [ ] Group mapping configured

### US-005: Configure Multi-Tenant Access Control
**Description:** As an admin, I want group-based access so users only see authorized tools.

**Acceptance Criteria:**
- [ ] `group_tenant_mapping` table populated with server-group mappings
- [ ] Users in "developers" group see: Atlassian, GitHub, SonarQube
- [ ] Users in "project-managers" group see: ClickUp, Trello
- [ ] Users in "all-tools" group see everything
- [ ] Unauthorized tool calls return 403 Forbidden
- [ ] Admin Portal can modify mappings

### US-006: Complete Microsoft OAuth Setup
**Description:** As a user, I want to log in with Microsoft account on Hetzner.

**Acceptance Criteria:**
- [ ] Add callback URL in Azure Portal: `https://ai-ui.coolestdomain.win/oauth/microsoft/callback`
- [ ] Test Microsoft login on Hetzner deployment
- [ ] User created with correct email
- [ ] Groups populated (if using Entra ID groups)

### US-007: Add Non-Proxy MCP Servers to Open WebUI
**Description:** As a user, I want Linear and Notion tools available directly in Open WebUI.

**Acceptance Criteria:**
- [ ] Get Linear OAuth credentials from Lukas
- [ ] Get Notion API key from Lukas
- [ ] Configure in Open WebUI Admin > Tools > External Connections
- [ ] Test: Linear issues, Notion pages accessible
- [ ] Document which servers are proxy vs direct

### US-008: Create Shared Team .env
**Description:** As a developer, I want a shared .env so the team can run locally with same config.

**Acceptance Criteria:**
- [ ] Create `.env.team-shared` with all API keys (excluding secrets in .gitignore)
- [ ] Document in README which values to fill
- [ ] Both local and Hetzner can use same credentials
- [ ] Share securely with Lukas (not via git)

## Functional Requirements

- **FR-1:** Each MCP server must have environment variables for API keys (not hardcoded)
- **FR-2:** `tenants.py` must enable/disable servers based on available credentials
- **FR-3:** Multi-tenant access control must check `group_tenant_mapping` for every tool call
- **FR-4:** API keys must be stored in `.env` files, never committed to git
- **FR-5:** Non-proxy MCP servers (Linear, Notion) configured directly in Open WebUI
- **FR-6:** All tool calls must be logged with user email for audit

## Non-Goals

- Setting up CI/CD pipelines (future)
- Automatic API key rotation (future)
- Usage quotas per user/group (future)
- Billing/metering integration (future)

## Technical Considerations

### Environment Variables to Add

```bash
# Atlassian
ATLASSIAN_ORG_ID=baadf1ba-f964-4b21-afb5-1a0134bccacb
ATLASSIAN_API_KEY=ATCTT3xFfGN0...
ATLASSIAN_URL=https://lherajt.atlassian.net/
ATLASSIAN_USER=lherajt@gmail.com

# ClickUp
CLICKUP_API_TOKEN=pk_192121530_9GNCQSXNHLHJB84FYGMH8KHMA8SIA33Q

# Trello
TRELLO_API_KEY=44d2785269016755bff7deb928de4dfa
TRELLO_API_SECRET=ce3509e67640095134486644625b6d53c...
TRELLO_API_TOKEN=ATTA650es5dac4doac7e...

# SonarQube
SONARQUBE_TOKEN=a2d0e7d546ea4560ce3bde7af5f4bbb45e1fcd9c

# GitHub (already configured)
GITHUB_TOKEN=your-github-token

# Notion (need from Lukas)
NOTION_API_KEY=

# Linear (OAuth - need from Lukas)
LINEAR_CLIENT_ID=
LINEAR_CLIENT_SECRET=
```

### Database Seeding Script Update

```sql
-- Add server mappings for new MCP servers
INSERT INTO group_tenant_mapping (group_name, tenant_id, created_at) VALUES
  ('developers', 'atlassian', NOW()),
  ('developers', 'github', NOW()),
  ('developers', 'sonarqube', NOW()),
  ('project-managers', 'clickup', NOW()),
  ('project-managers', 'trello', NOW()),
  ('all-tools', 'atlassian', NOW()),
  ('all-tools', 'clickup', NOW()),
  ('all-tools', 'trello', NOW()),
  ('all-tools', 'sonarqube', NOW()),
  ('all-tools', 'github', NOW()),
  ('all-tools', 'filesystem', NOW())
ON CONFLICT DO NOTHING;
```

## Success Metrics

- All 4 new MCP servers (Atlassian, ClickUp, Trello, SonarQube) respond to tool calls
- Multi-tenant filtering works (users only see authorized tools)
- Microsoft OAuth works on Hetzner with callback URL
- Team can run local environment with shared credentials
- No API keys exposed in logs or error messages

## Open Questions

1. **Linear OAuth:** Does Lukas have Linear OAuth credentials, or do we need to set up an OAuth app?
2. **Notion API:** Does Lukas have a Notion integration/API key?
3. **Group Structure:** What user groups should exist? (developers, project-managers, admins, etc.)
4. **Default Access:** Should new users get any tools by default, or require explicit group membership?

## Implementation Order

1. Add environment variables to Hetzner `.env`
2. Update `tenants.py` to enable new servers
3. Redeploy MCP Proxy: `docker compose restart mcp-proxy`
4. Test each server individually via curl
5. Update database with group mappings
6. Add Azure callback URL for Microsoft OAuth
7. Test multi-tenant access with different users
8. Get Linear/Notion credentials from Lukas
9. Configure non-proxy servers in Open WebUI
10. Create and share team .env file

---

*PRD Created: January 27, 2026*
*Author: Claude (with Jacint)*
*Status: Ready for Implementation*
