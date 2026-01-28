"""
Admin Portal - User & Group Management for MCP Proxy

A simple web interface to manage:
- Users (add/remove from groups)
- Groups (create/delete)
- Group-Tenant mappings (which groups can access which MCP servers)

Endpoints:
  GET  /                    - Dashboard
  GET  /users               - List users
  POST /users               - Add user to group
  DELETE /users/{email}     - Remove user from group
  GET  /groups              - List groups
  POST /groups              - Create group
  DELETE /groups/{name}     - Delete group
  GET  /mappings            - List group-tenant mappings
  POST /mappings            - Create mapping
  DELETE /mappings          - Delete mapping
  GET  /health              - Health check
"""

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import asyncpg
import os
import logging
from typing import Optional, List
from contextlib import asynccontextmanager
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://openwebui:localdev@localhost:5432/openwebui")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "admin@example.com").split(",")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


async def init_db_pool():
    """Initialize database connection pool."""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=30
        )
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


async def close_db_pool():
    """Close database connection pool."""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    await init_db_pool()
    yield
    await close_db_pool()


app = FastAPI(
    title="Admin Portal",
    description="User and Group Management for MCP Proxy",
    version="1.0.0",
    lifespan=lifespan
)


def get_base_html(title: str, content: str, message: str = "") -> str:
    """Generate base HTML page."""
    message_html = f'<div class="message">{message}</div>' if message else ''

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - MCP Admin</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; }}
        .navbar {{ background: #1a1a2e; color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }}
        .navbar h1 {{ font-size: 20px; }}
        .navbar nav a {{ color: #a0a0a0; text-decoration: none; margin-left: 24px; }}
        .navbar nav a:hover, .navbar nav a.active {{ color: white; }}
        .container {{ max-width: 1200px; margin: 24px auto; padding: 0 24px; }}
        .card {{ background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h2 {{ margin-bottom: 16px; color: #333; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f9f9f9; font-weight: 600; }}
        .btn {{ padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }}
        .btn-primary {{ background: #3b82f6; color: white; }}
        .btn-danger {{ background: #ef4444; color: white; }}
        .btn-success {{ background: #22c55e; color: white; }}
        .btn:hover {{ opacity: 0.9; }}
        .form-group {{ margin-bottom: 16px; }}
        .form-group label {{ display: block; margin-bottom: 4px; font-weight: 500; }}
        .form-group input, .form-group select {{ width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; }}
        .message {{ background: #dbeafe; color: #1e40af; padding: 12px; border-radius: 4px; margin-bottom: 16px; }}
        .error {{ background: #fee2e2; color: #991b1b; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; }}
        .stat-card {{ text-align: center; }}
        .stat-card .number {{ font-size: 48px; font-weight: 700; color: #3b82f6; }}
        .stat-card .label {{ color: #666; }}
        .tag {{ display: inline-block; background: #e5e7eb; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin: 2px; }}
    </style>
</head>
<body>
    <div class="navbar">
        <h1>MCP Admin Portal</h1>
        <nav>
            <a href="/">Dashboard</a>
            <a href="/users">Users</a>
            <a href="/groups">Groups</a>
            <a href="/mappings">Mappings</a>
        </nav>
    </div>
    <div class="container">
        {message_html}
        {content}
    </div>
</body>
</html>
"""


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "admin-portal"}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard with stats."""
    if not db_pool:
        return get_base_html("Dashboard", "<p>Database not connected</p>")

    async with db_pool.acquire() as conn:
        user_count = await conn.fetchval("SELECT COUNT(DISTINCT user_email) FROM mcp_proxy.user_group_membership")
        group_count = await conn.fetchval("SELECT COUNT(DISTINCT group_name) FROM mcp_proxy.user_group_membership")
        mapping_count = await conn.fetchval("SELECT COUNT(*) FROM mcp_proxy.group_tenant_mapping")

    content = f"""
    <h2>Dashboard</h2>
    <div class="grid">
        <div class="card stat-card">
            <div class="number">{user_count or 0}</div>
            <div class="label">Users</div>
        </div>
        <div class="card stat-card">
            <div class="number">{group_count or 0}</div>
            <div class="label">Groups</div>
        </div>
        <div class="card stat-card">
            <div class="number">{mapping_count or 0}</div>
            <div class="label">Server Mappings</div>
        </div>
    </div>

    <div class="card">
        <h2>Quick Actions</h2>
        <p style="margin-bottom: 16px;">Manage users, groups, and server access permissions.</p>
        <a href="/users" class="btn btn-primary">Manage Users</a>
        <a href="/groups" class="btn btn-primary" style="margin-left: 8px;">Manage Groups</a>
        <a href="/mappings" class="btn btn-primary" style="margin-left: 8px;">Server Mappings</a>
    </div>
    """

    return get_base_html("Dashboard", content)


@app.get("/users", response_class=HTMLResponse)
async def list_users(message: str = ""):
    """List all users and their groups."""
    if not db_pool:
        return get_base_html("Users", "<p>Database not connected</p>")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_email, array_agg(group_name) as groups
            FROM mcp_proxy.user_group_membership
            GROUP BY user_email
            ORDER BY user_email
        """)

        groups = await conn.fetch("SELECT DISTINCT group_name FROM mcp_proxy.user_group_membership ORDER BY group_name")

    users_html = ""
    for row in rows:
        groups_tags = "".join([f'<span class="tag">{g}</span>' for g in row["groups"]])
        users_html += f"""
        <tr>
            <td>{row['user_email']}</td>
            <td>{groups_tags}</td>
            <td>
                <form method="post" action="/users/delete" style="display:inline;">
                    <input type="hidden" name="email" value="{row['user_email']}">
                    <button type="submit" class="btn btn-danger">Remove All</button>
                </form>
            </td>
        </tr>
        """

    group_options = "".join([f'<option value="{g["group_name"]}">{g["group_name"]}</option>' for g in groups])

    content = f"""
    <div class="card">
        <h2>Add User to Group</h2>
        <form method="post" action="/users">
            <div class="grid">
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" name="email" required placeholder="user@example.com">
                </div>
                <div class="form-group">
                    <label>Group</label>
                    <select name="group_name" required>
                        <option value="">Select group...</option>
                        {group_options}
                        <option value="__new__">+ Create new group</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>New Group Name (if creating new)</label>
                    <input type="text" name="new_group" placeholder="MCP-NewGroup">
                </div>
            </div>
            <button type="submit" class="btn btn-success">Add User to Group</button>
        </form>
    </div>

    <div class="card">
        <h2>Users ({len(rows)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Email</th>
                    <th>Groups</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {users_html if users_html else '<tr><td colspan="3">No users yet. Add one above!</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    return get_base_html("Users", content, message)


@app.post("/users")
async def add_user_to_group(email: str = Form(...), group_name: str = Form(...), new_group: str = Form("")):
    """Add a user to a group."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    # Handle new group creation
    if group_name == "__new__":
        if not new_group:
            return RedirectResponse(url="/users?message=Please+enter+a+new+group+name", status_code=303)
        group_name = new_group

    email = email.lower().strip()
    group_name = group_name.strip()

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO mcp_proxy.user_group_membership (user_email, group_name)
            VALUES ($1, $2)
            ON CONFLICT (user_email, group_name) DO NOTHING
        """, email, group_name)

    return RedirectResponse(url=f"/users?message=Added+{email}+to+{group_name}", status_code=303)


@app.post("/users/delete")
async def remove_user(email: str = Form(...)):
    """Remove user from all groups."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM mcp_proxy.user_group_membership WHERE user_email = $1", email.lower())

    return RedirectResponse(url="/users?message=Removed+user", status_code=303)


@app.get("/groups", response_class=HTMLResponse)
async def list_groups(message: str = ""):
    """List all groups."""
    if not db_pool:
        return get_base_html("Groups", "<p>Database not connected</p>")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT group_name, COUNT(user_email) as user_count
            FROM mcp_proxy.user_group_membership
            GROUP BY group_name
            ORDER BY group_name
        """)

    groups_html = ""
    for row in rows:
        groups_html += f"""
        <tr>
            <td>{row['group_name']}</td>
            <td>{row['user_count']}</td>
            <td>
                <form method="post" action="/groups/delete" style="display:inline;">
                    <input type="hidden" name="group_name" value="{row['group_name']}">
                    <button type="submit" class="btn btn-danger">Delete</button>
                </form>
            </td>
        </tr>
        """

    content = f"""
    <div class="card">
        <h2>Create Group</h2>
        <form method="post" action="/groups">
            <div class="form-group" style="max-width: 400px;">
                <label>Group Name</label>
                <input type="text" name="group_name" required placeholder="MCP-GitHub">
            </div>
            <button type="submit" class="btn btn-success">Create Group</button>
        </form>
    </div>

    <div class="card">
        <h2>Groups ({len(rows)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Group Name</th>
                    <th>Users</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {groups_html if groups_html else '<tr><td colspan="3">No groups yet.</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    return get_base_html("Groups", content, message)


@app.post("/groups")
async def create_group(group_name: str = Form(...)):
    """Create a new group (by adding a placeholder user)."""
    # Groups are implicitly created when users are added
    # For explicit creation, we just redirect to users page
    return RedirectResponse(url=f"/users?message=Add+a+user+to+group+{group_name}", status_code=303)


@app.post("/groups/delete")
async def delete_group(group_name: str = Form(...)):
    """Delete a group (removes all users from it)."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM mcp_proxy.user_group_membership WHERE group_name = $1", group_name)
        await conn.execute("DELETE FROM mcp_proxy.group_tenant_mapping WHERE group_name = $1", group_name)

    return RedirectResponse(url="/groups?message=Deleted+group", status_code=303)


@app.get("/mappings", response_class=HTMLResponse)
async def list_mappings(message: str = ""):
    """List group-tenant mappings (which groups can access which MCP servers)."""
    if not db_pool:
        return get_base_html("Mappings", "<p>Database not connected</p>")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT group_name, tenant_id, created_at
            FROM mcp_proxy.group_tenant_mapping
            ORDER BY group_name, tenant_id
        """)

        groups = await conn.fetch("SELECT DISTINCT group_name FROM mcp_proxy.user_group_membership ORDER BY group_name")

    mappings_html = ""
    for row in rows:
        created = row['created_at'].strftime('%Y-%m-%d') if row['created_at'] else 'N/A'
        mappings_html += f"""
        <tr>
            <td>{row['group_name']}</td>
            <td>{row['tenant_id']}</td>
            <td>{created}</td>
            <td>
                <form method="post" action="/mappings/delete" style="display:inline;">
                    <input type="hidden" name="group_name" value="{row['group_name']}">
                    <input type="hidden" name="tenant_id" value="{row['tenant_id']}">
                    <button type="submit" class="btn btn-danger">Delete</button>
                </form>
            </td>
        </tr>
        """

    group_options = "".join([f'<option value="{g["group_name"]}">{g["group_name"]}</option>' for g in groups])

    # Known MCP servers
    servers = ["github", "filesystem", "linear", "notion", "atlassian", "asana", "gitlab", "slack"]
    server_options = "".join([f'<option value="{s}">{s}</option>' for s in servers])

    content = f"""
    <div class="card">
        <h2>Add Server Access</h2>
        <p style="margin-bottom: 16px; color: #666;">Grant a group access to an MCP server.</p>
        <form method="post" action="/mappings">
            <div class="grid">
                <div class="form-group">
                    <label>Group</label>
                    <select name="group_name" required>
                        <option value="">Select group...</option>
                        {group_options}
                    </select>
                </div>
                <div class="form-group">
                    <label>MCP Server</label>
                    <select name="tenant_id" required>
                        <option value="">Select server...</option>
                        {server_options}
                    </select>
                </div>
            </div>
            <button type="submit" class="btn btn-success">Grant Access</button>
        </form>
    </div>

    <div class="card">
        <h2>Group → Server Mappings ({len(rows)})</h2>
        <p style="margin-bottom: 16px; color: #666;">These mappings control which groups can access which MCP servers.</p>
        <table>
            <thead>
                <tr>
                    <th>Group</th>
                    <th>MCP Server</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {mappings_html if mappings_html else '<tr><td colspan="4">No mappings yet. Add one above!</td></tr>'}
            </tbody>
        </table>
    </div>
    """

    return get_base_html("Mappings", content, message)


@app.post("/mappings")
async def add_mapping(group_name: str = Form(...), tenant_id: str = Form(...)):
    """Add a group-tenant mapping."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO mcp_proxy.group_tenant_mapping (group_name, tenant_id)
            VALUES ($1, $2)
            ON CONFLICT (group_name, tenant_id) DO NOTHING
        """, group_name, tenant_id)

    return RedirectResponse(url=f"/mappings?message=Granted+{group_name}+access+to+{tenant_id}", status_code=303)


@app.post("/mappings/delete")
async def delete_mapping(group_name: str = Form(...), tenant_id: str = Form(...)):
    """Delete a group-tenant mapping."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    async with db_pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM mcp_proxy.group_tenant_mapping
            WHERE group_name = $1 AND tenant_id = $2
        """, group_name, tenant_id)

    return RedirectResponse(url="/mappings?message=Removed+access", status_code=303)


# API endpoints for programmatic access
@app.get("/api/users")
async def api_list_users():
    """API: List all users and their groups."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_email, array_agg(group_name) as groups
            FROM mcp_proxy.user_group_membership
            GROUP BY user_email
            ORDER BY user_email
        """)

    return [{"email": row["user_email"], "groups": row["groups"]} for row in rows]


@app.get("/api/groups")
async def api_list_groups():
    """API: List all groups."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT group_name, COUNT(user_email) as user_count
            FROM mcp_proxy.user_group_membership
            GROUP BY group_name
            ORDER BY group_name
        """)

    return [{"name": row["group_name"], "user_count": row["user_count"]} for row in rows]


@app.get("/api/mappings")
async def api_list_mappings():
    """API: List all group-tenant mappings."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not connected")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT group_name, tenant_id
            FROM mcp_proxy.group_tenant_mapping
            ORDER BY group_name, tenant_id
        """)

    return [{"group": row["group_name"], "server": row["tenant_id"]} for row in rows]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
