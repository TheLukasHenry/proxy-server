# PRD: MCP Proxy Server Hetzner Deployment

## Introduction

Deploy the MCP Proxy Server to Hetzner VPS using Docker Compose. This is the first phase of a full-stack deployment. The proxy server provides a unified gateway for multiple MCP (Model Context Protocol) servers, exposing tools to Open WebUI through a single external connection.

**Repository:** https://github.com/TheLukasHenry/proxy-server
**Target:** Hetzner VPS (~$10-30/month vs $200-500/month on Azure/Kubernetes)
**LLM Backend:** OpenAI API directly

## Goals

- Deploy MCP Proxy Server to Hetzner VPS with Docker Compose
- Configure OpenAI API as the LLM backend
- Expose tools hierarchically (`/github/search_repositories`) as ONE Open WebUI external connection
- Establish foundation for full-stack deployment (Open WebUI, Admin Portal, Auth Service)
- Ensure the proxy server is accessible and functional before adding other services

## Architecture Overview

```
Phase 1 (This PRD):
┌─────────────────────────────────────────────────────────┐
│                  HETZNER VPS                             │
│  ┌──────────────┐                                       │
│  │  MCP Proxy   │ ← Single endpoint for all tools       │
│  │  :8000       │                                       │
│  └──────────────┘                                       │
│         ↓                                               │
│  ┌──────────────┐                                       │
│  │ PostgreSQL   │ ← User/group permissions              │
│  │  :5432       │                                       │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘

Phase 2 (Later):
┌─────────────────────────────────────────────────────────┐
│  Traefik → Auth Service → Open WebUI + MCP Proxy + Admin│
└─────────────────────────────────────────────────────────┘
```

## User Stories

### US-001: Provision Hetzner VPS
**Description:** As a DevOps engineer, I need a Hetzner VPS provisioned so that I can deploy the MCP Proxy.

**Acceptance Criteria:**
- [ ] Hetzner VPS created (minimum 4GB RAM, 2 vCPU)
- [ ] Ubuntu 22.04 or Debian 12 installed
- [ ] Docker and Docker Compose installed
- [ ] SSH access configured
- [ ] Firewall allows ports 80, 443, 8000 (temporary for testing)

### US-002: Clone and Configure Repository
**Description:** As a developer, I need the proxy-server repository cloned and configured on the VPS.

**Acceptance Criteria:**
- [ ] Repository cloned from https://github.com/TheLukasHenry/proxy-server
- [ ] `.env` file created from `.env.hetzner.example`
- [ ] OpenAI API key configured (`OPENAI_API_KEY`)
- [ ] PostgreSQL password set (`POSTGRES_PASSWORD`)
- [ ] Domain configured (or use IP for initial testing)

### US-003: Deploy MCP Proxy with Docker Compose
**Description:** As a developer, I need to deploy the MCP Proxy server so that tools are accessible.

**Acceptance Criteria:**
- [ ] `docker compose up -d` runs successfully
- [ ] MCP Proxy container is running and healthy
- [ ] PostgreSQL container is running and healthy
- [ ] Health endpoint responds: `curl http://<vps-ip>:8000/health`
- [ ] Server list endpoint works: `curl http://<vps-ip>:8000/servers`

### US-004: Verify Tool Exposure (Hierarchical)
**Description:** As a user, I want tools exposed hierarchically so Open WebUI can use them as ONE external connection.

**Acceptance Criteria:**
- [ ] Tools accessible at `/{server}/{tool}` format (e.g., `/github/search_repositories`)
- [ ] OpenAPI spec available at `/openapi.json`
- [ ] Single OpenAPI endpoint exposes all available tools
- [ ] Test tool execution: `curl -X POST http://<vps-ip>:8000/github/search_repositories -d '{"arguments":{"query":"test"}}'`

### US-005: Configure OpenAI API Connection
**Description:** As a user, I want the system to use OpenAI API directly for LLM responses.

**Acceptance Criteria:**
- [ ] `OPENAI_API_KEY` environment variable set
- [ ] `OPENAI_API_BASE_URL` set to `https://api.openai.com/v1` (or custom)
- [ ] Verify connection works (when Open WebUI is added later)

### US-006: Database Schema Initialized
**Description:** As a developer, I need the PostgreSQL database initialized with the correct schema.

**Acceptance Criteria:**
- [ ] Tables created: `user_group_membership`, `group_tenant_mapping`, `user_admin_status`
- [ ] Default admin user seeded (if applicable)
- [ ] Default group-to-server mappings seeded
- [ ] Can query: `SELECT * FROM group_tenant_mapping;`

### US-007: Test MCP Proxy Locally First
**Description:** As a developer, I want to test the deployment locally before pushing to Hetzner.

**Acceptance Criteria:**
- [ ] `docker compose -f docker-compose.local-test.yml up -d` works
- [ ] All services start without errors
- [ ] Can access MCP Proxy at `http://localhost:8000`
- [ ] Can access health endpoint
- [ ] Teardown works: `docker compose down`

## Functional Requirements

- **FR-1:** MCP Proxy must expose all enabled MCP server tools through a unified OpenAPI endpoint
- **FR-2:** Tools must be accessible via hierarchical URL pattern: `/{server}/{tool}`
- **FR-3:** Proxy must support `API_GATEWAY_MODE=true` for header-based authentication
- **FR-4:** Proxy must read user permissions from PostgreSQL database
- **FR-5:** Health endpoint must return status of proxy and database connection
- **FR-6:** OpenAPI spec must be dynamically generated from all enabled MCP servers
- **FR-7:** System must use OpenAI API as the LLM backend

## Non-Goals (Out of Scope for Phase 1)

- Traefik reverse proxy setup (Phase 2)
- SSL/TLS with Let's Encrypt (Phase 2)
- Microsoft Entra ID OIDC authentication (Phase 2)
- Open WebUI deployment (Phase 2)
- Admin Portal deployment (Phase 2)
- Auth Service deployment (Phase 2)
- Custom domain configuration (Phase 2)
- Production hardening (Phase 2)

## Technical Considerations

### Docker Compose File to Use
For Phase 1 (proxy-only), create a minimal `docker-compose.proxy-only.yml`:

```yaml
services:
  mcp-proxy:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_GATEWAY_MODE=false  # No auth headers yet
      - DATABASE_URL=postgresql://openwebui:password@postgres:5432/openwebui
    depends_on:
      postgres:
        condition: service_healthy

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=openwebui
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=openwebui
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./scripts/init-db-hetzner.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U openwebui"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
```

### Environment Variables Required

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | `secure-password-123` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `GITHUB_TOKEN` | GitHub PAT (if using GitHub MCP) | `ghp_...` |
| `MCP_API_KEY` | Internal MCP authentication | `mcp-secret-key` |

### Key Files in Repository

```
proxy-server/
├── main.py              # FastAPI proxy server
├── auth.py              # User extraction from headers
├── tenants.py           # MCP server configurations (70+)
├── db.py                # PostgreSQL access control
├── Dockerfile           # Container build
├── docker-compose.yml   # Full stack
├── docker-compose.hetzner.yml  # Production
├── scripts/
│   └── init-db-hetzner.sql     # Database schema
└── .env.hetzner.example        # Environment template
```

## Success Metrics

- MCP Proxy responds to health checks within 500ms
- All configured MCP server tools appear in OpenAPI spec
- Tool execution completes successfully (when tested with curl)
- Database queries for user permissions work correctly
- System stable for 24+ hours without restarts

## Open Questions

1. **Domain:** Should we use a domain immediately or test with IP first?
   - Recommendation: Start with IP, add domain in Phase 2

2. **SSL:** Do we need HTTPS for Phase 1?
   - Recommendation: No, add via Traefik in Phase 2

3. **GitHub MCP:** Should GitHub MCP server be enabled in Phase 1?
   - Depends on having `GITHUB_TOKEN` available

4. **Other MCP Servers:** Which MCP servers should be enabled initially?
   - Recommendation: Start with `filesystem` only, add more as needed

## Next Steps After Phase 1

1. **Phase 2A:** Add Traefik for SSL and reverse proxy
2. **Phase 2B:** Add Open WebUI with OpenAI connection
3. **Phase 2C:** Add Auth Service for Microsoft Entra ID
4. **Phase 2D:** Add Admin Portal for user/group management
5. **Phase 3:** Production hardening, monitoring, backups

---

## Quick Start Commands

```bash
# On Hetzner VPS:

# 1. Clone repository
git clone https://github.com/TheLukasHenry/proxy-server.git
cd proxy-server

# 2. Create environment file
cp .env.hetzner.example .env
nano .env  # Edit with your values

# 3. Start services
docker compose -f docker-compose.proxy-only.yml up -d

# 4. Verify
curl http://localhost:8000/health
curl http://localhost:8000/servers

# 5. Check logs
docker logs mcp-proxy
```

---

*PRD Created: January 26, 2026*
*Author: Claude (with Jacint)*
*Status: Ready for Implementation*
