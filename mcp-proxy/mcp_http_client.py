# mcp-proxy/mcp_http_client.py
"""
MCP Streamable HTTP Client

Implements the MCP Streamable HTTP transport protocol (JSON-RPC 2.0 over HTTP + SSE).
Used for servers like Linear that speak native MCP protocol instead of REST/OpenAPI.

Protocol:
1. POST /mcp with {"method":"initialize",...} → captures Mcp-Session-Id header
2. POST /mcp with {"method":"tools/list"} + session header → SSE response with tools
3. POST /mcp with {"method":"tools/call","params":{...}} + session header → SSE response

Responses use SSE format: event: message\ndata: {json-rpc result}
"""
import httpx
import json
import time
from typing import Any, Dict, List, Optional, Tuple


class MCPStreamableClient:
    """Client for MCP servers that use the Streamable HTTP transport."""

    # Class-level session cache: endpoint_url -> (session_id, timestamp)
    _sessions: Dict[str, Tuple[str, float]] = {}
    SESSION_TTL = 3600  # 1 hour

    def __init__(self, endpoint_url: str, api_key: str = "", timeout: float = 30.0):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.timeout = timeout

    def _get_cached_session(self) -> Optional[str]:
        """Get cached session ID if still valid."""
        entry = self._sessions.get(self.endpoint_url)
        if entry:
            session_id, ts = entry
            if time.time() - ts < self.SESSION_TTL:
                return session_id
            del self._sessions[self.endpoint_url]
        return None

    def _cache_session(self, session_id: str):
        """Cache a session ID."""
        self._sessions[self.endpoint_url] = (session_id, time.time())

    def _invalidate_session(self):
        """Remove cached session."""
        self._sessions.pop(self.endpoint_url, None)

    def _base_headers(self) -> Dict[str, str]:
        """Build base headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _parse_sse_response(text: str) -> Optional[Dict[str, Any]]:
        """
        Parse SSE-formatted response to extract JSON-RPC result.

        SSE format:
            event: message
            data: {"jsonrpc":"2.0","id":1,"result":{...}}

        Also handles plain JSON responses (non-SSE).
        """
        # Try plain JSON first (some responses aren't SSE)
        text = text.strip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Parse SSE: look for data: lines after event: message
        last_data = None
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        last_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

        return last_data

    async def initialize(self) -> str:
        """
        Send initialize request and capture session ID.

        Returns the Mcp-Session-Id for subsequent requests.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-proxy",
                    "version": "0.3.0"
                }
            }
        }

        headers = self._base_headers()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.endpoint_url,
                json=payload,
                headers=headers
            )

            if response.status_code not in (200, 201):
                raise Exception(
                    f"MCP initialize failed: {response.status_code} {response.text[:500]}"
                )

            # Capture session ID from response header
            session_id = response.headers.get("mcp-session-id", "")
            if not session_id:
                # Some servers return it lowercase
                session_id = response.headers.get("Mcp-Session-Id", "")

            if session_id:
                self._cache_session(session_id)
                print(f"  [MCP-HTTP] Initialized session: {session_id[:20]}...")
            else:
                print(f"  [MCP-HTTP] Warning: No session ID in initialize response")

            # Parse the response to confirm initialization
            result = self._parse_sse_response(response.text)
            if result:
                print(f"  [MCP-HTTP] Server: {result.get('result', {}).get('serverInfo', {})}")

            # Send initialized notification
            await self._send_initialized(client, headers, session_id)

            return session_id

    async def _send_initialized(self, client: httpx.AsyncClient, headers: Dict, session_id: str):
        """Send the initialized notification after successful init."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        notify_headers = {**headers}
        if session_id:
            notify_headers["mcp-session-id"] = session_id

        try:
            await client.post(
                self.endpoint_url,
                json=notification,
                headers=notify_headers
            )
        except Exception as e:
            print(f"  [MCP-HTTP] Initialized notification failed (non-fatal): {e}")

    async def _ensure_session(self) -> str:
        """Ensure we have a valid session, initializing if needed."""
        session_id = self._get_cached_session()
        if not session_id:
            session_id = await self.initialize()
        return session_id

    async def _request(self, method: str, params: Optional[Dict] = None, retry_on_auth: bool = True) -> Dict[str, Any]:
        """
        Send a JSON-RPC request with session handling.

        Automatically re-initializes on 4xx errors.
        """
        session_id = await self._ensure_session()

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": method,
        }
        if params:
            payload["params"] = params

        headers = self._base_headers()
        if session_id:
            headers["mcp-session-id"] = session_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.endpoint_url,
                json=payload,
                headers=headers
            )

            # Re-initialize on auth/session errors
            if response.status_code in (401, 403, 404, 409) and retry_on_auth:
                print(f"  [MCP-HTTP] Got {response.status_code}, re-initializing session...")
                self._invalidate_session()
                return await self._request(method, params, retry_on_auth=False)

            if response.status_code not in (200, 201):
                raise Exception(
                    f"MCP {method} failed: {response.status_code} {response.text[:500]}"
                )

            result = self._parse_sse_response(response.text)
            if not result:
                raise Exception(f"MCP {method}: could not parse response: {response.text[:500]}")

            # Check for JSON-RPC error
            if "error" in result:
                error = result["error"]
                raise Exception(f"MCP {method} error: {error.get('message', error)}")

            return result

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Fetch available tools from the MCP server.

        Returns list of tool definitions with name, description, and inputSchema.
        """
        result = await self._request("tools/list")
        tools = result.get("result", {}).get("tools", [])
        print(f"  [MCP-HTTP] Listed {len(tools)} tools from {self.endpoint_url}")
        return tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        params = {
            "name": tool_name,
            "arguments": arguments or {}
        }

        result = await self._request("tools/call", params)
        return result.get("result", result)


# Module-level helper for quick access
_clients: Dict[str, MCPStreamableClient] = {}


def get_mcp_client(endpoint_url: str, api_key: str = "") -> MCPStreamableClient:
    """Get or create an MCPStreamableClient for the given endpoint."""
    key = f"{endpoint_url}:{api_key[:8] if api_key else ''}"
    if key not in _clients:
        _clients[key] = MCPStreamableClient(endpoint_url, api_key)
    return _clients[key]
