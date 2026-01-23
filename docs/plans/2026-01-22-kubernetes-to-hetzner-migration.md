# Migration Plan: Kubernetes (Azure AKS) to Hetzner Docker Compose

**Date:** 2026-01-22
**Status:** Ready for Implementation
**Cost Savings:** ~$200-500/month (AKS) → ~$10-30/month (Hetzner)

## Architecture Comparison

### Current: Kubernetes on Azure AKS

```
Internet → Azure Load Balancer → Nginx Ingress → Open WebUI
                                      ↓
                              Cert-Manager (SSL)
                                      ↓
                              MCP Proxy (reads Entra ID groups from JWT)
```

**Group Management:** Azure Portal → Entra ID → JWT token claims
**Problems:**
- High cost ($200-500/month)
- Requires Azure Portal for group management
- Complex Kubernetes configuration

### New: Docker Compose on Hetzner VPS

```
Internet → Traefik (SSL via Let's Encrypt)
              ↓
         traefikoidc (Microsoft OIDC)
              ↓
         auth-service (ForwardAuth)
              ↓
         PostgreSQL (group lookup)
              ↓
         Backend Services (Open WebUI, MCP Proxy, Admin Portal)
```

**Group Management:** Admin Portal UI → PostgreSQL database
**Benefits:**
- Low cost (~$10-30/month)
- Self-managed group/user administration
- Simple Docker Compose deployment
- Same multi-tenant capabilities

## Component Architecture

### 1. Traefik (Reverse Proxy + SSL)

**Role:** Entry point for all HTTP traffic

```yaml
# Handles:
# - SSL/TLS termination (Let's Encrypt ACME)
# - Routing to backend services
# - Middleware chain (auth, rate limiting)
```

**Routes:**
| Domain | Service |
|--------|---------|
| `app.domain.com` | Open WebUI |
| `mcp.domain.com` | MCP Proxy |
| `admin.domain.com` | Admin Portal |

### 2. traefikoidc (OIDC Plugin)

**Role:** Microsoft Entra ID authentication

```yaml
# Authenticates users via:
# - Microsoft Entra ID OAuth 2.0 / OIDC
# - Sets X-Forwarded-User header with user email
# - Redirects unauthenticated users to Microsoft login
```

### 3. auth-service (ForwardAuth)

**Role:** PostgreSQL group lookup, header enrichment

```
Input:  X-Forwarded-User: user@company.com (from traefikoidc)
Output: X-User-Email: user@company.com
        X-User-Groups: MCP-Admin,Tenant-Google
        X-User-Admin: true
```

**Flow:**
1. Receives forwarded request from Traefik
2. Extracts user email from `X-Forwarded-User`
3. Queries PostgreSQL for user's groups
4. Returns 200 with enriched headers (or 401 if user not found)

### 4. Admin Portal

**Role:** Web UI for user/group management

**Features:**
- User management (add/remove users)
- Group management (create/delete groups)
- Group membership (assign users to groups)
- Tenant mapping (assign groups to MCP servers)

**Access:** Admin-only (requires `MCP-Admin` group)

### 5. PostgreSQL Schema

```sql
-- User to group membership
CREATE TABLE user_group_membership (
    user_email VARCHAR(255) NOT NULL,
    group_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_email, group_name)
);

-- Group to tenant/server mapping (existing)
CREATE TABLE group_tenant_mapping (
    group_name VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (group_name, tenant_id)
);

-- Admin users
CREATE TABLE user_admin_status (
    user_email VARCHAR(255) PRIMARY KEY,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User visits app.domain.com                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Traefik receives request                                      │
│    - Terminates SSL                                              │
│    - Applies middleware chain                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. traefikoidc middleware                                        │
│    - Checks for valid OIDC session                               │
│    - If no session: redirect to Microsoft login                  │
│    - If session valid: set X-Forwarded-User header               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. auth-forwardauth middleware                                   │
│    - Calls auth-service with X-Forwarded-User                    │
│    - auth-service queries PostgreSQL for groups                  │
│    - Returns X-User-Email, X-User-Groups, X-User-Admin           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Backend service receives request with headers                 │
│    - Open WebUI: uses X-User-Email for user context              │
│    - MCP Proxy: filters servers by X-User-Groups                 │
│    - Admin Portal: checks X-User-Admin for access                │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Create Missing Components

| # | Component | Files | Priority |
|---|-----------|-------|----------|
| 1 | auth-service | `auth-service/main.py`, `Dockerfile`, `requirements.txt` | HIGH |
| 2 | admin-portal | `admin-portal/main.py`, `Dockerfile`, `requirements.txt`, templates | HIGH |
| 3 | Database schema | `scripts/init-db-hetzner.sql` | HIGH |
| 4 | Docker Compose | `docker-compose.hetzner.yml` | HIGH |
| 5 | Traefik config | `traefik/traefik.yml`, `traefik/dynamic/` | HIGH |
| 6 | Environment | `.env.hetzner.example` | MEDIUM |

### Phase 2: Local Testing

1. Run `docker compose -f docker-compose.hetzner.yml up -d`
2. Access Admin Portal at `http://localhost:8080`
3. Add test user and assign groups
4. Test MCP Proxy tool filtering
5. Verify Open WebUI integration

### Phase 3: Hetzner Deployment

1. Provision Hetzner VPS (4GB+ RAM, ~$10/month)
2. Install Docker and Docker Compose
3. Clone repository
4. Configure `.env` with production values
5. Set up DNS records
6. Run Docker Compose
7. Verify Let's Encrypt certificates

## File Structure (After Migration)

```
IO/
├── auth-service/
│   ├── main.py              # ForwardAuth service
│   ├── Dockerfile
│   └── requirements.txt
├── admin-portal/
│   ├── main.py              # User/group management UI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── templates/
│       ├── base.html
│       ├── users.html
│       ├── groups.html
│       └── mappings.html
├── traefik/
│   ├── traefik.yml          # Static config
│   └── dynamic/
│       ├── middlewares.yml  # Auth chain config
│       └── routers.yml      # Route definitions
├── scripts/
│   ├── init-db-hetzner.sql  # Database schema
│   └── seed_mcp_servers.py  # Existing seeder
├── docker-compose.yml       # Local development (current)
├── docker-compose.hetzner.yml # Hetzner production
└── .env.hetzner.example     # Environment template
```

## Key Differences from Kubernetes

| Aspect | Kubernetes | Hetzner Docker Compose |
|--------|------------|------------------------|
| SSL/TLS | Cert-Manager + Nginx | Traefik ACME |
| Auth | Entra ID JWT claims | traefikoidc + auth-service |
| Groups | Azure Portal | Admin Portal UI |
| Storage | PersistentVolumeClaims | Docker volumes |
| Networking | Kubernetes Services | Docker networks |
| Cost | $200-500/month | $10-30/month |

## Rollback Plan

If issues arise:
1. Keep Kubernetes cluster running during migration
2. Update DNS to point back to AKS load balancer
3. No data loss (PostgreSQL data persists)

## Security Considerations

1. **Traefik:** Enable HSTS, secure headers
2. **auth-service:** Internal network only (not exposed)
3. **Admin Portal:** Requires `MCP-Admin` group
4. **Database:** Strong password, internal network only
5. **OIDC:** Microsoft Entra ID handles authentication

## Next Steps After This Plan

1. [ ] Create auth-service implementation
2. [ ] Create admin-portal with basic UI
3. [ ] Write Traefik configuration
4. [ ] Create docker-compose.hetzner.yml
5. [ ] Test locally with simulated headers
6. [ ] Deploy to Hetzner VPS
7. [ ] Configure DNS and verify SSL
