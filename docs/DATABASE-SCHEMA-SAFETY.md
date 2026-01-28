# Database Schema Safety — Open WebUI Upstream Updates

## Schema Layout

Our PostgreSQL database (`openwebui`) has two schemas:

| Schema | Owner | Purpose |
|---|---|---|
| `public` | Open WebUI | All Open WebUI tables (users, chats, models, etc.) managed by Alembic migrations |
| `mcp_proxy` | MCP Proxy | Our custom tables (groups, tenant mappings, admin status) — NEVER touched by Open WebUI |

### Our Tables (mcp_proxy schema)

```
mcp_proxy.user_group_membership  — Which users belong to which groups
mcp_proxy.group_tenant_mapping   — Which groups can access which MCP servers
mcp_proxy.user_admin_status      — Which users are admins
mcp_proxy.user_server_access     — View: user → server access (derived)
mcp_proxy.group_summary          — View: group stats (derived)
```

### Open WebUI Tables (public schema)

```
public."user"                    — User accounts (we READ this for JWT email lookup)
public.chat                      — Chat history
public.model                     — Model configurations
public.tool                      — Tool definitions
public.alembic_version           — Migration tracking
... (50+ other tables)
```

## Why This Is Safe

1. **Open WebUI's Alembic only manages `public` schema.** Its migration scripts use `op.create_table()`, `op.add_column()`, etc. which default to the `public` schema. It has no knowledge of `mcp_proxy` schema.

2. **PostgreSQL schemas are fully isolated namespaces.** A `DROP TABLE user_group_membership` in a migration would only affect `public.user_group_membership` (which doesn't exist), not `mcp_proxy.user_group_membership`.

3. **Our code explicitly qualifies all table names** with `mcp_proxy.` prefix — there's no ambiguity about which schema we're reading from.

4. **Cross-schema reads are native PostgreSQL.** We read `public."user"` for email lookup and write to `mcp_proxy.*` tables. Both work with the same database connection.

## How to Safely Update Open WebUI

### Step 1: Pre-Update Check

```bash
# SSH into Hetzner
ssh root@46.224.193.25

# Verify our tables exist and have data
docker exec postgres psql -U openwebui -d openwebui -c "
  SELECT 'user_group_membership' as tbl, COUNT(*) as rows FROM mcp_proxy.user_group_membership
  UNION ALL
  SELECT 'group_tenant_mapping', COUNT(*) FROM mcp_proxy.group_tenant_mapping
  UNION ALL
  SELECT 'user_admin_status', COUNT(*) FROM mcp_proxy.user_admin_status;
"

# Save a backup of our data
docker exec postgres pg_dump -U openwebui -d openwebui --schema=mcp_proxy > /root/mcp_proxy_backup_$(date +%Y%m%d).sql
```

### Step 2: Update Open WebUI

```bash
cd /root/IO

# Pull latest image
docker compose -f docker-compose.hetzner-unified.yml pull open-webui

# Restart Open WebUI (it will run Alembic migrations automatically)
docker compose -f docker-compose.hetzner-unified.yml up -d open-webui

# Watch logs for migration success
docker logs -f open-webui 2>&1 | head -50
```

### Step 3: Post-Update Verification

```bash
# Verify our tables are untouched
docker exec postgres psql -U openwebui -d openwebui -c "
  SELECT 'user_group_membership' as tbl, COUNT(*) as rows FROM mcp_proxy.user_group_membership
  UNION ALL
  SELECT 'group_tenant_mapping', COUNT(*) FROM mcp_proxy.group_tenant_mapping
  UNION ALL
  SELECT 'user_admin_status', COUNT(*) FROM mcp_proxy.user_admin_status;
"

# Verify Open WebUI is healthy
curl -s http://localhost:3100/api/version

# Verify MCP Proxy still works
curl -s http://localhost:8000/health | python3 -m json.tool

# Test a tool call
curl -s -X POST http://localhost:8000/refresh
```

### Step 4: If Something Goes Wrong

```bash
# Restore our data from backup
docker exec -i postgres psql -U openwebui -d openwebui < /root/mcp_proxy_backup_YYYYMMDD.sql

# Or restore from init script (loses custom user assignments, keeps default mappings)
docker exec -i postgres psql -U openwebui -d openwebui < /root/IO/scripts/init-db-hetzner.sql

# Re-seed from mcp-servers.json
docker compose -f docker-compose.hetzner-unified.yml run --rm db-init
```

## Schema Verification Script

Run `scripts/check-mcp-schema.sh` to verify schema health:

```bash
bash scripts/check-mcp-schema.sh
```

This checks:
- `mcp_proxy` schema exists
- All 3 tables exist with correct columns
- Tables have data (not empty)
- Cross-schema read to `public."user"` works

## Migration from Public Schema

If tables are still in the `public` schema (pre-migration state), run:

```bash
docker exec -i postgres psql -U openwebui -d openwebui < scripts/migrate-to-mcp-schema.sql
```

This idempotent script:
1. Creates `mcp_proxy` schema
2. Creates new tables in `mcp_proxy`
3. Copies data from `public` tables (if they exist)
4. Creates indexes and views
5. Drops old `public` tables (only after verifying data was copied)

## Key Rules

1. **NEVER create tables in the `public` schema** — that's Open WebUI's territory
2. **ALWAYS use `mcp_proxy.` prefix** in SQL queries
3. **Backup before updating** Open WebUI: `pg_dump --schema=mcp_proxy`
4. **Read-only access to `public."user"`** is safe — we only SELECT from it
5. **The `db-init` container** re-seeds `mcp_proxy.group_tenant_mapping` on every deploy
