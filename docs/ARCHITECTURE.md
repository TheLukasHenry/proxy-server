# Architecture Overview

**Last Updated:** January 23, 2026

Multi-tenant AI platform with MCP tool integration.
**Deployment:** Docker Compose on Hetzner VPS (NOT Kubernetes)

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DOCKER COMPOSE SETUP                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Open WebUI  │───►│  MCP Proxy   │───►│ MCP Servers  │      │
│  │  :3000       │    │  :8000       │    │ GitHub, etc  │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                                    │
│         ▼                   ▼                                    │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │  PostgreSQL  │◄───│  Group/User  │                           │
│  │  :5432       │    │  Database    │                           │
│  └──────────────┘    └──────────────┘                           │
│                                                                  │
│  For Hetzner Production (adds):                                  │
│  ┌──────────────┐    ┌──────────────┐                           │
│  │   Traefik    │───►│ Auth Service │ (SSL + OIDC)              │
│  └──────────────┘    └──────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment

| Environment | Command | Database |
|-------------|---------|----------|
| **Local Dev** | `docker compose up -d` | PostgreSQL |
| **Hetzner Prod** | `docker compose -f docker-compose.hetzner.yml up -d` | PostgreSQL |

**Note:** Kubernetes deployment is archived. We use Docker Compose now.

## Multi-Tenant Architecture

**How it works:**
1. User logs into Open WebUI with email (e.g., `joelalama@google.com`)
2. MCP Proxy extracts user email from request headers
3. Tenant config (`tenants.py`) determines which tools the user can access
4. User only sees tools from their assigned tenants

**Tenant Mappings (tenants.py):**
- `joelalama@google.com` -> Google tenant + GitHub tenant (14 tools)
- `miketest@microsoft.com` -> Microsoft tenant only
- Admin users -> All tenants (42+ tools)

## Key Files

```
IO/
├── docker-compose.yml              # Main development setup
├── docker-compose.hetzner.yml      # Hetzner production
├── docker-compose.local-test.yml   # Local testing
├── .env.hetzner.example            # Environment template
│
├── mcp-proxy/                      # Multi-tenant MCP gateway
│   ├── main.py                     # FastAPI server
│   ├── tenants.py                  # Tenant/group mappings
│   ├── auth.py                     # User extraction (API_GATEWAY_MODE)
│   └── config/mcp-servers.json     # Server definitions
│
├── admin-portal/                   # User/Group management UI
│   └── main.py
│
├── auth-service/                   # ForwardAuth for Traefik
│   └── main.py
│
├── traefik/                        # Reverse proxy (Hetzner)
│   ├── traefik.yml
│   └── dynamic/middlewares.yml
│
├── scripts/
│   └── init-db-hetzner.sql         # Database schema
│
├── open-webui-functions/           # Custom Open WebUI tools
│   └── reporting/                  # Reporting toolkit
│
├── archive/                        # OLD - not used
└── docs/                           # Documentation
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| open-webui | 3000/8080 | Main UI (Chat interface) |
| mcp-proxy | 8000 | Multi-tenant tool gateway |
| mcp-filesystem | 8001 | File access tools |
| mcp-github | 8002 | GitHub API tools |
| postgresql | 5432 | Database (K8s only) |

## Adding New Tenants

1. Edit `mcp-proxy/tenants.py`
2. Add tenant configuration with MCP server URL
3. Map users to tenant in `USER_TENANT_MAPPING`
4. Restart MCP Proxy

## Adding New Users

1. Create user in Open WebUI (Admin Panel -> Users)
2. Add user email to `tenants.py` USER_TENANT_MAPPING
3. User will see tools from assigned tenants on next login

## Production Deployment (Hetzner)

For production on Hetzner VPS:
1. Use `docker-compose.hetzner.yml`
2. PostgreSQL stores user/group mappings
3. Traefik handles SSL (Let's Encrypt) and OIDC auth
4. Admin Portal for user/group management

## Authentication Flow (Hetzner)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │────►│   Traefik    │────►│ Auth Service │
│              │     │  (SSL+OIDC)  │     │ (PostgreSQL) │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                    │
                            ▼                    ▼
                     ┌──────────────┐     ┌──────────────┐
                     │  Open WebUI  │     │  MCP Proxy   │
                     │  X-User-*    │     │  X-User-*    │
                     └──────────────┘     └──────────────┘
```

**Headers set by Auth Service:**
- `X-User-Email`: user@company.com
- `X-User-Groups`: MCP-Admin,MCP-GitHub
- `X-User-Admin`: true/false

## Database Tables

```sql
-- User to group membership
user_group_membership (user_email, group_name)

-- Group to MCP server access
group_tenant_mapping (group_name, tenant_id)

-- Admin users
user_admin_status (user_email, is_admin)
```

**Group → Server Mapping:**
| Group | Server Access |
|-------|---------------|
| MCP-Admin | All servers |
| MCP-GitHub | github server |
| Tenant-Google | Google-specific servers |
