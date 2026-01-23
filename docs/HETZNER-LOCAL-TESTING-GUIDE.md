# Hetzner Architecture - Local Testing Guide

**Date:** January 21, 2026
**Status:** Ready for Local Testing

---

## Overview

This guide explains how to test the new Hetzner architecture locally before deploying to production.

### Key Changes from Kubernetes:

| Aspect | OLD (Kubernetes) | NEW (Hetzner) |
|--------|------------------|---------------|
| **Deployment** | Kubernetes on Azure | Docker Compose on Hetzner VPS |
| **Entry Point** | Nginx Ingress | Traefik reverse proxy |
| **SSL** | Cert-Manager | Traefik ACME (built-in) |
| **Groups Source** | Entra ID token claims | PostgreSQL database |
| **Group Management** | Azure Portal | Admin Portal (web UI) |
| **Cost** | ~$200-500/month | ~$10-30/month |

---

## Files Created

```
IO/
├── docker-compose.hetzner.yml      # Production (Hetzner VPS)
├── docker-compose.local-test.yml   # LOCAL TESTING
├── .env.hetzner.example            # Environment template
│
├── traefik/                        # Traefik configuration
│   ├── traefik.yml                 # Main config
│   └── dynamic/
│       └── middlewares.yml         # OIDC + ForwardAuth
│
├── auth-service/                   # ForwardAuth service
│   ├── main.py                     # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
│
├── admin-portal/                   # User/Group management UI
│   ├── main.py                     # FastAPI + HTML templates
│   ├── Dockerfile
│   └── requirements.txt
│
├── scripts/
│   └── init-db-hetzner.sql         # Database schema
│
└── mcp-proxy/
    └── auth.py                     # Updated for API_GATEWAY_MODE
```

---

## Local Testing

### Step 1: Start Services

```bash
# From the IO directory
docker compose -f docker-compose.local-test.yml up -d
```

### Step 2: Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Open WebUI** | http://localhost:3000 | AI Chat Interface |
| **Admin Portal** | http://localhost:8080 | Manage Users & Groups |
| **MCP Proxy** | http://localhost:8000 | Tool Gateway API |
| **Auth Service** | http://localhost:8090 | ForwardAuth (internal) |
| **PostgreSQL** | localhost:5432 | Database |

### Step 3: Test Admin Portal

1. Open http://localhost:8080
2. Go to **Users** tab
3. Add a test user: `test@example.com` → `MCP-Admin` group
4. Go to **Mappings** tab
5. Verify MCP-Admin has access to all servers

### Step 4: Test Auth Service

```bash
# Test group lookup
curl "http://localhost:8090/auth/test?email=admin@example.com"

# Expected response:
{
  "email": "admin@example.com",
  "groups": ["MCP-Admin", "MCP-GitHub", "MCP-Filesystem"],
  "is_admin": true
}
```

### Step 5: Test MCP Proxy with Headers

```bash
# Simulate request with API Gateway headers
curl -H "X-User-Email: admin@example.com" \
     -H "X-User-Groups: MCP-Admin,MCP-GitHub" \
     http://localhost:8000/servers

# Should return list of servers the user can access
```

---

## Database Tables

### user_group_membership
Which users belong to which groups.

```sql
SELECT * FROM user_group_membership;

-- Example:
-- user_email          | group_name
-- admin@example.com   | MCP-Admin
-- admin@example.com   | MCP-GitHub
-- alice@company.com   | MCP-GitHub
```

### group_tenant_mapping
Which groups can access which MCP servers.

```sql
SELECT * FROM group_tenant_mapping;

-- Example:
-- group_name    | tenant_id
-- MCP-Admin     | github
-- MCP-Admin     | filesystem
-- MCP-GitHub    | github
```

### Helper Views

```sql
-- User's server access
SELECT * FROM user_server_access WHERE user_email = 'admin@example.com';

-- Group summary
SELECT * FROM group_summary;
```

---

## Architecture Flow

### LOCAL TESTING (No Traefik OIDC):

```
User → Open WebUI → MCP Proxy
              ↓           ↓
         Login Form    API_GATEWAY_MODE=true
              ↓           ↓
         Sends headers  Trusts X-User-Email, X-User-Groups
```

### PRODUCTION (Hetzner with Traefik):

```
User → Traefik → traefikoidc → auth-service → Backend
           ↓           ↓              ↓
         HTTPS    Microsoft      PostgreSQL
         + SSL    Entra ID       (groups lookup)
                     ↓
                Sets X-Forwarded-User
                     ↓
                auth-service reads email
                queries PostgreSQL for groups
                returns X-User-Email, X-User-Groups
```

---

## Differences: Local vs Production

| Aspect | LOCAL | PRODUCTION |
|--------|-------|------------|
| SSL | None (HTTP) | Let's Encrypt (HTTPS) |
| Auth | Login form | Microsoft Entra ID OIDC |
| URL | localhost:3000 | app.yourdomain.com |
| Traefik | Not used | Reverse proxy + OIDC |
| Ports | Exposed | Only 80/443 exposed |

---

## Troubleshooting

### Database not connecting

```bash
# Check PostgreSQL is running
docker logs postgres

# Check connection
docker exec -it postgres psql -U openwebui -d openwebui -c "SELECT 1"
```

### Auth service not starting

```bash
# Check logs
docker logs auth-service

# Common issue: Database not ready
# Solution: Wait for PostgreSQL to be healthy
```

### MCP Proxy not filtering servers

```bash
# Verify API_GATEWAY_MODE is enabled
docker exec mcp-proxy env | grep API_GATEWAY

# Should show: API_GATEWAY_MODE=true
```

### Admin Portal not showing users

```bash
# Check if tables were created
docker exec -it postgres psql -U openwebui -d openwebui -c "\\dt"

# Should show: user_group_membership, group_tenant_mapping, user_admin_status
```

---

## Next Steps

### For Hetzner Production:

1. Get Hetzner VPS (4GB+ RAM recommended)
2. Point DNS records:
   - `app.yourdomain.com` → VPS IP
   - `mcp.yourdomain.com` → VPS IP
   - `admin.yourdomain.com` → VPS IP
3. Copy `.env.hetzner.example` to `.env` and fill in values
4. Create `traefik-public` network: `docker network create traefik-public`
5. Run: `docker compose -f docker-compose.hetzner.yml up -d`

---

*Guide created: January 21, 2026*
