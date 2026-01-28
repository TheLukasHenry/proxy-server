-- =============================================================================
-- MIGRATION: Move MCP Proxy tables from public to mcp_proxy schema
-- =============================================================================
--
-- Purpose: Isolate our custom tables from Open WebUI's Alembic migrations.
--          Open WebUI only manages the `public` schema, so moving our tables
--          to `mcp_proxy` schema ensures they are never touched by upstream updates.
--
-- SAFE TO RUN: This script is idempotent. It checks for existing tables and
--              only moves data that exists. Running it multiple times is safe.
--
-- Usage on Hetzner:
--   docker exec -i postgres psql -U openwebui -d openwebui < scripts/migrate-to-mcp-schema.sql
--
-- =============================================================================

BEGIN;

-- Step 1: Create the mcp_proxy schema
CREATE SCHEMA IF NOT EXISTS mcp_proxy;

-- Step 2: Create new tables in mcp_proxy schema
CREATE TABLE IF NOT EXISTS mcp_proxy.user_group_membership (
    user_email VARCHAR(255) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_email, group_name)
);

CREATE TABLE IF NOT EXISTS mcp_proxy.group_tenant_mapping (
    group_name VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (group_name, tenant_id)
);

CREATE TABLE IF NOT EXISTS mcp_proxy.user_admin_status (
    user_email VARCHAR(255) PRIMARY KEY,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Step 3: Copy data from public tables (if they exist) to mcp_proxy tables
-- Uses DO block to safely check if source tables exist before copying

DO $$
BEGIN
    -- Copy user_group_membership
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_group_membership') THEN
        INSERT INTO mcp_proxy.user_group_membership (user_email, group_name, created_at)
        SELECT user_email, group_name, created_at
        FROM public.user_group_membership
        ON CONFLICT (user_email, group_name) DO NOTHING;
        RAISE NOTICE 'Copied user_group_membership data to mcp_proxy schema';
    ELSE
        RAISE NOTICE 'No public.user_group_membership table found (skipping copy)';
    END IF;

    -- Copy group_tenant_mapping
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'group_tenant_mapping') THEN
        INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id, created_at)
        SELECT group_name, tenant_id, created_at
        FROM public.group_tenant_mapping
        ON CONFLICT (group_name, tenant_id) DO NOTHING;
        RAISE NOTICE 'Copied group_tenant_mapping data to mcp_proxy schema';
    ELSE
        RAISE NOTICE 'No public.group_tenant_mapping table found (skipping copy)';
    END IF;

    -- Copy user_admin_status
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_admin_status') THEN
        INSERT INTO mcp_proxy.user_admin_status (user_email, is_admin, created_at, updated_at)
        SELECT user_email, is_admin, created_at, updated_at
        FROM public.user_admin_status
        ON CONFLICT (user_email) DO UPDATE SET is_admin = EXCLUDED.is_admin;
        RAISE NOTICE 'Copied user_admin_status data to mcp_proxy schema';
    ELSE
        RAISE NOTICE 'No public.user_admin_status table found (skipping copy)';
    END IF;
END $$;

-- Step 4: Create indexes on new tables
CREATE INDEX IF NOT EXISTS idx_user_group_membership_email
    ON mcp_proxy.user_group_membership (user_email);
CREATE INDEX IF NOT EXISTS idx_user_group_membership_group
    ON mcp_proxy.user_group_membership (group_name);
CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_group
    ON mcp_proxy.group_tenant_mapping (group_name);
CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_tenant
    ON mcp_proxy.group_tenant_mapping (tenant_id);

-- Step 5: Create views in mcp_proxy schema
CREATE OR REPLACE VIEW mcp_proxy.user_server_access AS
SELECT DISTINCT
    ugm.user_email,
    gtm.tenant_id as server_id
FROM mcp_proxy.user_group_membership ugm
JOIN mcp_proxy.group_tenant_mapping gtm ON ugm.group_name = gtm.group_name;

CREATE OR REPLACE VIEW mcp_proxy.group_summary AS
SELECT
    g.group_name,
    COUNT(DISTINCT ugm.user_email) as user_count,
    COUNT(DISTINCT gtm.tenant_id) as server_count
FROM (
    SELECT DISTINCT group_name FROM mcp_proxy.user_group_membership
    UNION
    SELECT DISTINCT group_name FROM mcp_proxy.group_tenant_mapping
) g
LEFT JOIN mcp_proxy.user_group_membership ugm ON g.group_name = ugm.group_name
LEFT JOIN mcp_proxy.group_tenant_mapping gtm ON g.group_name = gtm.group_name
GROUP BY g.group_name
ORDER BY g.group_name;

-- Step 6: Drop old public tables (only if mcp_proxy tables have data)
DO $$
DECLARE
    mcp_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO mcp_count FROM mcp_proxy.group_tenant_mapping;

    IF mcp_count > 0 THEN
        -- Safe to drop old tables since data is in mcp_proxy
        DROP VIEW IF EXISTS public.user_server_access;
        DROP VIEW IF EXISTS public.group_summary;
        DROP TABLE IF EXISTS public.user_group_membership CASCADE;
        DROP TABLE IF EXISTS public.group_tenant_mapping CASCADE;
        DROP TABLE IF EXISTS public.user_admin_status CASCADE;
        RAISE NOTICE 'Dropped old public schema tables (data safely in mcp_proxy)';
    ELSE
        RAISE NOTICE 'WARNING: mcp_proxy.group_tenant_mapping is empty - NOT dropping public tables';
        RAISE NOTICE 'Run the seed script first, then re-run this migration';
    END IF;
END $$;

COMMIT;

-- Step 7: Verify migration
DO $$
DECLARE
    ugm_count INTEGER;
    gtm_count INTEGER;
    uas_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO ugm_count FROM mcp_proxy.user_group_membership;
    SELECT COUNT(*) INTO gtm_count FROM mcp_proxy.group_tenant_mapping;
    SELECT COUNT(*) INTO uas_count FROM mcp_proxy.user_admin_status;

    RAISE NOTICE '';
    RAISE NOTICE '=== MIGRATION COMPLETE ===';
    RAISE NOTICE 'mcp_proxy.user_group_membership: % rows', ugm_count;
    RAISE NOTICE 'mcp_proxy.group_tenant_mapping: % rows', gtm_count;
    RAISE NOTICE 'mcp_proxy.user_admin_status: % rows', uas_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Verify with: \dt mcp_proxy.*';
    RAISE NOTICE 'Open WebUI tables untouched in public schema';
END $$;
