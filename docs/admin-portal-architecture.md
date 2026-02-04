# MCP Admin Portal - Architecture

## Overview

The MCP Admin Portal is a web-based management interface for administering multi-tenant MCP configurations. It allows Open WebUI administrators to manage user-group assignments, group-server permissions, and tenant-specific API keys through a user-friendly interface.

**URL**: `https://ai-ui-dev.duckdns.org/mcp-admin/portal`

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER (User)                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  localStorage: { token: "eyJhbGc..." }  (JWT from Open WebUI login)     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CADDY (Reverse Proxy + SSL)                              │
│                           ai-ui-dev.duckdns.org                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  /                    →  Open WebUI (localhost:3100)                    │    │
│  │  /mcp-admin/*         →  MCP Proxy (localhost:8000)                     │    │
│  │  /admin/*             →  MCP Proxy (localhost:8000)                     │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────────────┐
│      OPEN WEBUI (:3100)           │   │           MCP PROXY (:8000)               │
│  ┌─────────────────────────────┐  │   │  ┌─────────────────────────────────────┐  │
│  │  - AI Chat Interface        │  │   │  │  /portal      → admin.html (UI)    │  │
│  │  - User Authentication      │  │   │  │  /admin/*     → Admin API (16 eps) │  │
│  │  - JWT Token Generation     │  │   │  │  /{server}/*  → MCP Tool Routing   │  │
│  │  - Microsoft OAuth          │  │   │  └─────────────────────────────────────┘  │
│  └─────────────────────────────┘  │   │                                           │
│                                   │   │  ┌─────────────────────────────────────┐  │
│  On Login:                        │   │  │  AUTH FLOW:                         │  │
│  1. User signs in (MS OAuth)      │   │  │  1. Read JWT from Authorization hdr │  │
│  2. JWT created & stored in       │   │  │  2. Validate with WEBUI_SECRET_KEY  │  │
│     localStorage                  │   │  │  3. Lookup user email from DB       │  │
│                                   │   │  │  4. Check admin role in Open WebUI  │  │
│                                   │   │  │  5. Allow/Deny request              │  │
└───────────────────────────────────┘   │  └─────────────────────────────────────┘  │
                                        └──────────────────┬────────────────────────┘
                                                           │
                                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          POSTGRESQL DATABASE                                     │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Schema: mcp_proxy                                                        │   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────────┐    │   │
│  │  │ user_group_membership   │  │ group_server_access                 │    │   │
│  │  │ - user_email            │  │ - group_name                        │    │   │
│  │  │ - group_name            │  │ - server_id                         │    │   │
│  │  └─────────────────────────┘  └─────────────────────────────────────┘    │   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────────┐    │   │
│  │  │ tenant_api_keys         │  │ tenant_server_endpoints             │    │   │
│  │  │ - tenant_id             │  │ - tenant_id                         │    │   │
│  │  │ - server_id             │  │ - server_id                         │    │   │
│  │  │ - key_name              │  │ - endpoint_url                      │    │   │
│  │  │ - key_value (encrypted) │  └─────────────────────────────────────┘    │   │
│  │  └─────────────────────────┘                                              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Schema: public (Open WebUI)                                              │   │
│  │  ┌─────────────────────────┐                                              │   │
│  │  │ user                    │  ← Admin check: role = 'admin'               │   │
│  │  │ - id, email, role       │                                              │   │
│  │  └─────────────────────────┘                                              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │  Caddy   │     │  MCP     │     │  Auth    │     │ Database │
│ Browser  │     │  Proxy   │     │  Proxy   │     │  Module  │     │          │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │                │
     │ 1. Login to Open WebUI         │                │                │
     │ ─────────────────────────────► │                │                │
     │                │                │                │                │
     │ 2. JWT stored in localStorage  │                │                │
     │ ◄───────────────────────────── │                │                │
     │                │                │                │                │
     │ 3. GET /mcp-admin/portal       │                │                │
     │ ──────────────►│                │                │                │
     │                │ 4. Route to    │                │                │
     │                │    mcp-proxy   │                │                │
     │                │ ──────────────►│                │                │
     │                │                │ 5. Serve       │                │
     │ 6. admin.html  │                │    HTML        │                │
     │ ◄──────────────────────────────│                │                │
     │                │                │                │                │
     │ 7. JS reads localStorage.token │                │                │
     │                │                │                │                │
     │ 8. GET /admin/users            │                │                │
     │    Authorization: Bearer <JWT> │                │                │
     │ ──────────────►│ ──────────────►│                │                │
     │                │                │ 9. Validate    │                │
     │                │                │    JWT         │                │
     │                │                │ ──────────────►│                │
     │                │                │                │ 10. Decode JWT │
     │                │                │                │     Get user_id│
     │                │                │                │ ──────────────►│
     │                │                │                │                │
     │                │                │                │ 11. Lookup     │
     │                │                │                │     email by id│
     │                │                │                │ ◄──────────────│
     │                │                │                │                │
     │                │                │                │ 12. Check      │
     │                │                │                │     role=admin │
     │                │                │                │ ──────────────►│
     │                │                │                │ ◄──────────────│
     │                │                │ 13. User info  │                │
     │                │                │ ◄──────────────│                │
     │                │                │                │                │
     │                │                │ 14. Query      │                │
     │                │                │     mcp_proxy  │                │
     │                │                │     tables     │                │
     │                │                │ ────────────────────────────────►
     │                │                │ ◄────────────────────────────────
     │                │                │                │                │
     │ 15. JSON Response (users list) │                │                │
     │ ◄──────────────────────────────│                │                │
     │                │                │                │                │
```

---

## Admin Portal Features

### Tab 1: Users & Groups
- View all users with their group memberships
- Add users to groups
- Remove users from groups
- Search/filter by email

### Tab 2: Groups & Servers
- View all groups with their server access
- Create new groups
- Edit group server permissions
- Delete groups (with confirmation)

### Tab 3: API Keys
- View tenant-specific API keys (masked)
- Add/update API keys per tenant-server
- Delete API keys
- Requires MCP-Admin group membership

### Tab 4: Dynamic Routing
- View endpoint overrides
- Configure per-tenant backend routing
- Example: MCP-GitHub → different container with different credentials

---

## Admin Portal API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/admin/users` | GET | List all users with groups | Open WebUI Admin |
| `/admin/users/groups` | POST | Add user to group | Open WebUI Admin |
| `/admin/users/groups` | DELETE | Remove user from group | Open WebUI Admin |
| `/admin/groups` | GET | List all groups with servers | Open WebUI Admin |
| `/admin/groups` | POST | Create new group | Open WebUI Admin |
| `/admin/groups/{name}` | PUT | Update group servers | Open WebUI Admin |
| `/admin/groups/{name}` | DELETE | Delete group | Open WebUI Admin |
| `/admin/servers` | GET | List available MCP servers | Open WebUI Admin |
| `/admin/tenant-keys` | GET | List tenant API keys | MCP-Admin Group |
| `/admin/tenant-keys` | POST | Add/update API key | MCP-Admin Group |
| `/admin/tenant-keys` | DELETE | Delete API key | MCP-Admin Group |
| `/admin/endpoints` | GET | List endpoint overrides | Open WebUI Admin |
| `/admin/endpoints` | POST | Add endpoint override | Open WebUI Admin |
| `/admin/endpoints` | DELETE | Delete endpoint override | Open WebUI Admin |

---

## Data Flow: Adding User to Group

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Admin     │    │   Admin     │    │  MCP Proxy  │    │  PostgreSQL │
│   Browser   │    │   Portal    │    │   Backend   │    │   Database  │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       │ 1. Click "Add    │                  │                  │
       │    User to Group"│                  │                  │
       │ ────────────────►│                  │                  │
       │                  │                  │                  │
       │ 2. Modal opens   │                  │                  │
       │    Enter email:  │                  │                  │
       │    "user@co.com" │                  │                  │
       │    Select group: │                  │                  │
       │    "MCP-GitHub"  │                  │                  │
       │                  │                  │                  │
       │ 3. Click Save    │                  │                  │
       │ ────────────────►│                  │                  │
       │                  │                  │                  │
       │                  │ 4. POST /admin/users/groups        │
       │                  │    { email, group_name }           │
       │                  │    + Authorization: Bearer <JWT>   │
       │                  │ ─────────────────►│                │
       │                  │                  │                  │
       │                  │                  │ 5. Validate JWT │
       │                  │                  │    Check admin  │
       │                  │                  │                  │
       │                  │                  │ 6. INSERT INTO  │
       │                  │                  │    user_group_  │
       │                  │                  │    membership   │
       │                  │                  │ ────────────────►
       │                  │                  │ ◄────────────────
       │                  │                  │                  │
       │                  │ 7. { status: "added" }             │
       │                  │ ◄─────────────────│                │
       │                  │                  │                  │
       │ 8. Toast:        │                  │                  │
       │    "User added!" │                  │                  │
       │    Table refresh │                  │                  │
       │ ◄────────────────│                  │                  │
       │                  │                  │                  │
```

---

## Key Files

```
mcp-proxy/
├── main.py                 # FastAPI app, includes admin_router
├── admin_api.py            # 16 admin endpoints
├── auth.py                 # JWT validation, user extraction
├── db.py                   # Database functions for admin ops
├── static/
│   └── admin.html          # Admin Portal SPA (Alpine.js + Tailwind)
└── tenants.py              # Server configurations

/etc/caddy/Caddyfile        # Routing rules for same-domain access
```

---

## Database Schema

### mcp_proxy.user_group_membership
```sql
CREATE TABLE user_group_membership (
    user_email VARCHAR(255) NOT NULL,
    group_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_email, group_name)
);
```

### mcp_proxy.group_server_access
```sql
CREATE TABLE group_server_access (
    group_name VARCHAR(100) NOT NULL,
    server_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_name, server_id)
);
```

### mcp_proxy.tenant_api_keys
```sql
CREATE TABLE tenant_api_keys (
    tenant_id VARCHAR(100) NOT NULL,
    server_id VARCHAR(100) NOT NULL,
    key_name VARCHAR(100) NOT NULL,
    key_value TEXT NOT NULL,  -- encrypted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, server_id, key_name)
);
```

### mcp_proxy.tenant_server_endpoints
```sql
CREATE TABLE tenant_server_endpoints (
    tenant_id VARCHAR(100) NOT NULL,
    server_id VARCHAR(100) NOT NULL,
    endpoint_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, server_id)
);
```

---

## Caddy Configuration

```caddyfile
ai-ui-dev.duckdns.org {
    # MCP Admin Portal - must be before the catch-all
    handle /mcp-admin* {
        uri strip_prefix /mcp-admin
        reverse_proxy localhost:8000 {
            header_up X-Forwarded-Prefix /mcp-admin
        }
    }

    # Admin API endpoints
    handle /admin/* {
        reverse_proxy localhost:8000
    }

    # Open WebUI (default)
    handle {
        reverse_proxy localhost:3100
    }
}
```

---

## Why This Architecture?

| Lukas's Requirement | Solution |
|---------------------|----------|
| "Same URL as Open WebUI" | Caddy routes `/mcp-admin/*` to MCP Proxy |
| "Use existing auth" | Portal reads JWT from localStorage (shared domain) |
| "Non-coders can manage" | Clean UI with modals, no SQL needed |
| "API keys not in .env" | Stored in database, managed via UI |
| "Survives Open WebUI updates" | Separate service, just shares auth |

---

## Security Considerations

1. **JWT Validation**: All admin endpoints validate the Open WebUI JWT token
2. **Admin Role Check**: User must have `role='admin'` in Open WebUI's user table
3. **MCP-Admin Group**: Sensitive operations (API keys) require MCP-Admin group membership
4. **Same-Origin**: Portal and Open WebUI share the same domain, enabling secure token sharing
5. **HTTPS**: All traffic encrypted via Caddy's automatic SSL

---

## Deployment Checklist

- [x] Deploy admin_api.py to mcp-proxy
- [x] Deploy admin.html to mcp-proxy/static/
- [x] Update main.py to include admin_router
- [x] Update db.py with admin functions
- [x] Configure Caddy routing
- [x] Set `API_GATEWAY_MODE=false` for JWT validation
- [x] Open port 8000 in Hetzner firewall
- [x] Test all 4 tabs in browser
