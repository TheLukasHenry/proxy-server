"""
Auth Service - ForwardAuth for Traefik

This service is called by Traefik's ForwardAuth middleware to:
1. Extract user email from traefikoidc session (X-Forwarded-User header)
2. Look up user's groups from PostgreSQL
3. Return headers: X-User-Email, X-User-Groups

The MCP Proxy then uses these headers to filter available servers.

Endpoints:
  GET /auth - ForwardAuth endpoint (called by Traefik)
  GET /health - Health check
"""

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import asyncpg
import os
import logging
from typing import Optional, List
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://openwebui:localdev@localhost:5432/openwebui")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
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
    title="Auth Service",
    description="ForwardAuth service for Traefik - looks up user groups from PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)


async def get_user_groups(email: str) -> List[str]:
    """
    Get groups for a user from the database.

    Queries: user_group_membership table
    Returns: List of group names
    """
    if not db_pool:
        logger.error("Database pool not initialized")
        return []

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT group_name
                FROM user_group_membership
                WHERE user_email = $1
                """,
                email.lower()
            )
            groups = [row["group_name"] for row in rows]
            logger.info(f"User {email} has groups: {groups}")
            return groups
    except Exception as e:
        logger.error(f"Error fetching groups for {email}: {e}")
        return []


async def is_user_admin(email: str) -> bool:
    """
    Check if user is an admin.

    Queries: user_admin_status table
    """
    if not db_pool:
        return False

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT is_admin
                FROM user_admin_status
                WHERE user_email = $1
                """,
                email.lower()
            )
            return row["is_admin"] if row else False
    except Exception as e:
        logger.error(f"Error checking admin status for {email}: {e}")
        return False


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "connected" if db_pool else "disconnected"
    return {
        "status": "healthy",
        "service": "auth-service",
        "database": db_status
    }


@app.get("/auth")
async def forward_auth(request: Request, response: Response):
    """
    ForwardAuth endpoint - called by Traefik for every request.

    Flow:
    1. traefikoidc sets X-Forwarded-User header with user email
    2. This endpoint reads that header
    3. Looks up user's groups from PostgreSQL
    4. Returns headers: X-User-Email, X-User-Groups, X-User-Admin
    5. Traefik forwards these headers to the backend service

    If no user header is present, returns 401 Unauthorized.
    """
    # Get user email from traefikoidc
    user_email = request.headers.get("X-Forwarded-User")

    # Also check alternative headers (for compatibility)
    if not user_email:
        user_email = request.headers.get("X-Auth-Request-Email")
    if not user_email:
        user_email = request.headers.get("Remote-User")

    if DEBUG:
        logger.info(f"ForwardAuth request - Headers: {dict(request.headers)}")

    if not user_email:
        logger.warning("No user email in headers - unauthorized")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in."
        )

    # Normalize email
    user_email = user_email.lower().strip()

    # Get user's groups from database
    groups = await get_user_groups(user_email)

    # Check if admin
    is_admin = await is_user_admin(user_email)

    # Build response headers
    response.headers["X-User-Email"] = user_email
    response.headers["X-User-Groups"] = ",".join(groups) if groups else ""
    response.headers["X-User-Admin"] = "true" if is_admin else "false"
    response.headers["X-User-Name"] = user_email.split("@")[0]  # Use email prefix as name

    logger.info(f"Auth OK: {user_email} -> groups={groups}, admin={is_admin}")

    return {"status": "ok", "user": user_email, "groups": groups}


@app.get("/auth/test")
async def test_auth(email: str):
    """
    Test endpoint - simulate ForwardAuth for a given email.

    Usage: GET /auth/test?email=alice@example.com

    For local testing only!
    """
    if not DEBUG:
        raise HTTPException(status_code=403, detail="Test endpoint disabled in production")

    groups = await get_user_groups(email)
    is_admin = await is_user_admin(email)

    return {
        "email": email,
        "groups": groups,
        "is_admin": is_admin,
        "headers_that_would_be_set": {
            "X-User-Email": email,
            "X-User-Groups": ",".join(groups),
            "X-User-Admin": "true" if is_admin else "false"
        }
    }


@app.get("/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint - show all incoming headers."""
    if not DEBUG:
        raise HTTPException(status_code=403, detail="Debug endpoint disabled in production")

    return {
        "headers": dict(request.headers),
        "client": request.client.host if request.client else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
