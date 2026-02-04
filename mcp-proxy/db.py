"""
Database module for MCP Proxy tenant access lookups.

Uses PostgreSQL to store user-tenant access mappings.
This provides secure, database-backed access control instead of relying on
headers or token groups.
"""

import os
import asyncpg
from typing import Optional
from functools import lru_cache

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://openwebui:localdevpassword@postgresql:5432/openwebui")


def log(msg: str):
    """Debug logging."""
    print(f"[DB] {msg}")


_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _pool
    if _pool is None:
        log(f"Creating connection pool...")
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=30
        )
        log("Connection pool created")
    return _pool


async def get_user_tenants(email: str) -> list[str]:
    """
    Get list of tenant IDs the user has access to.

    Args:
        email: User's email address

    Returns:
        List of tenant IDs (e.g., ['Tenant-Google', 'github', 'filesystem'])
    """
    if not email:
        return []

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tenant_id FROM mcp_proxy.user_tenant_access
                WHERE LOWER(user_email) = LOWER($1)
                """,
                email
            )
            tenants = [row['tenant_id'] for row in rows]
            log(f"User {email} has access to: {tenants}")
            return tenants
    except Exception as e:
        log(f"Error fetching tenants for {email}: {e}")
        return []


async def get_user_access_level(email: str, tenant_id: str) -> Optional[str]:
    """
    Get user's access level for a specific tenant.

    Args:
        email: User's email address
        tenant_id: Tenant ID to check

    Returns:
        Access level ('admin', 'read', etc.) or None if no access
    """
    if not email or not tenant_id:
        return None

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT access_level FROM mcp_proxy.user_tenant_access
                WHERE LOWER(user_email) = LOWER($1) AND tenant_id = $2
                """,
                email, tenant_id
            )
            return row['access_level'] if row else None
    except Exception as e:
        log(f"Error fetching access level: {e}")
        return None


async def user_has_tenant_access(email: str, tenant_id: str) -> bool:
    """
    Check if user has access to a specific tenant.

    Args:
        email: User's email address
        tenant_id: Tenant ID to check

    Returns:
        True if user has access, False otherwise
    """
    access_level = await get_user_access_level(email, tenant_id)
    return access_level is not None


async def add_user_tenant_access(email: str, tenant_id: str, access_level: str = 'read') -> bool:
    """
    Add tenant access for a user.

    Args:
        email: User's email address
        tenant_id: Tenant ID to grant access to
        access_level: Access level ('admin', 'read', etc.)

    Returns:
        True if added successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp_proxy.user_tenant_access (user_email, tenant_id, access_level)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_email, tenant_id) DO UPDATE SET access_level = $3
                """,
                email, tenant_id, access_level
            )
            log(f"Added access: {email} -> {tenant_id} ({access_level})")
            return True
    except Exception as e:
        log(f"Error adding access: {e}")
        return False


async def close_pool():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        log("Connection pool closed")


# =============================================================================
# USER GROUP MEMBERSHIP LOOKUP
# =============================================================================

async def get_user_groups(email: str) -> list[str]:
    """
    Look up a user's group memberships from the database.

    When X-User-Groups header is empty (e.g., Open WebUI doesn't pass groups),
    we can still determine the user's groups from the user_group_membership table.

    Args:
        email: User's email address

    Returns:
        List of group names the user belongs to
    """
    if not email:
        return []

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT group_name FROM mcp_proxy.user_group_membership
                WHERE LOWER(user_email) = LOWER($1)
                """,
                email
            )
            groups = [row['group_name'] for row in rows]
            log(f"User {email} groups from DB: {groups}")
            return groups
    except Exception as e:
        log(f"Error fetching user groups for {email}: {e}")
        return []


# =============================================================================
# GROUP-TENANT MAPPING FUNCTIONS
# =============================================================================

async def get_tenants_from_groups(groups: list[str]) -> list[str]:
    """
    Get list of tenant IDs from group names.

    Args:
        groups: List of group names (e.g., ['Tenant-Google', 'MCP-GitHub'])

    Returns:
        List of unique tenant IDs the groups have access to
    """
    if not groups:
        return []

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Use ANY to match any of the provided groups
            rows = await conn.fetch(
                """
                SELECT DISTINCT tenant_id FROM mcp_proxy.group_tenant_mapping
                WHERE group_name = ANY($1)
                """,
                groups
            )
            tenants = [row['tenant_id'] for row in rows]
            log(f"Groups {groups} have access to: {tenants}")
            return tenants
    except Exception as e:
        log(f"Error fetching tenants from groups: {e}")
        return []


async def group_has_tenant_access(groups: list[str], tenant_id: str) -> bool:
    """
    Check if any of the groups has access to a specific tenant.

    Args:
        groups: List of group names
        tenant_id: Tenant ID to check

    Returns:
        True if any group has access, False otherwise
    """
    if not groups or not tenant_id:
        return False

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM mcp_proxy.group_tenant_mapping
                WHERE group_name = ANY($1) AND tenant_id = $2
                LIMIT 1
                """,
                groups, tenant_id
            )
            return row is not None
    except Exception as e:
        log(f"Error checking group tenant access: {e}")
        return False


async def add_group_tenant_mapping(group_name: str, tenant_id: str) -> bool:
    """
    Add a group-tenant mapping.

    Args:
        group_name: Group name (e.g., 'Tenant-Google')
        tenant_id: Tenant/server ID (e.g., 'github')

    Returns:
        True if added successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id)
                VALUES ($1, $2)
                ON CONFLICT (group_name, tenant_id) DO NOTHING
                """,
                group_name, tenant_id
            )
            log(f"Added group mapping: {group_name} -> {tenant_id}")
            return True
    except Exception as e:
        log(f"Error adding group mapping: {e}")
        return False


async def remove_group_tenant_mapping(group_name: str, tenant_id: str) -> bool:
    """
    Remove a group-tenant mapping.

    Args:
        group_name: Group name
        tenant_id: Tenant/server ID

    Returns:
        True if removed successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM mcp_proxy.group_tenant_mapping
                WHERE group_name = $1 AND tenant_id = $2
                """,
                group_name, tenant_id
            )
            log(f"Removed group mapping: {group_name} -> {tenant_id}")
            return True
    except Exception as e:
        log(f"Error removing group mapping: {e}")
        return False


async def get_all_group_mappings() -> dict[str, list[str]]:
    """
    Get all group-tenant mappings.

    Returns:
        Dictionary mapping group names to lists of tenant IDs
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT group_name, tenant_id FROM mcp_proxy.group_tenant_mapping
                ORDER BY group_name, tenant_id
                """
            )
            mappings = {}
            for row in rows:
                group = row['group_name']
                tenant = row['tenant_id']
                if group not in mappings:
                    mappings[group] = []
                mappings[group].append(tenant)
            return mappings
    except Exception as e:
        log(f"Error fetching all group mappings: {e}")
        return {}


# =============================================================================
# TENANT-SPECIFIC API KEYS (US-011)
# =============================================================================

async def get_tenant_api_key(tenant_id: str, server_id: str, key_name: str) -> Optional[str]:
    """
    Get a tenant-specific API key for a server.

    Args:
        tenant_id: Tenant/group name (e.g., 'Tenant-Google')
        server_id: Server ID (e.g., 'github')
        key_name: Key name (e.g., 'GITHUB_TOKEN')

    Returns:
        The API key value or None if not found
    """
    if not tenant_id or not server_id or not key_name:
        return None

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT key_value FROM mcp_proxy.tenant_server_keys
                WHERE tenant_id = $1 AND server_id = $2 AND key_name = $3
                """,
                tenant_id, server_id, key_name
            )
            if row:
                log(f"Found tenant-specific key: {tenant_id} -> {server_id} -> {key_name}")
                return row['key_value']
            return None
    except Exception as e:
        log(f"Error fetching tenant API key: {e}")
        return None


async def get_tenant_api_keys_for_server(tenant_ids: list[str], server_id: str) -> dict[str, str]:
    """
    Get all tenant-specific API keys for a server from multiple tenants.
    Returns the first matching tenant's keys (priority by order in list).

    Args:
        tenant_ids: List of tenant/group names to check (e.g., ['Tenant-Google', 'MCP-GitHub'])
        server_id: Server ID (e.g., 'github')

    Returns:
        Dictionary of key_name -> key_value for the first matching tenant
    """
    if not tenant_ids or not server_id:
        return {}

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Get all keys for matching tenants, ordered by tenant_id position in list
            rows = await conn.fetch(
                """
                SELECT tenant_id, key_name, key_value
                FROM mcp_proxy.tenant_server_keys
                WHERE tenant_id = ANY($1) AND server_id = $2
                ORDER BY array_position($1::varchar[], tenant_id)
                """,
                tenant_ids, server_id
            )

            if not rows:
                return {}

            # Return keys from the first matching tenant
            first_tenant = rows[0]['tenant_id']
            keys = {}
            for row in rows:
                if row['tenant_id'] == first_tenant:
                    keys[row['key_name']] = row['key_value']

            log(f"Found {len(keys)} tenant-specific keys for {first_tenant} -> {server_id}")
            return keys
    except Exception as e:
        log(f"Error fetching tenant API keys: {e}")
        return {}


async def set_tenant_api_key(tenant_id: str, server_id: str, key_name: str, key_value: str) -> bool:
    """
    Set a tenant-specific API key for a server.

    Args:
        tenant_id: Tenant/group name (e.g., 'Tenant-Google')
        server_id: Server ID (e.g., 'github')
        key_name: Key name (e.g., 'GITHUB_TOKEN')
        key_value: The API key value

    Returns:
        True if set successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp_proxy.tenant_server_keys (tenant_id, server_id, key_name, key_value, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (tenant_id, server_id, key_name)
                DO UPDATE SET key_value = $4, updated_at = NOW()
                """,
                tenant_id, server_id, key_name, key_value
            )
            log(f"Set tenant API key: {tenant_id} -> {server_id} -> {key_name}")
            return True
    except Exception as e:
        log(f"Error setting tenant API key: {e}")
        return False


async def delete_tenant_api_key(tenant_id: str, server_id: str, key_name: str) -> bool:
    """
    Delete a tenant-specific API key.

    Args:
        tenant_id: Tenant/group name
        server_id: Server ID
        key_name: Key name

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM mcp_proxy.tenant_server_keys
                WHERE tenant_id = $1 AND server_id = $2 AND key_name = $3
                """,
                tenant_id, server_id, key_name
            )
            log(f"Deleted tenant API key: {tenant_id} -> {server_id} -> {key_name}")
            return True
    except Exception as e:
        log(f"Error deleting tenant API key: {e}")
        return False


async def get_all_tenant_keys() -> list[dict]:
    """
    Get all tenant-specific API keys (without values, for admin display).

    Returns:
        List of {tenant_id, server_id, key_name, updated_at}
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tenant_id, server_id, key_name,
                       CASE WHEN key_value IS NOT NULL THEN '***' ELSE NULL END as has_value,
                       updated_at
                FROM mcp_proxy.tenant_server_keys
                ORDER BY tenant_id, server_id, key_name
                """
            )
            return [dict(row) for row in rows]
    except Exception as e:
        log(f"Error fetching all tenant keys: {e}")
        return []


async def get_tenant_keys_by_tenant(tenant_id: str) -> list[dict]:
    """
    Get all API keys for a specific tenant (without values).

    Args:
        tenant_id: Tenant/group name

    Returns:
        List of {server_id, key_name, updated_at}
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT server_id, key_name, updated_at
                FROM mcp_proxy.tenant_server_keys
                WHERE tenant_id = $1
                ORDER BY server_id, key_name
                """,
                tenant_id
            )
            return [dict(row) for row in rows]
    except Exception as e:
        log(f"Error fetching tenant keys for {tenant_id}: {e}")
        return []


# =============================================================================
# TENANT-SPECIFIC SERVER ENDPOINTS (US-011: Data Isolation - Dynamic Routing)
# =============================================================================

async def get_tenant_endpoint_override(tenant_ids: list[str], server_id: str) -> Optional[str]:
    """
    Get tenant-specific endpoint URL override for a server.

    This enables dynamic routing: same tool name (e.g., github_get_me) can route
    to different backend containers based on user's tenant/group.

    Args:
        tenant_ids: List of tenant/group names to check (priority order)
        server_id: Server ID (e.g., 'github')

    Returns:
        Override endpoint URL if found, None otherwise
    """
    if not tenant_ids or not server_id:
        return None

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Check each tenant in priority order
            row = await conn.fetchrow(
                """
                SELECT endpoint_url FROM mcp_proxy.tenant_server_endpoints
                WHERE tenant_id = ANY($1) AND server_id = $2
                ORDER BY array_position($1::varchar[], tenant_id)
                LIMIT 1
                """,
                tenant_ids, server_id
            )
            if row:
                log(f"[DYNAMIC-ROUTING] Override for {server_id}: {row['endpoint_url']} (tenant: {tenant_ids})")
                return row['endpoint_url']
            return None
    except Exception as e:
        log(f"Error fetching tenant endpoint override: {e}")
        return None


async def set_tenant_endpoint_override(tenant_id: str, server_id: str, endpoint_url: str) -> bool:
    """
    Set a tenant-specific endpoint URL override.

    Args:
        tenant_id: Tenant/group name (e.g., 'MCP-GitHub')
        server_id: Server ID (e.g., 'github')
        endpoint_url: Override URL (e.g., 'http://mcp-github-tenant:8000')

    Returns:
        True if set successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp_proxy.tenant_server_endpoints (tenant_id, server_id, endpoint_url)
                VALUES ($1, $2, $3)
                ON CONFLICT (tenant_id, server_id) DO UPDATE SET endpoint_url = $3
                """,
                tenant_id, server_id, endpoint_url
            )
            log(f"Set endpoint override: {tenant_id} -> {server_id} -> {endpoint_url}")
            return True
    except Exception as e:
        log(f"Error setting tenant endpoint override: {e}")
        return False


async def get_all_tenant_endpoints() -> list[dict]:
    """Get all tenant endpoint overrides for admin display."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT tenant_id, server_id, endpoint_url, created_at
                FROM mcp_proxy.tenant_server_endpoints
                ORDER BY tenant_id, server_id
                """
            )
            return [dict(row) for row in rows]
    except Exception as e:
        log(f"Error fetching all tenant endpoints: {e}")
        return []


async def delete_tenant_endpoint_override(tenant_id: str, server_id: str) -> bool:
    """
    Delete a tenant-specific endpoint override.

    Args:
        tenant_id: Tenant/group name
        server_id: Server ID

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM mcp_proxy.tenant_server_endpoints
                WHERE tenant_id = $1 AND server_id = $2
                """,
                tenant_id, server_id
            )
            log(f"Deleted endpoint override: {tenant_id} -> {server_id}")
            return True
    except Exception as e:
        log(f"Error deleting tenant endpoint override: {e}")
        return False


# =============================================================================
# ADMIN PORTAL: OPEN WEBUI ADMIN VERIFICATION
# =============================================================================

async def is_openwebui_admin(email: str) -> bool:
    """
    Check if user is an Open WebUI admin by checking the public.user table.

    Args:
        email: User's email address

    Returns:
        True if user has role='admin' in Open WebUI, False otherwise
    """
    if not email:
        return False

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT role FROM public."user"
                WHERE LOWER(email) = LOWER($1)
                """,
                email
            )
            if row and row['role'] == 'admin':
                log(f"User {email} is Open WebUI admin")
                return True
            log(f"User {email} is NOT Open WebUI admin (role={row['role'] if row else 'not found'})")
            return False
    except Exception as e:
        log(f"Error checking admin status for {email}: {e}")
        return False


# =============================================================================
# ADMIN PORTAL: USER-GROUP MANAGEMENT
# =============================================================================

async def get_all_users_with_groups() -> list[dict]:
    """
    Get all users with their group memberships.

    Returns:
        List of {email, groups: [group_name, ...], updated_at}
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_email,
                       array_agg(group_name ORDER BY group_name) as groups,
                       MAX(created_at) as updated_at
                FROM mcp_proxy.user_group_membership
                GROUP BY user_email
                ORDER BY user_email
                """
            )
            return [
                {
                    "email": row['user_email'],
                    "groups": list(row['groups']) if row['groups'] else [],
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
                }
                for row in rows
            ]
    except Exception as e:
        log(f"Error fetching all users with groups: {e}")
        return []


async def add_user_to_group(email: str, group_name: str) -> bool:
    """
    Add a user to a group.

    Args:
        email: User's email address
        group_name: Group name to add user to

    Returns:
        True if added successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp_proxy.user_group_membership (user_email, group_name, created_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_email, group_name) DO NOTHING
                """,
                email, group_name
            )
            log(f"Added user to group: {email} -> {group_name}")
            return True
    except Exception as e:
        log(f"Error adding user to group: {e}")
        return False


async def remove_user_from_group(email: str, group_name: str) -> bool:
    """
    Remove a user from a group.

    Args:
        email: User's email address
        group_name: Group name to remove user from

    Returns:
        True if removed successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM mcp_proxy.user_group_membership
                WHERE LOWER(user_email) = LOWER($1) AND group_name = $2
                """,
                email, group_name
            )
            log(f"Removed user from group: {email} -> {group_name}")
            return True
    except Exception as e:
        log(f"Error removing user from group: {e}")
        return False


# =============================================================================
# ADMIN PORTAL: GROUP MANAGEMENT
# =============================================================================

async def get_all_groups_with_servers() -> list[dict]:
    """
    Get all groups with their server access and user counts.

    Returns:
        List of {group_name, servers: [...], user_count}
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    g.group_name,
                    COALESCE(array_agg(DISTINCT g.tenant_id) FILTER (WHERE g.tenant_id IS NOT NULL), '{}') as servers,
                    COUNT(DISTINCT u.user_email) as user_count
                FROM mcp_proxy.group_tenant_mapping g
                LEFT JOIN mcp_proxy.user_group_membership u ON g.group_name = u.group_name
                GROUP BY g.group_name
                ORDER BY g.group_name
                """
            )
            return [
                {
                    "group_name": row['group_name'],
                    "servers": list(row['servers']) if row['servers'] else [],
                    "user_count": row['user_count']
                }
                for row in rows
            ]
    except Exception as e:
        log(f"Error fetching all groups with servers: {e}")
        return []


async def get_group_users(group_name: str) -> list[str]:
    """
    Get all users in a specific group.

    Args:
        group_name: Group name

    Returns:
        List of user email addresses
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_email FROM mcp_proxy.user_group_membership
                WHERE group_name = $1
                ORDER BY user_email
                """,
                group_name
            )
            return [row['user_email'] for row in rows]
    except Exception as e:
        log(f"Error fetching users for group {group_name}: {e}")
        return []


async def create_group(group_name: str, server_ids: list[str]) -> bool:
    """
    Create a new group with server access.

    Args:
        group_name: Name of the group to create
        server_ids: List of server IDs the group can access

    Returns:
        True if created successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Insert group-server mappings
            for server_id in server_ids:
                await conn.execute(
                    """
                    INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id)
                    VALUES ($1, $2)
                    ON CONFLICT (group_name, tenant_id) DO NOTHING
                    """,
                    group_name, server_id
                )
            log(f"Created group: {group_name} with servers: {server_ids}")
            return True
    except Exception as e:
        log(f"Error creating group {group_name}: {e}")
        return False


async def update_group_servers(group_name: str, server_ids: list[str]) -> bool:
    """
    Update a group's server access (replace all servers).

    Args:
        group_name: Name of the group
        server_ids: New list of server IDs

    Returns:
        True if updated successfully, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Remove all existing server mappings
                await conn.execute(
                    """
                    DELETE FROM mcp_proxy.group_tenant_mapping
                    WHERE group_name = $1
                    """,
                    group_name
                )
                # Add new server mappings
                for server_id in server_ids:
                    await conn.execute(
                        """
                        INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id)
                        VALUES ($1, $2)
                        """,
                        group_name, server_id
                    )
            log(f"Updated group {group_name} servers: {server_ids}")
            return True
    except Exception as e:
        log(f"Error updating group {group_name}: {e}")
        return False


async def delete_group(group_name: str) -> dict:
    """
    Delete a group and all its mappings.

    Args:
        group_name: Name of the group to delete

    Returns:
        Dict with {success: bool, users_removed: int, servers_removed: int}
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Count affected users
                user_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM mcp_proxy.user_group_membership
                    WHERE group_name = $1
                    """,
                    group_name
                )

                # Count affected server mappings
                server_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM mcp_proxy.group_tenant_mapping
                    WHERE group_name = $1
                    """,
                    group_name
                )

                # Delete user memberships
                await conn.execute(
                    """
                    DELETE FROM mcp_proxy.user_group_membership
                    WHERE group_name = $1
                    """,
                    group_name
                )

                # Delete server mappings
                await conn.execute(
                    """
                    DELETE FROM mcp_proxy.group_tenant_mapping
                    WHERE group_name = $1
                    """,
                    group_name
                )

            log(f"Deleted group {group_name}: {user_count} users, {server_count} servers")
            return {
                "success": True,
                "users_removed": user_count,
                "servers_removed": server_count
            }
    except Exception as e:
        log(f"Error deleting group {group_name}: {e}")
        return {"success": False, "error": str(e)}


async def get_all_available_servers() -> list[str]:
    """
    Get list of all server IDs that exist in the group_tenant_mapping table.
    This is used for UI dropdowns.

    Returns:
        List of unique server IDs
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT tenant_id FROM mcp_proxy.group_tenant_mapping
                ORDER BY tenant_id
                """
            )
            return [row['tenant_id'] for row in rows]
    except Exception as e:
        log(f"Error fetching available servers: {e}")
        return []
