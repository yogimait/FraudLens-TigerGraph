"""TigerGraph MCP client with pyTigerGraph fallback.

Spawns the `tigergraph-mcp` MCP server (stdio) and routes calls through it;
any MCP failure permanently falls back to a direct pyTigerGraph connection.
Module import never raises and never blocks (Savanna may be unreachable).
"""
import asyncio
import json
import os
import re
import sys
import threading
from contextlib import AsyncExitStack
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _MCP_SDK_OK = True
except Exception:
    _MCP_SDK_OK = False

RUN_INSTALLED_QUERY = "tigergraph__run_installed_query"
RUN_QUERY = "tigergraph__run_query"

_TOOL_CALL_TIMEOUT = 60.0


def _subprocess_env() -> dict:
    env = dict(os.environ)
    env.setdefault("TG_TGCLOUD", "true")
    if env.get("TG_GRAPH") and not env.get("TG_GRAPHNAME"):
        env["TG_GRAPHNAME"] = env["TG_GRAPH"]
    env["PYTHONUTF8"] = "1"
    return env


def _extract_payload(content: list) -> Any:
    """Pull the useful payload out of an MCP TextContent response."""
    for item in content:
        text = getattr(item, "text", None)
        if not text:
            continue
        stripped = text.strip()
        match = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
        if match:
            stripped = match.group(1).strip()
        try:
            decoded = json.loads(stripped)
        except (TypeError, ValueError):
            continue
        if isinstance(decoded, dict) and "data" in decoded:
            data = decoded["data"]
            if isinstance(data, dict) and "result" in data:
                return data["result"]
            return data
        return decoded
    raise ValueError("MCP response contained no parsable text content")


class TigerGraphMCP:
    """MCP-first TigerGraph access with automatic pyTigerGraph fallback."""

    def __init__(self, agent_dir: Optional[str] = None) -> None:
        self._agent_dir = agent_dir or os.path.dirname(os.path.abspath(__file__))
        self.use_mcp = False
        self._mcp_failed = False
        self._session: Optional[Any] = None
        self._tools: set = set()
        self._stack: Optional[AsyncExitStack] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._conn: Optional[Any] = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None and self._loop.is_running():
            return self._loop
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        return self._loop

    def _run(self, coro):
        loop = self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=_TOOL_CALL_TIMEOUT * 2)

    async def _connect_async(self) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "tigergraph_mcp.main"],
            env=_subprocess_env(),
            cwd=self._agent_dir,
        )
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        result = await session.list_tools()
        self._session = session
        self._tools = {t.name for t in result.tools}
        self.use_mcp = True

    def connect(self) -> bool:
        """Start the MCP server subprocess and complete the handshake."""
        if self._mcp_failed or not _MCP_SDK_OK:
            return False
        if self.use_mcp:
            return True
        try:
            self._run(self._connect_async())
            return self.use_mcp
        except Exception as e:
            print(f"TigerGraph MCP unavailable, using pyTigerGraph fallback: {type(e).__name__}: {e}")
            self._mcp_failed = True
            self.use_mcp = False
            return False

    async def call_tool(self, name: str, args: dict) -> Any:
        """Call an MCP tool and return the parsed payload."""
        if self._session is None:
            raise RuntimeError("MCP session not connected")
        result = await self._session.call_tool(name, args or {}, read_timeout_seconds=_TOOL_CALL_TIMEOUT)
        if getattr(result, "isError", False):
            raise RuntimeError(f"MCP tool {name} returned an error: {result.content}")
        return _extract_payload(result.content)

    def list_tools(self) -> list:
        """Return the tool names exposed by the MCP server (may be empty)."""
        if self._session is None:
            return []
        try:
            result = self._run(self._session.list_tools())
            return [t.name for t in result.tools]
        except Exception:
            return []

    def _mcp_call(self, tool: str, args: dict) -> Any:
        self.connect()
        if not self.use_mcp or tool not in self._tools:
            raise RuntimeError("MCP not available for this call")
        result = self._run(self.call_tool(tool, args))
        if isinstance(result, dict) and result.get("success") is False:
            raise RuntimeError(f"MCP query failed: {str(result.get('summary', ''))[:200]}")
        return result

    def _mark_failed(self, e: Exception) -> None:
        print(f"TigerGraph MCP call failed ({type(e).__name__}: {e}); falling back to pyTigerGraph")

    # ------------------------------------------------------------------
    # pyTigerGraph fallback connection (same shape as agent/graph.py)
    # ------------------------------------------------------------------
    @property
    def conn(self):
        if self._conn is None:
            import pyTigerGraph as tg

            self._conn = tg.TigerGraphConnection(
                host=os.environ.get("TG_HOST", ""),
                graphname=os.environ.get("TG_GRAPH", "FraudGraph"),
                gsqlSecret=os.environ.get("TG_SECRET", ""),
                tgCloud=True,
            )
            try:
                self._conn.getToken(self._conn.createSecret())
            except Exception:
                pass
        return self._conn

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------
    def run_installed_query(self, name: str, params: dict) -> Any:
        """Run an installed query via MCP, falling back to pyTigerGraph."""
        try:
            return self._mcp_call(RUN_INSTALLED_QUERY, {"query_name": name, "params": params or {}})
        except Exception as e:
            self._mark_failed(e)
            return self.conn.runInstalledQuery(name, params or {})

    @staticmethod
    def _inline_params(gsql: str, params: dict) -> str:
        def esc(v: Any) -> str:
            if isinstance(v, bool):
                return "true" if v else "false"
            if isinstance(v, (int, float)):
                return repr(v)
            s = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{s}"'

        for key, value in params.items():
            gsql = gsql.replace(f"${{{key}}}", esc(value))
        # Bind GSQL header params (INTERPRET QUERY (STRING t_id) ...) as
        # literal values inside the query body and strip the declared
        # parameter list — MCP's run_query tool takes query_text only and
        # cannot bind declared parameters.
        header, body = gsql, gsql
        match = re.search(r"\(([^()]*)\)", gsql)
        body_start = gsql.find("{")
        if match and body_start != -1:
            header = gsql[:body_start]
            header = header.replace(f"({match.group(1)})", "()", 1)
            body = gsql[body_start:]
            for key, value in params.items():
                body = re.sub(rf"\b{re.escape(key)}\b", esc(value), body)
            gsql = header + body
        return gsql

    def run_interpreted_query(self, gsql: str, params: dict) -> Any:
        """Run an interpreted query via MCP, falling back to pyTigerGraph."""
        try:
            if params:
                gsql = self._inline_params(gsql, params)
                if "${" in gsql:
                    raise ValueError("unresolved query parameters after inlining")
            return self._mcp_call(RUN_QUERY, {"query_text": gsql})
        except Exception as e:
            if not self._mcp_failed:
                self._mark_failed(e)
            if params:
                return self.conn.runInterpretedQuery(gsql, params)
            return self.conn.runInterpretedQuery(gsql)

    # ------------------------------------------------------------------
    def close(self) -> None:
        """Shut down the MCP session and subprocess, if running."""
        stack, self._stack, self._session, self.use_mcp = self._stack, None, None, False
        if stack is not None and self._loop is not None and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(stack.aclose(), self._loop).result(timeout=10)
            except Exception:
                pass
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
            self._loop = None


if __name__ == "__main__":
    client = TigerGraphMCP()
    ok = client.connect()
    tools = client.list_tools()
    print(f"MCP connected: {ok}")
    print(f"MCP tools: {len(tools)}")
    for name in sorted(tools)[:10]:
        print(f"  {name}")
    client.close()
    print("Self-check done.")
