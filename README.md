# MCP Proxy - Multi-Tenant AI Tool Gateway

Enterprise-grade multi-tenant MCP (Model Context Protocol) gateway with centralized authentication, rate limiting, and admin portal.

**Production URL:** https://ai-ui.coolestdomain.win

---

## Key Features

- **15,000+ Users** - Scales to enterprise with Microsoft Entra ID (Azure AD) authentication
- **Auto User Creation** - Users sign in with Microsoft, accounts created automatically
- **Multi-Tenant** - Groups control which MCP servers each tenant can access
- **Admin Portal** - Non-technical admins manage users/groups via web UI (no SQL needed)
- **API Gateway** - Centralized JWT validation, rate limiting, analytics
- **Tenant API Keys** - Store API keys in database, not .env files

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TRAFFIC FLOW                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   Browser ──► Cloudflare ──► Caddy:80 ──► API Gateway:8085 ──► Backend Services │
│                                                 │                                │
│                                                 ├── MCP Proxy    (tools)         │
│                                                 ├── Open WebUI   (chat)          │
│                                                 └── Admin Portal (management)    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### What Each Component Does

| Component | Port | Purpose |
|-----------|------|---------|
| **Caddy** | 80 | Reverse proxy, routes all traffic to API Gateway |
| **API Gateway** | 8085 | JWT validation, rate limiting, header injection |
| **MCP Proxy** | 8000 | Tool orchestration, multi-tenant filtering |
| **Open WebUI** | 3100 | AI chat interface |
| **Admin Portal** | 8080 | User/group management UI |
| **PostgreSQL** | 5432 | Database for users, groups, analytics |
| **Redis** | 6379 | Session cache |

---

## Quick Start (Production)

### Prerequisites
- Docker & Docker Compose
- Domain with Cloudflare (or direct access)

### Deploy

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your secrets

# Start all services
docker compose -f docker-compose.unified.yml up -d

# Check health
curl http://localhost/gateway/health
```

### URLs

| URL | Service |
|-----|---------|
| `/` | Open WebUI (main chat) |
| `/mcp-admin` | Admin Portal |
| `/gateway/health` | API Gateway health check |
| `/gateway/stats` | Rate limiter statistics |
| `/servers` | List MCP servers |

---

## Docker Compose Files

| File | Purpose | When to Use |
|------|---------|-------------|
| `docker-compose.unified.yml` | **Production** - Full stack with API Gateway | Deploy to server |
| `docker-compose.yml` | Basic stack without gateway | Quick local testing |
| `docker-compose.local-test.yml` | Local dev with test auth | Development |

### Production Deployment

```bash
docker compose -f docker-compose.unified.yml up -d
```

### Local Development

```bash
docker compose up -d
```

---

## API Gateway Features

The API Gateway sits between Caddy and backend services, providing:

### 1. JWT Validation
- Validates Open WebUI session tokens
- Extracts user info from JWT claims

### 2. Rate Limiting
- **Authenticated users:** 100 requests/minute
- **Unauthenticated (by IP):** 1000 requests/minute

### 3. Header Injection
Injects user info for downstream services:
```
X-User-Email: user@example.com
X-User-Groups: MCP-Admin,MCP-GitHub
X-User-Admin: true
X-User-Name: user
X-Gateway-Validated: true
```

### 4. API Analytics
Logs all requests to `mcp_proxy.api_analytics` table:
- User email
- Method, endpoint
- Status code, response time
- User agent, client IP

### Configuration

```bash
# .env variables
RATE_LIMIT_PER_MINUTE=100     # Per authenticated user
RATE_LIMIT_PER_IP=1000        # Per IP (unauthenticated)
RATE_LIMIT_ENABLED=true
ENABLE_API_ANALYTICS=true
```

---

## Microsoft Entra ID Authentication

All 15,000+ users authenticate via **Microsoft Entra ID (Azure AD)** using their work email.

### User Flow

```
1. User visits https://ai-ui.coolestdomain.win
2. Clicks "Sign in with Microsoft"
3. Authenticates with work email (e.g., john@acmecorp.com)
4. Open WebUI creates account automatically (first login)
5. User starts as basic user (no MCP access)
6. Admin assigns user to groups via /mcp-admin
7. User can now access MCP tools based on their groups
```

### Why Microsoft Auth?
- No manual user creation for 15K users
- Users use existing work credentials
- Automatic account provisioning on first login
- Enterprise SSO compliance

---

## Admin Portal

Web-based management interface at `/mcp-admin` for non-technical administrators.

**Access Restricted:** Only Open WebUI admins can access the portal.

### Features

| Tab | Purpose |
|-----|---------|
| **Users & Groups** | Assign users to permission groups |
| **Groups & Servers** | Configure which servers each group can access |
| **API Keys** | Manage tenant-specific API keys (not in .env!) |
| **Dynamic Routing** | Route tenants to different backend containers |

### Access Control
- Checks Open WebUI `user.role = 'admin'`
- Non-admins get 403 Forbidden
- Even with direct URL access, API rejects non-admins

### Database Tables

```sql
-- User-group assignments
mcp_proxy.user_group_membership (user_email, group_name)

-- Group-server permissions
mcp_proxy.group_tenant_mapping (group_name, tenant_id)

-- Tenant API keys (encrypted)
mcp_proxy.tenant_server_keys (tenant_id, server_id, api_key_encrypted)

-- Custom endpoint routing
mcp_proxy.tenant_server_endpoints (tenant_id, server_id, endpoint_url)

-- Request analytics
mcp_proxy.api_analytics (timestamp, user_email, method, endpoint, status_code, ...)
```

---

## Multi-Tenant Access Control

### How It Works

1. User logs into Open WebUI
2. API Gateway validates JWT, looks up user's groups from database
3. Gateway injects `X-User-Groups` header
4. MCP Proxy filters tools based on group membership

### Example Groups

| Group | Access |
|-------|--------|
| `MCP-Admin` | All servers (admin) |
| `MCP-GitHub` | GitHub tools only |
| `MCP-Filesystem` | Filesystem tools only |
| `Tenant-AcmeCorp` | Company-specific servers |

### Adding a New Tenant

1. Go to `/mcp-admin` → Groups & Servers
2. Click "Create Group" → Name: `Tenant-NewCompany`
3. Select which servers they can access
4. Go to Users & Groups → Add users to the group
5. (Optional) Add tenant-specific API keys in API Keys tab

---

## Environment Variables

### Required

```bash
WEBUI_SECRET_KEY=your-secret-key      # JWT signing key (must match Open WebUI)
POSTGRES_PASSWORD=your-db-password     # Database password
DATABASE_URL=postgresql://...          # Full connection string
```

### Optional

```bash
# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_IP=1000
RATE_LIMIT_ENABLED=true

# Analytics
ENABLE_API_ANALYTICS=true

# Debug
DEBUG=false

# MCP Proxy
API_GATEWAY_MODE=true                  # Trust headers from gateway
META_TOOLS_MODE=false                  # Use meta-tools pattern
```

### MCP Server API Keys

```bash
# Source Control
GITHUB_TOKEN=ghp_...
GITLAB_TOKEN=glpat-...

# Project Management
LINEAR_API_KEY=...
NOTION_API_KEY=ntn_...
CLICKUP_API_KEY=...

# Communication
SLACK_BOT_TOKEN=xoxb-...

# See .env.example for full list
```

---

## Project Structure

```
├── api-gateway/              # API Gateway service
│   ├── main.py               # FastAPI app (JWT, rate limiting, routing)
│   ├── Dockerfile
│   └── requirements.txt
│
├── mcp-proxy/                # MCP Proxy service
│   ├── main.py               # Tool orchestration, OpenAPI generation
│   ├── auth.py               # User extraction from headers
│   ├── db.py                 # Database queries (groups, keys, etc.)
│   ├── tenants.py            # Server configurations
│   ├── admin_api.py          # Admin portal API endpoints
│   └── static/portal.html    # Admin portal UI
│
├── Caddyfile                 # Reverse proxy configuration
├── docker-compose.unified.yml # Production deployment
├── docker-compose.yml        # Basic local deployment
├── .env.example              # Environment template
│
├── docs/                     # Documentation
│   ├── roadmap-api-gateway.md
│   └── admin-portal-architecture.md
│
└── tasks/                    # PRDs and task definitions
    └── prd-admin-portal.md
```

---

## Commands

### Deployment

```bash
# Start production stack
docker compose -f docker-compose.unified.yml up -d

# View logs
docker compose -f docker-compose.unified.yml logs -f

# Restart specific service
docker compose -f docker-compose.unified.yml restart api-gateway

# Rebuild after code changes
docker compose -f docker-compose.unified.yml build api-gateway
docker compose -f docker-compose.unified.yml up -d api-gateway
```

### Health Checks

```bash
# Gateway health
curl http://localhost/gateway/health

# Rate limiter stats
curl http://localhost/gateway/stats

# MCP Proxy servers
curl http://localhost/servers
```

### Database

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U openwebui -d openwebui

# View users and groups
SELECT * FROM mcp_proxy.user_group_membership;

# View API analytics
SELECT * FROM mcp_proxy.api_analytics ORDER BY id DESC LIMIT 10;
```

---

## Troubleshooting

### API Gateway returns 502

```bash
# Check if services can communicate
docker network ls
docker network inspect proxy-server_backend

# Ensure MCP Proxy is on same network
docker network connect proxy-server_backend mcp-proxy
```

### Admin Portal shows "No users found"

1. Ensure you're logged into Open WebUI first
2. Check you have `MCP-Admin` group membership
3. Check MCP Proxy logs: `docker logs mcp-proxy`

### Rate limit exceeded

```bash
# Check current rate limit status
curl http://localhost/gateway/stats

# Rate limits reset after 60 seconds
```

---

## Security Notes

- API keys stored encrypted in database (not .env for tenant-specific keys)
- JWT validated on every request through API Gateway
- Admin portal restricted to Open WebUI admins only
- Rate limiting prevents abuse
- All requests logged for audit

---

## Deploying to Server

### First Time Setup

```bash
# 1. SSH to server
ssh root@your-server-ip

# 2. Clone repository
git clone <repo-url> /root/proxy-server
cd /root/proxy-server

# 3. Configure environment
cp .env.example .env
nano .env  # Fill in secrets

# 4. Start all services
docker compose -f docker-compose.unified.yml up -d

# 5. Verify
curl http://localhost:8085/gateway/health
```

### Updating Code on Server

```bash
# 1. Push changes to git (from local)
git add .
git commit -m "Update message"
git push

# 2. SSH to server and pull
ssh root@your-server-ip
cd /root/proxy-server
git pull

# 3. Rebuild and restart affected service
docker compose -f docker-compose.unified.yml build api-gateway
docker compose -f docker-compose.unified.yml up -d api-gateway
```

### Updating Without Git (Direct Copy)

```bash
# Copy single file to server
scp ./api-gateway/main.py root@your-server-ip:/root/proxy-server/api-gateway/main.py

# SSH and rebuild
ssh root@your-server-ip
cd /root/proxy-server
docker compose -f docker-compose.unified.yml build api-gateway
docker compose -f docker-compose.unified.yml up -d api-gateway
```

### Server Requirements

- Ubuntu 22.04+ or Debian 11+
- Docker & Docker Compose v2
- 4GB RAM minimum (8GB recommended)
- Ports 80, 443 open (or Cloudflare Tunnel)

---

## For AI Assistants

**DO NOT COMMIT OR PUSH WITHOUT EXPLICIT APPROVAL**

1. Only edit files in this `IO` repository
2. Do NOT touch `ai_ui` directory (client repository)
3. Ask before committing or pushing
4. Test changes locally before deploying

---

## License

Internal use only.
