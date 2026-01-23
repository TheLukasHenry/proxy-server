# Current Project Status

**Date:** January 23, 2026
**Last Updated:** By Claude

---

## TL;DR - What We Have Now

| Component | Status | Notes |
|-----------|--------|-------|
| Open WebUI | ✅ Running | localhost:3000 |
| PostgreSQL Database | ✅ Running | User groups stored here |
| MCP Proxy | ✅ Running | Multi-tenant tool gateway |
| Admin Portal | ✅ Built | User/group management UI |
| Auth Service | ✅ Built | ForwardAuth for Traefik |
| Traefik Config | ✅ Built | For Hetzner production |
| Reporting Tools | ✅ Working | Excel export + Charts |

---

## Architecture - NOW (Hetzner/Docker Compose)

**We are NOT using Kubernetes anymore.** We migrated to Docker Compose on Hetzner.

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LOCAL TESTING:                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Open WebUI  │───►│  MCP Proxy   │───►│ MCP Servers  │  │
│  │  :3000       │    │  :8000       │    │ GitHub, etc  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                               │
│         ▼                   ▼                               │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │  PostgreSQL  │◄───│ Group/User   │                      │
│  │  :5432       │    │ Database     │                      │
│  └──────────────┘    └──────────────┘                      │
│                                                              │
│  HETZNER PRODUCTION (when deployed):                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Traefik    │───►│ Auth Service │───►│  Backends    │  │
│  │   (SSL)      │    │ (PostgreSQL) │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Files That Exist

### Docker Compose Files
```
IO/
├── docker-compose.yml              # Main development (USE THIS)
├── docker-compose.hetzner.yml      # Hetzner production
├── docker-compose.local-test.yml   # Local testing mode
└── .env.hetzner.example            # Environment template
```

### Hetzner Components (All Built)
```
IO/
├── admin-portal/                   # ✅ User/Group management UI
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── auth-service/                   # ✅ ForwardAuth for Traefik
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── traefik/                        # ✅ Reverse proxy config
│   ├── traefik.yml
│   └── dynamic/
│       └── middlewares.yml
│
└── scripts/
    └── init-db-hetzner.sql         # ✅ Database schema
```

### MCP Proxy (Core)
```
IO/mcp-proxy/
├── main.py                         # FastAPI server
├── auth.py                         # User extraction (API_GATEWAY_MODE)
├── tenants.py                      # Tenant/group mappings
├── mcp_server.py                   # MCP protocol handler
└── config/
    └── mcp-servers.json            # Server definitions
```

### Open WebUI Functions (Reporting)
```
IO/open-webui-functions/
└── reporting/
    └── visualize_data_action.py    # Chart visualization v0.2.1

IO/temp/
├── export_to_excel_fixed.py        # Excel export
└── visualize_data_r3.py            # AI-powered charts (community)
```

---

## What's Working Right Now

### Open WebUI Functions (Action Buttons)
| Function | Version | Status |
|----------|---------|--------|
| Export to Excel | v0.1.1 | ✅ Working |
| Visualize Data | v0.2.1 | ✅ Working |
| Visualize Data R3 | v0.0.2r3 | ⚠️ Needs API config |

### Multi-Tenant MCP
| Feature | Status |
|---------|--------|
| MCP Proxy | ✅ Running |
| Group-based access | ✅ Works via PostgreSQL |
| API Gateway Mode | ✅ Supports X-User-* headers |

---

## Key Changes from Before

| Before (Kubernetes/Azure) | Now (Docker Compose/Hetzner) |
|---------------------------|------------------------------|
| Kubernetes on Azure AKS | Docker Compose on Hetzner VPS |
| ~$200-500/month | ~$10-30/month |
| Entra ID groups from JWT | PostgreSQL database for groups |
| Azure Portal for group mgmt | Admin Portal UI |
| Cert-Manager for SSL | Traefik ACME (Let's Encrypt) |
| Complex YAML manifests | Simple docker-compose.yml |

---

## How to Run Locally

```bash
# Start everything
docker compose up -d

# Access services
# Open WebUI: http://localhost:3000
# Admin Portal: http://localhost:8080 (if enabled)
# MCP Proxy: http://localhost:8000
```

---

## Database Tables (PostgreSQL)

```sql
-- User to group membership
user_group_membership (user_email, group_name)

-- Group to MCP server mapping
group_tenant_mapping (group_name, tenant_id)

-- Admin status
user_admin_status (user_email, is_admin)
```

---

## What's NOT Being Used Anymore

These folders exist but are **archived/not used**:

```
kubernetes/          # OLD - Not using Kubernetes
archive/             # OLD - Archived files
mcp-poc/             # OLD - Proof of concept
```

---

## Documentation Status

| Doc | Status | Notes |
|-----|--------|-------|
| HETZNER-LOCAL-TESTING-GUIDE.md | ✅ Current | How to test locally |
| REPORTING-TOOLKIT-GUIDE.md | ✅ Updated | Excel + Charts |
| ARCHITECTURE.md | ⚠️ Outdated | Still mentions K8s |
| plans/2026-01-22-kubernetes-to-hetzner-migration.md | ✅ Current | Migration plan |

---

## Next Steps (If Needed)

1. **Deploy to Hetzner VPS** (when ready for production)
2. **Update ARCHITECTURE.md** to reflect Docker Compose setup
3. **Configure Visualize Data R3** if AI-powered charts needed
4. **Test Admin Portal** with real users

---

## Quick Reference

**Start local environment:**
```bash
docker compose up -d
```

**Open WebUI:**
```
http://localhost:3000
Admin: alamajacintg04@gmail.com / 123456
```

**Check MCP Proxy:**
```bash
curl http://localhost:8000/health
```

**View database:**
```bash
docker exec -it postgres psql -U openwebui -d openwebui
\dt  -- list tables
SELECT * FROM user_group_membership;
SELECT * FROM group_tenant_mapping;
```

---

*Status captured: January 23, 2026*
