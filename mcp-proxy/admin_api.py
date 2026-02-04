# mcp-proxy/admin_api.py
"""
Admin Portal API Router

This module provides all admin API endpoints for the MCP Proxy.
Using a separate router ensures these routes have priority over catch-all routes.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List
import re

from auth import extract_user_from_headers_optional
from db import (
    is_openwebui_admin,
    get_all_users_with_groups,
    add_user_to_group,
    remove_user_from_group,
    get_all_groups_with_servers,
    get_group_users,
    create_group,
    update_group_servers,
    delete_group,
    get_all_tenant_keys,
    get_tenant_keys_by_tenant,
    set_tenant_api_key,
    delete_tenant_api_key,
    get_all_tenant_endpoints,
    set_tenant_endpoint_override,
    delete_tenant_endpoint_override,
)
from tenants import ALL_SERVERS

# Create the admin router
admin_router = APIRouter(prefix="/admin", tags=["Admin Portal"])


# =============================================================================
# AUTHENTICATION HELPERS
# =============================================================================

async def require_admin(request: Request) -> str:
    """
    Verify user is an Open WebUI admin. Returns user email if admin.
    Raises HTTPException if not authenticated or not admin.
    """
    user = await extract_user_from_headers_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    is_admin = await is_openwebui_admin(user.email)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Open WebUI admin role required")

    return user.email


async def require_mcp_admin(request: Request) -> str:
    """
    Verify user is in MCP-Admin group. Returns user email if authorized.
    Raises HTTPException if not authenticated or not in MCP-Admin group.
    """
    user = await extract_user_from_headers_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    entra_groups = user.entra_groups if user else []
    if "MCP-Admin" not in entra_groups:
        raise HTTPException(status_code=403, detail="MCP-Admin group required")

    return user.email


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class UserGroupRequest(BaseModel):
    """Request body for adding/removing user from group."""
    email: str
    group_name: str


class CreateGroupRequest(BaseModel):
    """Request body for creating a group."""
    group_name: str
    server_ids: List[str] = []


class UpdateGroupRequest(BaseModel):
    """Request body for updating a group's servers."""
    server_ids: List[str]


class TenantKeyRequest(BaseModel):
    """Request body for setting a tenant API key."""
    tenant_id: str
    server_id: str
    key_name: str
    key_value: str


class TenantKeyDeleteRequest(BaseModel):
    """Request body for deleting a tenant API key."""
    tenant_id: str
    server_id: str
    key_name: str


class EndpointOverrideRequest(BaseModel):
    """Request body for setting an endpoint override."""
    tenant_id: str
    server_id: str
    endpoint_url: str


class EndpointOverrideDeleteRequest(BaseModel):
    """Request body for deleting an endpoint override."""
    tenant_id: str
    server_id: str


# =============================================================================
# USER-GROUP MANAGEMENT ENDPOINTS
# =============================================================================

@admin_router.get("/users")
async def list_users_with_groups(request: Request):
    """
    List all users with their group memberships.

    Requires Open WebUI admin role.
    Returns: {count: int, users: [{email, groups: [...], updated_at}, ...]}
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} listing all users")

    users = await get_all_users_with_groups()
    return {
        "count": len(users),
        "users": users
    }


@admin_router.post("/users/groups")
async def add_user_group(body: UserGroupRequest, request: Request):
    """
    Add a user to a group.

    Requires Open WebUI admin role.

    Example body:
    {
        "email": "user@example.com",
        "group_name": "MCP-GitHub"
    }
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} adding {body.email} to {body.group_name}")

    success = await add_user_to_group(body.email, body.group_name)
    if success:
        return {
            "status": "added",
            "email": body.email,
            "group_name": body.group_name
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to add user to group")


@admin_router.delete("/users/groups")
async def remove_user_group(body: UserGroupRequest, request: Request):
    """
    Remove a user from a group.

    Requires Open WebUI admin role.

    Example body:
    {
        "email": "user@example.com",
        "group_name": "MCP-GitHub"
    }
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} removing {body.email} from {body.group_name}")

    success = await remove_user_from_group(body.email, body.group_name)
    if success:
        return {
            "status": "removed",
            "email": body.email,
            "group_name": body.group_name
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to remove user from group")


# =============================================================================
# GROUP-SERVER MANAGEMENT ENDPOINTS
# =============================================================================

@admin_router.get("/groups")
async def list_groups_with_servers(request: Request):
    """
    List all groups with their server access and user counts.

    Requires Open WebUI admin role.
    Returns: {count: int, groups: [{group_name, servers: [...], user_count}, ...]}
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} listing all groups")

    groups = await get_all_groups_with_servers()
    return {
        "count": len(groups),
        "groups": groups
    }


@admin_router.get("/groups/{group_name}")
async def get_group_details(group_name: str, request: Request):
    """
    Get details for a specific group including users.

    Requires Open WebUI admin role.
    """
    admin_email = await require_admin(request)

    users = await get_group_users(group_name)
    groups = await get_all_groups_with_servers()

    # Find the specific group
    group_info = next((g for g in groups if g['group_name'] == group_name), None)
    if not group_info:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")

    return {
        "group_name": group_name,
        "servers": group_info['servers'],
        "user_count": len(users),
        "users": users
    }


@admin_router.post("/groups")
async def create_new_group(body: CreateGroupRequest, request: Request):
    """
    Create a new group with server access.

    Requires Open WebUI admin role.

    Example body:
    {
        "group_name": "MCP-NewTeam",
        "server_ids": ["github", "filesystem"]
    }
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} creating group {body.group_name} with servers {body.server_ids}")

    # Validate group name (alphanumeric + hyphen)
    if not re.match(r'^[A-Za-z0-9-]+$', body.group_name):
        raise HTTPException(
            status_code=400,
            detail="Group name must contain only letters, numbers, and hyphens"
        )

    success = await create_group(body.group_name, body.server_ids)
    if success:
        return {
            "status": "created",
            "group_name": body.group_name,
            "server_ids": body.server_ids
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to create group")


@admin_router.put("/groups/{group_name}")
async def update_group(group_name: str, body: UpdateGroupRequest, request: Request):
    """
    Update a group's server access.

    Requires Open WebUI admin role.

    Example body:
    {
        "server_ids": ["github", "filesystem", "linear"]
    }
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} updating group {group_name} servers to {body.server_ids}")

    success = await update_group_servers(group_name, body.server_ids)
    if success:
        return {
            "status": "updated",
            "group_name": group_name,
            "server_ids": body.server_ids
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to update group")


@admin_router.delete("/groups/{group_name}")
async def delete_existing_group(group_name: str, request: Request):
    """
    Delete a group and all its mappings.

    Requires Open WebUI admin role.
    Warning: This will remove all users from this group.
    """
    admin_email = await require_admin(request)

    # Protect MCP-Admin group from deletion
    if group_name == "MCP-Admin":
        raise HTTPException(status_code=400, detail="Cannot delete MCP-Admin group")

    print(f"[ADMIN] {admin_email} deleting group {group_name}")

    result = await delete_group(group_name)
    if result.get("success"):
        return {
            "status": "deleted",
            "group_name": group_name,
            "users_removed": result.get("users_removed", 0),
            "servers_removed": result.get("servers_removed", 0)
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete group"))


# =============================================================================
# TENANT API KEY MANAGEMENT ENDPOINTS
# =============================================================================

@admin_router.get("/tenant-keys")
async def list_tenant_keys(request: Request):
    """
    List all tenant-specific API keys (without values).

    Requires MCP-Admin group membership.
    Returns list of {tenant_id, server_id, key_name, updated_at}.
    """
    admin_email = await require_mcp_admin(request)

    keys = await get_all_tenant_keys()
    return {
        "count": len(keys),
        "keys": keys
    }


@admin_router.get("/tenant-keys/{tenant_id}")
async def get_tenant_keys(tenant_id: str, request: Request):
    """
    Get all API keys for a specific tenant (without values).

    Requires MCP-Admin group membership.
    Returns list of {server_id, key_name, updated_at}.
    """
    admin_email = await require_mcp_admin(request)

    keys = await get_tenant_keys_by_tenant(tenant_id)
    return {
        "tenant_id": tenant_id,
        "count": len(keys),
        "keys": keys
    }


@admin_router.post("/tenant-keys")
async def create_tenant_key(body: TenantKeyRequest, request: Request):
    """
    Set a tenant-specific API key.

    Requires MCP-Admin group membership.
    If key already exists, it will be updated.

    Example body:
    {
        "tenant_id": "Tenant-Google",
        "server_id": "github",
        "key_name": "GITHUB_TOKEN",
        "key_value": "ghp_xxxx..."
    }
    """
    admin_email = await require_mcp_admin(request)

    success = await set_tenant_api_key(
        body.tenant_id, body.server_id, body.key_name, body.key_value
    )

    if success:
        return {
            "status": "created",
            "tenant_id": body.tenant_id,
            "server_id": body.server_id,
            "key_name": body.key_name
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to set tenant key")


@admin_router.delete("/tenant-keys")
async def remove_tenant_key(body: TenantKeyDeleteRequest, request: Request):
    """
    Delete a tenant-specific API key.

    Requires MCP-Admin group membership.

    Example body:
    {
        "tenant_id": "Tenant-Google",
        "server_id": "github",
        "key_name": "GITHUB_TOKEN"
    }
    """
    admin_email = await require_mcp_admin(request)

    success = await delete_tenant_api_key(body.tenant_id, body.server_id, body.key_name)

    if success:
        return {
            "status": "deleted",
            "tenant_id": body.tenant_id,
            "server_id": body.server_id,
            "key_name": body.key_name
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to delete tenant key")


# =============================================================================
# ENDPOINT OVERRIDE MANAGEMENT ENDPOINTS
# =============================================================================

@admin_router.get("/endpoints")
async def list_endpoint_overrides(request: Request):
    """
    List all tenant endpoint overrides.

    Requires Open WebUI admin role.
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} listing endpoint overrides")

    endpoints = await get_all_tenant_endpoints()
    return {
        "count": len(endpoints),
        "endpoints": [
            {
                "tenant_id": e["tenant_id"],
                "server_id": e["server_id"],
                "endpoint_url": e["endpoint_url"],
                "created_at": e["created_at"].isoformat() if e.get("created_at") else None
            }
            for e in endpoints
        ]
    }


@admin_router.post("/endpoints")
async def create_endpoint_override(body: EndpointOverrideRequest, request: Request):
    """
    Set a tenant-specific endpoint override for dynamic routing.

    Requires Open WebUI admin role.

    Example body:
    {
        "tenant_id": "MCP-GitHub",
        "server_id": "github",
        "endpoint_url": "http://mcp-github-tenant:8000"
    }
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} setting endpoint override: {body.tenant_id} -> {body.server_id} -> {body.endpoint_url}")

    # Validate URL format
    if not body.endpoint_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Endpoint URL must start with http:// or https://")

    success = await set_tenant_endpoint_override(body.tenant_id, body.server_id, body.endpoint_url)
    if success:
        return {
            "status": "created",
            "tenant_id": body.tenant_id,
            "server_id": body.server_id,
            "endpoint_url": body.endpoint_url
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to set endpoint override")


@admin_router.delete("/endpoints")
async def remove_endpoint_override(body: EndpointOverrideDeleteRequest, request: Request):
    """
    Delete a tenant endpoint override.

    Requires Open WebUI admin role.

    Example body:
    {
        "tenant_id": "MCP-GitHub",
        "server_id": "github"
    }
    """
    admin_email = await require_admin(request)
    print(f"[ADMIN] {admin_email} deleting endpoint override: {body.tenant_id} -> {body.server_id}")

    success = await delete_tenant_endpoint_override(body.tenant_id, body.server_id)
    if success:
        return {
            "status": "deleted",
            "tenant_id": body.tenant_id,
            "server_id": body.server_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to delete endpoint override")


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@admin_router.get("/servers")
async def list_available_servers(request: Request):
    """
    List all available server IDs for admin dropdowns.

    Requires Open WebUI admin role.
    """
    admin_email = await require_admin(request)

    # Get servers from ALL_SERVERS config
    servers = [
        {
            "id": server_id,
            "name": config.display_name,
            "enabled": config.enabled
        }
        for server_id, config in ALL_SERVERS.items()
    ]

    return {
        "count": len(servers),
        "servers": sorted(servers, key=lambda x: x["id"])
    }
