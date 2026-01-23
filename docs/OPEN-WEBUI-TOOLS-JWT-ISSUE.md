# Open WebUI External Tools - JWT Authentication Issue

**Date:** 2026-01-22
**Status:** FIXED - Implemented database lookup for user email

## Summary

When testing MCP tools in Open WebUI, the model said "I'm unable to create files" because the MCP Proxy could not identify the user for multi-tenant filtering.

## Root Cause

Open WebUI's **Session auth** sends a JWT to external tool servers, but:

1. The JWT only contains: `id`, `exp`, `jti`
2. **No email claim** in the JWT
3. No `X-OpenWebUI-User-Email` header sent to tool servers

The MCP Proxy's original auth flow:
```
1. Receive JWT from Open WebUI ✓
2. Validate JWT signature ✓
3. Try to get email from X-OpenWebUI-User-Email header -> NOT PRESENT
4. Try to get email from JWT claims -> NOT PRESENT (no 'email' claim)
5. Result: User email = None
6. Multi-tenant filtering fails (no user identity)
```

## Evidence from Logs (Before Fix)

```
[AUTH] API Gateway headers not present
[AUTH] JWT validated successfully - claims: ['id', 'exp', 'jti']
[AUTH] JWT validated - headers are now trustworthy
[AUTH] JWT valid but no user email found in headers or claims
=== /openapi.json request ===
  User email: None
```

## Fix Implemented

Modified `mcp-proxy/auth.py` to use JWT `id` claim to look up user email from database:

### Changes Made

1. **Added asyncpg import and DATABASE_URL config**
2. **Added lazy database connection pool**
3. **Added `lookup_email_by_user_id()` function**
4. **Made auth functions async**
5. **Added Step 5: Database lookup after JWT validation**

### New Auth Flow

```
1. Receive JWT from Open WebUI ✓
2. Validate JWT signature ✓
3. Try to get email from X-OpenWebUI-User-Email header -> NOT PRESENT
4. Try to get email from JWT claims -> NOT PRESENT
5. NEW: Look up email from database using JWT 'id' claim -> SUCCESS!
6. Multi-tenant filtering works (user identified via database)
```

### Code Added to `auth.py`

```python
async def lookup_email_by_user_id(user_id: str) -> Optional[str]:
    """
    Look up user email from Open WebUI's database using user ID.

    Open WebUI stores users in a 'user' table with 'id' and 'email' columns.
    When the JWT only contains 'id', we use this to get the email for
    multi-tenant filtering.
    """
    pool = await _get_db_pool()
    if not pool:
        return None

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT email FROM "user" WHERE id = $1',
            user_id
        )
        return row["email"] if row else None
```

### Updated `extract_user_from_headers_optional()`

```python
# Step 5: Database lookup - Open WebUI JWT has only id, no email
user_id = jwt_claims.get("id")
if user_id:
    _log(f"JWT has user_id but no email - attempting database lookup for: {user_id}")
    email = await lookup_email_by_user_id(user_id)
    if email:
        _log(f"Database lookup successful: {user_id} -> {email}")
        return UserInfo(
            email=email,
            user_id=user_id,
            name=jwt_claims.get("name", ""),
            role=jwt_claims.get("role", "user"),
            chat_id=None,
            auth_method="jwt_db_lookup"  # Indicates we looked up email from database
        )
```

## Files Modified

- `mcp-proxy/auth.py` - Added database lookup, made functions async
- `mcp-proxy/main.py` - Updated all auth function calls to use `await`

## Testing

1. Rebuilt MCP Proxy container with `docker compose build mcp-proxy`
2. Recreated container with `docker compose up -d mcp-proxy`
3. Verified health endpoint: `curl http://localhost:8000/health`

## Expected Logs (After Fix)

When a request comes with Open WebUI's Session auth JWT:

```
[AUTH] API Gateway headers not present
[AUTH] JWT validated successfully - claims: ['id', 'exp', 'jti']
[AUTH] JWT validated - headers are now trustworthy
[AUTH] JWT has user_id but no email - attempting database lookup for: abc123
[AUTH] Database lookup successful: abc123 -> user@example.com
=== /openapi.json request ===
  User email: user@example.com
```

## Configuration Requirements

The MCP Proxy needs `DATABASE_URL` environment variable pointing to Open WebUI's PostgreSQL database:

```yaml
# docker-compose.yml
mcp-proxy:
  environment:
    - DATABASE_URL=postgresql://openwebui:${POSTGRES_PASSWORD}@postgres:5432/openwebui
```

This allows the proxy to look up user emails from the same database Open WebUI uses.

## Related Files

- `mcp-proxy/auth.py` - Authentication logic (modified)
- `mcp-proxy/main.py` - FastAPI endpoints (modified)
- `mcp-proxy/tenants.py` - Multi-tenant access control
- `docker-compose.yml` - Container configuration
