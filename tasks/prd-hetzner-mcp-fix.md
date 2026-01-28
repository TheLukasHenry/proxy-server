# PRD: Fix Hetzner MCP Proxy - Full Parity with Local

## Introduction

Lukas tested the live Hetzner deployment and found that tools connect and attempt to call correctly, but return 500 errors. The root causes are: expired API tokens (GitHub, Trello), missing auth configuration (Open WebUI sends no JWT to MCP Proxy), split docker-compose files causing config drift, and missing MCP server containers (Excel, Dashboard). This PRD covers all fixes needed to achieve full local-to-Hetzner parity.

## Goals

- Fix all 500 errors on tool calls (GitHub, Trello, SonarQube)
- Unify Hetzner docker-compose into a single file with all services
- Establish proper auth flow (Open WebUI -> JWT -> MCP Proxy)
- Ensure all local MCP proxy tools are available on Hetzner live
- Disable servers that have no API keys to prevent phantom tool errors
- Add WEBUI_SECRET_KEY to MCP Proxy for JWT validation

## Current State (Scan Results)

### Working
- ClickUp: 200 OK (returns Lukas's workspace)
- Filesystem: 200 OK (file listing works)

### Failing
- GitHub: **500** -> upstream returns `401 Bad credentials` (PAT expired)
- Trello: **500** -> upstream returns `401` (API token invalid/expired)
- SonarQube: **500** -> upstream returns error (needs SONARQUBE_ORG)
- Linear, Notion, HubSpot, Pulumi, GitLab, Sentry, GitHub-Remote: **Enabled in tenants.py but NO containers or API keys on Hetzner**
- Excel Creator, Dashboard: **Enabled in tenants.py but NO containers on Hetzner**
- Asana: **Points to mcpo-sse:8011 which doesn't exist on Hetzner**

### Auth Issues
- Open WebUI `TOOL_SERVER_CONNECTIONS` uses `auth_type: "none"` -> sends NO JWT
- MCP Proxy has `WEBUI_SECRET_KEY` NOT in its env -> can't validate JWT even if sent
- `API_GATEWAY_MODE=true` in running container but no gateway sets X-User-Email
- Result: All tool calls are anonymous (no user identity)

### Config Drift
- Two compose files on Hetzner: `docker-compose.yml` (core services) and `docker-compose.hetzner.yml` (MCP servers)
- MCP Proxy was built from hetzner compose (has API_GATEWAY_MODE=true, all API keys)
- Open WebUI was built from main compose (has auth_type: "none")
- Port 8000 not mapped to host for mcp-proxy (only accessible via Docker internal network)

## User Stories

### US-001: Unify Hetzner docker-compose into single file
**Description:** As a developer, I need one docker-compose.yml on Hetzner that includes ALL services so there's no config drift.

**Acceptance Criteria:**
- [ ] Single docker-compose.yml with: open-webui, mcp-proxy, auth-service, admin-portal, postgres, redis, mcp-filesystem, mcp-github, mcp-clickup, mcp-trello, mcp-sonarqube
- [ ] All API keys passed from .env to mcp-proxy environment
- [ ] MCP Proxy port 8000 accessible from host for debugging
- [ ] Open WebUI on port 3100

### US-002: Fix auth flow - Open WebUI sends JWT to MCP Proxy
**Description:** As a user, I need my identity to be recognized when calling MCP tools so access control works.

**Acceptance Criteria:**
- [ ] Open WebUI `TOOL_SERVER_CONNECTIONS` uses `auth_type: "session"` (sends JWT)
- [ ] MCP Proxy has `WEBUI_SECRET_KEY` matching Open WebUI's secret
- [ ] MCP Proxy `API_GATEWAY_MODE=false` (uses JWT, not gateway headers)
- [ ] User email extracted from JWT via DB lookup (Open WebUI JWT has user_id, not email)
- [ ] Access control works end-to-end (user identified, groups checked from DB)

### US-003: Fix GitHub MCP server (expired PAT)
**Description:** As a user, I need GitHub tools to work for searching repos, viewing issues, etc.

**Acceptance Criteria:**
- [ ] Document that GITHUB_TOKEN in .env needs a valid PAT from Lukas
- [ ] GitHub container uses the PAT correctly via GITHUB_PERSONAL_ACCESS_TOKEN env var
- [ ] After token refresh: `/github/get_me` returns valid user info

### US-004: Fix Trello MCP server (expired token)
**Description:** As a user, I need Trello tools to work for viewing boards and cards.

**Acceptance Criteria:**
- [ ] Document that TRELLO_API_KEY and TRELLO_API_TOKEN in .env need valid values from Lukas
- [ ] Trello container receives both TRELLO_API_KEY and TRELLO_TOKEN env vars
- [ ] After token refresh: `/trello/list_boards` returns boards

### US-005: Fix SonarQube MCP server (missing org config)
**Description:** As a user, I need SonarQube tools to work for code quality analysis.

**Acceptance Criteria:**
- [ ] Add SONARQUBE_ORG env var to SonarQube container
- [ ] SonarQube container receives SONARQUBE_TOKEN, SONARQUBE_URL, SONARQUBE_ORG
- [ ] After config fix: `/sonarqube/search_projects` returns results or clear error

### US-006: Disable servers without API keys on Hetzner
**Description:** As a user, I should not see tools for servers that have no API keys configured, because calling them produces 500 errors.

**Acceptance Criteria:**
- [ ] Servers with auto-enable logic (e.g., `enabled=bool(os.getenv("KEY"))`) correctly disable when key is absent
- [ ] Verify: linear, notion, hubspot, pulumi, gitlab, sentry are disabled (no API keys in .env)
- [ ] Verify: github-remote is disabled (uses different endpoint than local github)
- [ ] After /refresh, only working tools appear in OpenAPI spec

### US-007: Add Excel Creator and Dashboard containers to Hetzner
**Description:** As a user, I need Excel and Dashboard tools available on Hetzner (they work locally).

**Acceptance Criteria:**
- [ ] mcp-excel container added to Hetzner docker-compose
- [ ] mcp-dashboard container added to Hetzner docker-compose
- [ ] Both containers accessible from mcp-proxy via internal network
- [ ] `/excel/create_excel` and `/dashboard/create_dashboard` return 200

### US-008: Sync local code changes to Hetzner
**Description:** As a developer, the local mcp-proxy code (with DB group lookup fix) needs to be on Hetzner.

**Acceptance Criteria:**
- [ ] mcp-proxy/db.py with `get_user_groups()` function deployed
- [ ] mcp-proxy/tenants.py with DB group lookup in `user_has_tenant_access_async()` deployed
- [ ] mcp-proxy rebuilt with `--no-cache` on Hetzner
- [ ] Verify: tool calls with user header correctly look up groups from DB

## Functional Requirements

- FR-1: Unify all Hetzner services into a single docker-compose.yml
- FR-2: Open WebUI must use `auth_type: "session"` for MCP Proxy tool server connection
- FR-3: MCP Proxy must have `WEBUI_SECRET_KEY` env var matching Open WebUI's secret
- FR-4: MCP Proxy must use `API_GATEWAY_MODE=false` for JWT-based auth
- FR-5: All MCP server API keys from .env must be passed to mcp-proxy container
- FR-6: Servers without API keys must be auto-disabled (enabled=false)
- FR-7: Excel Creator and Dashboard containers must be added to Hetzner deployment
- FR-8: MCP Proxy must have port 8000 mapped to host for debugging
- FR-9: After deployment, `POST /refresh` must load all working tools
- FR-10: Document which tokens need refresh from Lukas (GitHub PAT, Trello token)

## Non-Goals

- Not migrating to Traefik/SSL on this iteration (direct port access for now)
- Not adding new MCP servers beyond what exists locally
- Not changing the auth architecture (keep JWT + DB lookup approach)
- Not fixing Microsoft OAuth login (separate task)

## Technical Considerations

- The MCP Proxy already has DB group lookup code (added in previous session)
- Auto-enable logic in tenants.py: `enabled=bool(os.getenv("KEY"))` works for most servers
- Excel and Dashboard are custom containers built from `./mcp-servers/excel-creator` and `./mcp-servers/dashboard`
- SonarQube uses `@wallacewen/sonarqube-mcp-server` which needs SONARQUBE_ORG for SonarCloud

## Success Metrics

- All ClickUp tools: 200 OK
- All Filesystem tools: 200 OK
- All GitHub tools: 200 OK (after token refresh)
- All Trello tools: 200 OK (after token refresh)
- SonarQube tools: Working or clear config error (after SONARQUBE_ORG added)
- Excel/Dashboard tools: 200 OK
- User identity recognized in MCP Proxy (not anonymous)
- No phantom tools from disabled servers

## Open Questions

1. Does Lukas have a new GitHub PAT to replace the expired one?
2. Does Lukas have fresh Trello API credentials?
3. What is the SonarQube organization ID for SonarCloud?
4. Should we add Atlassian (Jira/Confluence) SSE server to the unified compose?

## Implementation Order

1. Create unified docker-compose.yml for Hetzner (US-001)
2. Fix auth flow - auth_type session + WEBUI_SECRET_KEY (US-002)
3. Add Excel/Dashboard containers (US-007)
4. Sync local code to Hetzner (US-008)
5. Deploy and test with /refresh
6. Disable servers without keys (US-006) - verify auto-enable works
7. Document token refresh needs for Lukas (US-003, US-004, US-005)
