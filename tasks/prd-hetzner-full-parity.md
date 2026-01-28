# PRD: Hetzner Full Parity — MCP Proxy, Database Safety & Progressive Disclosure

## Introduction

Lukas tested the live Hetzner deployment and found that while tools connect and attempt to call correctly, many return 500 errors. Beyond fixing those immediate issues, we need to ensure our custom database tables survive Open WebUI upstream updates (by isolating them in a separate PostgreSQL schema), get all MCP servers actually callable with valid API tokens, and lay the groundwork for progressive disclosure — showing users only the tools relevant to their prompt instead of overwhelming the LLM with 200+ tool definitions.

This PRD covers everything in three phases:
- **Phase 1 (ASAP):** Fix deployed Hetzner to full working state
- **Phase 2 (Near-term):** Database schema safety + remote MCP servers
- **Phase 3 (Future):** Progressive disclosure + context-aware tool selection

## Current State (What's Already Fixed)

The following were fixed in the previous session and are now working on Hetzner:
- Unified `docker-compose.hetzner-unified.yml` with all 13 services (no more config drift)
- Auth flow: `auth_type: "session"` sends JWT, `WEBUI_SECRET_KEY` shared, `API_GATEWAY_MODE=false`
- MCP Proxy visible in Open WebUI External Tools settings and chat integrations menu
- `TOOL_SERVER_CONNECTIONS` has `"config":{"enable":true}` (required by Open WebUI)
- 232 tools cached from 7 MCP servers (clickup, github, trello, sonarqube, filesystem, excel, dashboard)
- JWT auth end-to-end: JWT → DB user lookup → DB group lookup → access granted
- Database seeded with 29 group-tenant mappings via `db-init` container
- OAuth group management env vars added (`ENABLE_OAUTH_GROUP_MANAGEMENT`, `OAUTH_ADMIN_ROLES`, etc.)

## Goals

- Every MCP tool call returns 200 (not 500) for servers with valid API keys
- Custom database tables isolated in `mcp_proxy` schema, safe from Open WebUI Alembic migrations
- Remote MCP servers (Linear, Notion, etc.) callable when API keys are provided
- Group-based tool filtering works end-to-end (users only see tools their groups allow)
- Architecture documented for progressive disclosure (context-aware tool selection)
- Research completed on existing tools/libraries for smart tool routing

## User Stories

---

### PHASE 1: ASAP — Fix Deployed Hetzner

---

### US-001: Refresh expired API tokens on Hetzner
**Description:** As Lukas, I need valid API tokens so GitHub, Trello, and SonarQube tool calls succeed instead of returning 500 errors.

**Acceptance Criteria:**
- [ ] Document which tokens are expired and what Lukas needs to generate:
  - GitHub: New Personal Access Token (PAT) with `repo`, `read:org`, `read:user` scopes
  - Trello: New API Key + API Token from https://trello.com/power-ups/admin
  - SonarQube: Organization ID for SonarCloud (env var `SONARQUBE_ORG`)
- [ ] Update `.env` on Hetzner with fresh tokens (after Lukas provides them)
- [ ] Rebuild mcp-proxy: `docker compose build mcp-proxy --no-cache && docker compose up -d mcp-proxy`
- [ ] Run `POST /refresh` and verify tools cache successfully
- [ ] Test: `POST /github/github_get_me` returns 200 with valid user info
- [ ] Test: `POST /trello/trello_list_boards` returns 200 with boards
- [ ] Test: `POST /sonarqube/sonarqube_search_projects` returns 200 or clear error about org

---

### US-002: Verify network and firewall on Hetzner
**Description:** As a developer, I need to confirm all MCP services are reachable on the Docker internal network, since networking behaves differently on a remote server vs localhost.

**Acceptance Criteria:**
- [ ] From mcp-proxy container, curl each MCP server's health/openapi endpoint:
  - `http://mcp-filesystem:8001/openapi.json` → 200
  - `http://mcp-github:8000/openapi.json` → 200
  - `http://mcp-clickup:8000/openapi.json` → 200
  - `http://mcp-trello:8000/openapi.json` → 200
  - `http://mcp-sonarqube:8000/openapi.json` → 200
  - `http://mcp-excel:8000/openapi.json` → 200
  - `http://mcp-dashboard:8000/openapi.json` → 200
- [ ] Verify mcp-proxy port 8000 accessible from host: `curl http://localhost:8000/health`
- [ ] Verify Open WebUI can reach mcp-proxy internally: `docker exec open-webui curl http://mcp-proxy:8000/health`
- [ ] Document any firewall rules needed (ufw, iptables) for inter-container communication
- [ ] All 232 tools load after `POST /refresh`

---

### US-003: End-to-end tool call test from Open WebUI chat
**Description:** As a user, I need to type a prompt in the Hetzner Open WebUI chat and have MCP tools called successfully (not just via curl).

**Acceptance Criteria:**
- [ ] Log into http://46.224.193.25:3100/ as test user
- [ ] Enable MCP Proxy in chat integrations (wrench icon → toggle MCP Proxy ON)
- [ ] Send prompt: "List my ClickUp workspaces" → ClickUp tool called, returns workspace data
- [ ] Send prompt: "List files in /data" → Filesystem tool called, returns file listing
- [ ] Send prompt: "Create a simple Excel with columns Name, Revenue" → Excel tool called, download link appears
- [ ] MCP Proxy logs show JWT validated, user email extracted, groups checked, access granted
- [ ] No 500 errors in mcp-proxy logs during these calls

---

### PHASE 2: NEAR-TERM — Database Safety & Remote MCPs

---

### US-004: Migrate custom tables to `mcp_proxy` PostgreSQL schema
**Description:** As a developer, I need our custom tables (user_group_membership, group_tenant_mapping, user_admin_status) in a separate PostgreSQL schema so Open WebUI's Alembic migrations never touch them.

**Acceptance Criteria:**
- [ ] Create migration script `scripts/migrate-to-mcp-schema.sql`:
  ```sql
  CREATE SCHEMA IF NOT EXISTS mcp_proxy;
  -- Move tables, recreate indexes, grant permissions
  ```
- [ ] Update `scripts/init-db-hetzner.sql` to create tables in `mcp_proxy` schema:
  ```sql
  CREATE TABLE IF NOT EXISTS mcp_proxy.user_group_membership (...)
  CREATE TABLE IF NOT EXISTS mcp_proxy.group_tenant_mapping (...)
  CREATE TABLE IF NOT EXISTS mcp_proxy.user_admin_status (...)
  ```
- [ ] Update all SQL queries in `mcp-proxy/db.py` to use `mcp_proxy.` prefix:
  - `user_group_membership` → `mcp_proxy.user_group_membership`
  - `group_tenant_mapping` → `mcp_proxy.group_tenant_mapping`
  - `user_admin_status` → `mcp_proxy.user_admin_status`
- [ ] Update all SQL queries in `admin-portal/main.py` with same prefix
- [ ] Update `seed_mcp_servers.py` script to use `mcp_proxy.` schema prefix
- [ ] Keep read-only access to `public."user"` table (for email lookup from JWT user_id)
- [ ] Run migration on Hetzner PostgreSQL without data loss
- [ ] Verify: `\dt mcp_proxy.*` shows 3 tables in psql
- [ ] Verify: Open WebUI Alembic migrations still run cleanly (`docker exec open-webui alembic heads`)
- [ ] Verify: Tool calls still work after schema migration (JWT → email → groups → access)

---

### US-005: Document Open WebUI upstream update safety
**Description:** As a developer, I need documentation on how to safely update Open WebUI without losing MCP Proxy data.

**Acceptance Criteria:**
- [ ] Create `docs/DATABASE-SCHEMA-SAFETY.md` documenting:
  - Which tables are ours (`mcp_proxy.*`) vs Open WebUI's (`public.*`)
  - How Open WebUI uses Alembic for migrations (checks `alembic_version` table)
  - Step-by-step: How to update Open WebUI image safely
  - Step-by-step: How to verify our schema is untouched after update
  - Rollback procedure if something goes wrong
- [ ] Add pre-update check script: `scripts/check-mcp-schema.sh` that verifies table counts before/after update

---

### US-006: Enable remote MCP servers with API keys
**Description:** As a user, I need remote MCP servers (Linear, Notion, Atlassian, etc.) to be callable when Lukas provides API keys, without needing to rebuild containers.

**Acceptance Criteria:**
- [ ] Verify auto-enable logic in `tenants.py`: servers with `enabled=bool(os.getenv("KEY"))` correctly:
  - Enable when key IS set in `.env`
  - Disable when key is NOT set in `.env`
- [ ] After adding a new API key to `.env` and restarting mcp-proxy:
  - `POST /refresh` picks up the newly enabled server
  - Tools from that server appear in the OpenAPI spec
  - Tool calls to that server succeed (200)
- [ ] Document the process for Lukas: "How to add a new MCP server API key"
  1. Add key to `.env` file on Hetzner
  2. Run `docker compose restart mcp-proxy`
  3. Call `POST /refresh`
  4. Verify tools appear
- [ ] Test with at least one remote server that has an API key (e.g., Atlassian if configured)
- [ ] Disabled servers (no API key) return no tools and do not appear in OpenAPI spec

---

### US-007: Add Open WebUI native MCP servers (no proxy needed)
**Description:** As Lukas, I want MCP servers that Open WebUI supports natively (direct connection) to be added alongside the proxy servers, giving users the widest tool selection.

**Acceptance Criteria:**
- [ ] Research which MCP servers Open WebUI v0.7.2 supports natively via `TOOL_SERVER_CONNECTIONS` with `type: "mcp"`
- [ ] Identify servers from Lukas's Trello list that can be added directly
- [ ] Add native MCP servers to `TOOL_SERVER_CONNECTIONS` env var (alongside existing proxy connection)
- [ ] Verify native MCP tools appear in the chat integrations menu
- [ ] Document: Which servers go through proxy (multi-tenant filtering) vs direct (no filtering)

---

### PHASE 3: FUTURE — Progressive Disclosure & Smart Tool Routing

---

### US-008: Research context-aware tool selection libraries
**Description:** As a developer, I need to research existing tools, libraries, or patterns that solve the "too many tools" problem — selecting only relevant tools for a given prompt instead of sending all 232 to the LLM.

**Acceptance Criteria:**
- [ ] Research and document findings on:
  - **Tool indexing approaches**: Embedding tool descriptions, semantic search for relevant tools
  - **Existing libraries**: Any open-source projects that do tool routing/selection (e.g., LangChain tool selection, LlamaIndex tool retrieval, ToolLLM, Gorilla, NexusRaven)
  - **MCP-native approaches**: Does the MCP protocol have built-in tool filtering or categories?
  - **Open WebUI plugins**: Can a middleware/function pre-filter tools before they reach the LLM?
  - **Two-stage approach**: First ask a small/fast model "which tools are relevant?", then call the main model with only those tools
- [ ] Evaluate each approach on:
  - Implementation complexity (can we integrate it into our proxy?)
  - Latency impact (how much delay does tool selection add?)
  - Accuracy (does it pick the right tools?)
  - Maintenance burden (does it break when we add new tools?)
- [ ] Write `docs/PROGRESSIVE-DISCLOSURE-RESEARCH.md` with findings and recommendation
- [ ] Recommend one approach to implement first

---

### US-009: Implement group-based tool filtering in OpenAPI spec
**Description:** As a user, I should only see tools from MCP servers my groups have access to, so the LLM context is not overwhelmed with irrelevant tools.

**Acceptance Criteria:**
- [ ] MCP Proxy's `GET /openapi.json` already accepts user identity from JWT
- [ ] The OpenAPI spec returned is filtered: only paths for servers the user's groups can access
- [ ] User in `MCP-GitHub` group sees GitHub tools but NOT ClickUp tools (if not in that group)
- [ ] User in `MCP-Admin` group sees ALL tools (admin override)
- [ ] Anonymous requests (no JWT) see NO tools (empty OpenAPI spec)
- [ ] Verify: Open WebUI chat with MCP Proxy enabled only shows filtered tools to the LLM
- [ ] Test with two different users in different groups → each sees different tool sets

---

### US-010: Handle duplicate tools across MCP servers
**Description:** As a developer, I need a strategy for when multiple MCP servers expose similar tools (e.g., both GitLab and Bitbucket have "list repositories"), so the LLM knows which one to call.

**Acceptance Criteria:**
- [ ] Document the duplicate tool problem with concrete examples:
  - GitHub `list_repositories` vs GitLab `list_projects` vs Bitbucket `list_repos`
  - Both do the same thing but for different platforms
- [ ] Implement tool name prefixing: `github_list_repositories`, `gitlab_list_projects` (already done by MCP Proxy)
- [ ] Add tool description enrichment: each tool's description includes which platform/server it belongs to
  - Before: "List repositories"
  - After: "List repositories on GitHub. Use this for GitHub-hosted code."
- [ ] Research: Can we add a "routing hint" field to tool descriptions that helps the LLM choose?
- [ ] Document approach in `docs/TOOL-DEDUPLICATION-STRATEGY.md`

---

### US-011: Tenant-specific API key variables
**Description:** As an admin, I need different tenants (Google, Microsoft, AcmeCorp) to use different API keys for the same MCP server, so each tenant's data is isolated.

**Acceptance Criteria:**
- [ ] Design the configuration format for per-tenant API keys:
  ```json
  {
    "server_id": "github",
    "tenant_keys": {
      "Tenant-Google": { "GITHUB_TOKEN": "ghp_google_..." },
      "Tenant-Microsoft": { "GITHUB_TOKEN": "ghp_microsoft_..." }
    }
  }
  ```
- [ ] Update `mcp-proxy/tenants.py` to pass tenant-specific API key when proxying requests
- [ ] When user in Tenant-Google calls GitHub tools, the Google team's PAT is used
- [ ] When user in Tenant-Microsoft calls GitHub tools, the Microsoft team's PAT is used
- [ ] API keys stored securely (environment variables or encrypted in database, NOT in mcp-servers.json)
- [ ] Document: How to configure per-tenant API keys

---

## Functional Requirements

### Phase 1 — ASAP
- FR-1: All MCP servers with valid API keys must return 200 on tool calls (not 500)
- FR-2: Docker internal network must allow mcp-proxy to reach all MCP server containers
- FR-3: Open WebUI chat must successfully trigger MCP tool calls with JWT auth
- FR-4: `POST /refresh` must load all tools from all enabled servers
- FR-5: Servers without API keys must be auto-disabled (no phantom tools)

### Phase 2 — Near-term
- FR-6: Custom tables must live in `mcp_proxy` PostgreSQL schema
- FR-7: Open WebUI Alembic migrations must not affect `mcp_proxy` schema tables
- FR-8: Read-only cross-schema access to `public."user"` table for JWT email lookup
- FR-9: Adding an API key to `.env` + restart + refresh must enable a new server
- FR-10: Native MCP servers added via `TOOL_SERVER_CONNECTIONS` alongside proxy

### Phase 3 — Future
- FR-11: OpenAPI spec must be filtered by user's group memberships
- FR-12: Tool descriptions must include server/platform context for LLM disambiguation
- FR-13: Research document must evaluate at least 3 approaches for context-aware tool selection
- FR-14: Per-tenant API keys must be configurable without code changes

## Non-Goals

- Not implementing Traefik/SSL in this iteration (direct port access for now)
- Not adding new MCP server types beyond what's configured in `mcp-servers.json`
- Not changing the JWT auth architecture (keep current JWT + DB lookup)
- Not fixing Microsoft OAuth/Entra ID login (separate task)
- Not building a custom UI for progressive disclosure configuration
- Not implementing real-time tool usage analytics

## Technical Considerations

### Database Schema Migration
- PostgreSQL supports multiple schemas within a single database
- Use `CREATE SCHEMA IF NOT EXISTS mcp_proxy;` to create isolated namespace
- All custom table queries updated to `mcp_proxy.table_name` format
- Open WebUI's `public` schema untouched — its Alembic migration chain continues working
- Cross-schema reads work natively: `SELECT email FROM public."user" WHERE id = $1`
- Same connection URL — no second database needed

### MCP Proxy Architecture
- `tenants.py` has 60+ server configs across 4 tiers (HTTP, SSE, STDIO, LOCAL)
- Auto-enable: `enabled=bool(os.getenv("API_KEY"))` — servers self-disable without keys
- Tool cache: `POST /refresh` fetches OpenAPI from all enabled servers, caches tools in memory
- OpenAPI generation: `generate_dynamic_openapi_filtered()` can filter by user access

### Open WebUI Integration
- `TOOL_SERVER_CONNECTIONS` env var is a `PersistentConfig` — database can override env var
- `config.enable: true` is REQUIRED for Open WebUI to fetch tool server's OpenAPI spec
- Tool servers appear in chat via Integrations → Tools menu
- Open WebUI v0.7.2 supports both `type: "openapi"` and `type: "mcp"` connections

### Progressive Disclosure Research Areas
- **Semantic tool routing**: Embed tool descriptions, find nearest tools to user prompt
- **Category-based filtering**: Tag tools by category (git, project-management, file-ops), match to prompt intent
- **Two-stage LLM**: Fast model selects relevant tools, main model uses selected subset
- **MCP protocol**: Check if MCP spec supports tool categories or filtering hints

## Success Metrics

### Phase 1
- 0 errors on ClickUp, Filesystem, Excel, Dashboard tool calls
- GitHub, Trello, SonarQube return 200 after token refresh
- End-to-end chat → tool call → response works in Open WebUI on Hetzner

### Phase 2
- `\dt mcp_proxy.*` shows 3 tables in separate schema
- Open WebUI update (`docker pull`) does not affect MCP tables
- New API key → restart → refresh → server enabled in under 2 minutes

### Phase 3
- LLM receives ≤30 tool definitions per prompt (down from 232)
- Tool selection accuracy ≥90% (correct tool chosen for prompt)
- No user-facing latency increase >500ms from tool filtering

## Open Questions

1. **Tokens from Lukas**: Does Lukas have fresh GitHub PAT, Trello API key/token, and SonarQube org ID?
2. **Native MCP servers**: Which servers from Lukas's Trello list should be added directly to Open WebUI (not through proxy)?
3. **Progressive disclosure priority**: Should the research (US-008) happen before or in parallel with group-based filtering (US-009)?
4. **Tenant API keys storage**: Should per-tenant API keys be in environment variables, database, or a secrets manager (e.g., HashiCorp Vault)?
5. **Open WebUI PersistentConfig**: If someone changes `TOOL_SERVER_CONNECTIONS` via the admin UI, it overrides the env var in the database. Should we add a migration that resets this on deploy?

## Implementation Order

### Phase 1 (ASAP — do now)
1. US-002: Verify network and firewall
2. US-003: End-to-end tool call test from chat
3. US-001: Refresh expired tokens (blocked on Lukas providing them)

### Phase 2 (Near-term — next sprint)
4. US-004: Migrate to `mcp_proxy` schema
5. US-005: Document upstream update safety
6. US-006: Enable remote MCP servers with keys
7. US-007: Add native MCP servers to Open WebUI

### Phase 3 (Future — after Phase 2 complete)
8. US-008: Research context-aware tool selection
9. US-009: Group-based tool filtering in OpenAPI
10. US-010: Duplicate tool handling
11. US-011: Tenant-specific API keys
