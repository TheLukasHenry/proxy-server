-- =============================================================================
-- MCP Proxy - Hetzner Database Schema
-- =============================================================================
--
-- This script initializes the database tables for the Hetzner architecture.
--
-- SCHEMA ISOLATION:
--   All MCP Proxy tables live in the `mcp_proxy` schema, completely isolated
--   from Open WebUI's `public` schema. This means Open WebUI's Alembic
--   migrations will NEVER touch our tables.
--
-- Tables (in mcp_proxy schema):
--   user_group_membership  - Which users belong to which groups
--   group_tenant_mapping   - Which groups can access which MCP servers
--   user_admin_status      - Which users are admins
--
-- Cross-schema access:
--   Read-only access to public."user" table for JWT email lookup
--
-- =============================================================================

-- Enable pgvector extension (for Open WebUI RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- CREATE MCP_PROXY SCHEMA
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS mcp_proxy;

-- =============================================================================
-- USER GROUP MEMBERSHIP
-- =============================================================================
-- Which users belong to which groups
-- Example: alice@company.com belongs to MCP-GitHub, MCP-Admin

CREATE TABLE IF NOT EXISTS mcp_proxy.user_group_membership (
    user_email VARCHAR(255) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_email, group_name)
);

-- Index for quick lookups by user
CREATE INDEX IF NOT EXISTS idx_user_group_membership_email
    ON mcp_proxy.user_group_membership (user_email);

-- Index for quick lookups by group
CREATE INDEX IF NOT EXISTS idx_user_group_membership_group
    ON mcp_proxy.user_group_membership (group_name);

-- =============================================================================
-- GROUP TENANT MAPPING
-- =============================================================================
-- Which groups can access which MCP servers
-- Example: MCP-GitHub group can access 'github' server

CREATE TABLE IF NOT EXISTS mcp_proxy.group_tenant_mapping (
    group_name VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (group_name, tenant_id)
);

-- Index for quick lookups by group
CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_group
    ON mcp_proxy.group_tenant_mapping (group_name);

-- Index for quick lookups by tenant
CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_tenant
    ON mcp_proxy.group_tenant_mapping (tenant_id);

-- =============================================================================
-- USER ADMIN STATUS
-- =============================================================================
-- Which users are administrators (can access Admin Portal)

CREATE TABLE IF NOT EXISTS mcp_proxy.user_admin_status (
    user_email VARCHAR(255) PRIMARY KEY,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- SEED DATA - Default Groups and Mappings
-- =============================================================================

-- Default groups
INSERT INTO mcp_proxy.user_group_membership (user_email, group_name) VALUES
    ('admin@example.com', 'MCP-Admin'),
    ('admin@example.com', 'MCP-GitHub'),
    ('admin@example.com', 'MCP-Filesystem')
ON CONFLICT (user_email, group_name) DO NOTHING;

-- Make default admin
INSERT INTO mcp_proxy.user_admin_status (user_email, is_admin) VALUES
    ('admin@example.com', true)
ON CONFLICT (user_email) DO UPDATE SET is_admin = true;

-- Default group -> server mappings
-- MCP-Admin gets access to everything
INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id) VALUES
    ('MCP-Admin', 'github'),
    ('MCP-Admin', 'filesystem'),
    ('MCP-Admin', 'linear'),
    ('MCP-Admin', 'notion'),
    ('MCP-Admin', 'atlassian'),
    ('MCP-Admin', 'asana'),
    ('MCP-Admin', 'gitlab'),
    ('MCP-Admin', 'slack'),
    ('MCP-Admin', 'clickup'),
    ('MCP-Admin', 'trello'),
    ('MCP-Admin', 'sonarqube'),
    ('MCP-Admin', 'excel-creator'),
    ('MCP-Admin', 'dashboard')
ON CONFLICT (group_name, tenant_id) DO NOTHING;

-- MCP-GitHub gets access to github only
INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id) VALUES
    ('MCP-GitHub', 'github')
ON CONFLICT (group_name, tenant_id) DO NOTHING;

-- MCP-Filesystem gets access to filesystem only
INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id) VALUES
    ('MCP-Filesystem', 'filesystem')
ON CONFLICT (group_name, tenant_id) DO NOTHING;

-- =============================================================================
-- TOOL EMBEDDINGS (for Speakeasy meta-tools semantic search)
-- =============================================================================
-- Stores vector embeddings of tool names/descriptions for pgvector similarity search.
-- Used by search_tools meta-tool to find relevant tools from natural language queries.

CREATE TABLE IF NOT EXISTS mcp_proxy.tool_embeddings (
    tool_name VARCHAR(512) PRIMARY KEY,
    server_id VARCHAR(255) NOT NULL,
    display_name VARCHAR(512),
    description TEXT,
    embedding vector(384),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for quick lookups by server
CREATE INDEX IF NOT EXISTS idx_tool_embeddings_server
    ON mcp_proxy.tool_embeddings (server_id);

-- Note: ivfflat vector index is created after data is inserted
-- (requires non-empty table). The tool_embeddings module handles this.

-- =============================================================================
-- HELPER VIEWS (in mcp_proxy schema)
-- =============================================================================

-- View: User permissions (which servers each user can access)
CREATE OR REPLACE VIEW mcp_proxy.user_server_access AS
SELECT DISTINCT
    ugm.user_email,
    gtm.tenant_id as server_id
FROM mcp_proxy.user_group_membership ugm
JOIN mcp_proxy.group_tenant_mapping gtm ON ugm.group_name = gtm.group_name;

-- View: Group summary (user count and server count per group)
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

-- =============================================================================
-- DONE
-- =============================================================================

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'MCP Proxy database initialized in mcp_proxy schema!';
    RAISE NOTICE 'Schema: mcp_proxy (isolated from Open WebUI public schema)';
    RAISE NOTICE 'Tables: mcp_proxy.user_group_membership, mcp_proxy.group_tenant_mapping, mcp_proxy.user_admin_status';
    RAISE NOTICE 'Views: mcp_proxy.user_server_access, mcp_proxy.group_summary';
END $$;
