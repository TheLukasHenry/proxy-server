-- =============================================================================
-- MCP Proxy - Hetzner Database Schema
-- =============================================================================
--
-- This script initializes the database tables for the Hetzner architecture:
--
-- Tables:
--   user_group_membership  - Which users belong to which groups
--   group_tenant_mapping   - Which groups can access which MCP servers
--   user_admin_status      - Which users are admins
--
-- Unlike the Azure/Kubernetes approach where groups come from Entra ID tokens,
-- here groups are managed directly in PostgreSQL via the Admin Portal.
--
-- =============================================================================

-- Enable pgvector extension (for Open WebUI RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- USER GROUP MEMBERSHIP
-- =============================================================================
-- Which users belong to which groups
-- Example: alice@company.com belongs to MCP-GitHub, MCP-Admin

CREATE TABLE IF NOT EXISTS user_group_membership (
    user_email VARCHAR(255) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_email, group_name)
);

-- Index for quick lookups by user
CREATE INDEX IF NOT EXISTS idx_user_group_membership_email
    ON user_group_membership (user_email);

-- Index for quick lookups by group
CREATE INDEX IF NOT EXISTS idx_user_group_membership_group
    ON user_group_membership (group_name);

-- =============================================================================
-- GROUP TENANT MAPPING
-- =============================================================================
-- Which groups can access which MCP servers
-- Example: MCP-GitHub group can access 'github' server

CREATE TABLE IF NOT EXISTS group_tenant_mapping (
    group_name VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (group_name, tenant_id)
);

-- Index for quick lookups by group
CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_group
    ON group_tenant_mapping (group_name);

-- Index for quick lookups by tenant
CREATE INDEX IF NOT EXISTS idx_group_tenant_mapping_tenant
    ON group_tenant_mapping (tenant_id);

-- =============================================================================
-- USER ADMIN STATUS
-- =============================================================================
-- Which users are administrators (can access Admin Portal)

CREATE TABLE IF NOT EXISTS user_admin_status (
    user_email VARCHAR(255) PRIMARY KEY,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- SEED DATA - Default Groups and Mappings
-- =============================================================================

-- Default groups
INSERT INTO user_group_membership (user_email, group_name) VALUES
    ('admin@example.com', 'MCP-Admin'),
    ('admin@example.com', 'MCP-GitHub'),
    ('admin@example.com', 'MCP-Filesystem')
ON CONFLICT (user_email, group_name) DO NOTHING;

-- Make default admin
INSERT INTO user_admin_status (user_email, is_admin) VALUES
    ('admin@example.com', true)
ON CONFLICT (user_email) DO UPDATE SET is_admin = true;

-- Default group -> server mappings
-- MCP-Admin gets access to everything
INSERT INTO group_tenant_mapping (group_name, tenant_id) VALUES
    ('MCP-Admin', 'github'),
    ('MCP-Admin', 'filesystem'),
    ('MCP-Admin', 'linear'),
    ('MCP-Admin', 'notion'),
    ('MCP-Admin', 'atlassian'),
    ('MCP-Admin', 'asana'),
    ('MCP-Admin', 'gitlab'),
    ('MCP-Admin', 'slack')
ON CONFLICT (group_name, tenant_id) DO NOTHING;

-- MCP-GitHub gets access to github only
INSERT INTO group_tenant_mapping (group_name, tenant_id) VALUES
    ('MCP-GitHub', 'github')
ON CONFLICT (group_name, tenant_id) DO NOTHING;

-- MCP-Filesystem gets access to filesystem only
INSERT INTO group_tenant_mapping (group_name, tenant_id) VALUES
    ('MCP-Filesystem', 'filesystem')
ON CONFLICT (group_name, tenant_id) DO NOTHING;

-- =============================================================================
-- HELPER VIEWS
-- =============================================================================

-- View: User permissions (which servers each user can access)
CREATE OR REPLACE VIEW user_server_access AS
SELECT DISTINCT
    ugm.user_email,
    gtm.tenant_id as server_id
FROM user_group_membership ugm
JOIN group_tenant_mapping gtm ON ugm.group_name = gtm.group_name;

-- View: Group summary (user count and server count per group)
CREATE OR REPLACE VIEW group_summary AS
SELECT
    g.group_name,
    COUNT(DISTINCT ugm.user_email) as user_count,
    COUNT(DISTINCT gtm.tenant_id) as server_count
FROM (
    SELECT DISTINCT group_name FROM user_group_membership
    UNION
    SELECT DISTINCT group_name FROM group_tenant_mapping
) g
LEFT JOIN user_group_membership ugm ON g.group_name = ugm.group_name
LEFT JOIN group_tenant_mapping gtm ON g.group_name = gtm.group_name
GROUP BY g.group_name
ORDER BY g.group_name;

-- =============================================================================
-- DONE
-- =============================================================================

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'MCP Proxy Hetzner database initialized successfully!';
    RAISE NOTICE 'Tables created: user_group_membership, group_tenant_mapping, user_admin_status';
    RAISE NOTICE 'Views created: user_server_access, group_summary';
END $$;
