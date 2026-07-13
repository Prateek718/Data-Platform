"""The analyst's tool layer: one contract, two backends.

The analyst never touches the dataset directly — it reads the record only through the five
read-only tools the Stage 7 MCP server exposes. :class:`AnalystTools` is that contract, and it
mirrors the server's real signatures: the tool inputs the protocol accepts, and the plain payload
dicts the tools return (a refusal arrives as its serialized dict, never as an exception).

Two backends implement it, and a golden parity test asserts they return identical payloads:

* :class:`DirectTools` calls the server's pure query core in-process — hermetic and fast, used by
  the unit tests and by the report verifier, where re-executing a query per numeric claim must not
  cost a subprocess round-trip.
* :class:`McpStdioTools` is a real MCP client that spawns the actual server as a subprocess and
  speaks the protocol to it over stdio — the honest demo path.

Payloads are typed ``dict[str, object]`` (the core's own annotation), not ``dict[str, Any]``:
under mypy strict, ``Any`` would silently disable checking everywhere a payload is read, whereas
``object`` forces the reader to narrow the type explicitly — which is exactly the discipline the
verifier depends on.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from collections.abc import Sequence
from concurrent.futures import Future
from types import TracebackType
from typing import Final, Protocol

# Imported from the SDK's submodules rather than the `mcp` package root: `tests/mcp/` makes ruff's
# isort read a bare `mcp` as first-party, which would shuffle it into the local import block.
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, TextContent

from data_platform.mcp import catalog, lineage, refresh
from data_platform.mcp import query as query_mod
from data_platform.mcp.loader import REPO_ROOT, Dataset
from data_platform.mcp.refusals import as_payload

Payload = dict[str, object]

# Config-carried timeouts (CLAUDE.md: thresholds are config, not inline magic numbers). Startup
# covers spawning the server and its checksum gate over the release artifacts; the call timeout
# bounds a single tool round-trip. Both are generous — they exist to fail loudly on a hung server
# rather than to police latency (a warm round-trip is single-digit milliseconds).
STARTUP_TIMEOUT_S: Final = 60.0
CALL_TIMEOUT_S: Final = 60.0


class AnalystTools(Protocol):
    """The five read-only tools, exactly as the MCP server exposes them."""

    def list_datasets(self) -> Payload: ...

    def get_schema(self, table: str) -> Payload: ...

    def query(
        self,
        table: str,
        *,
        metrics: Sequence[str] | None = None,
        states: Sequence[str] | None = None,
        districts: Sequence[str] | None = None,
        fy_from: str | None = None,
        fy_to: str | None = None,
        month: str | None = None,
    ) -> Payload: ...

    def get_lineage(self, fact_ids: str | Sequence[str]) -> Payload: ...

    def request_refresh(self) -> Payload: ...


class DirectTools:
    """In-process backend: calls the query core directly over an already-loaded dataset."""

    def __init__(self, dataset: Dataset) -> None:
        self._ds = dataset

    def list_datasets(self) -> Payload:
        return {"datasets": catalog.list_datasets(self._ds)}

    def get_schema(self, table: str) -> Payload:
        return as_payload(catalog.get_schema(table))

    def query(
        self,
        table: str,
        *,
        metrics: Sequence[str] | None = None,
        states: Sequence[str] | None = None,
        districts: Sequence[str] | None = None,
        fy_from: str | None = None,
        fy_to: str | None = None,
        month: str | None = None,
    ) -> Payload:
        return as_payload(
            query_mod.query(
                self._ds,
                table,
                metrics=metrics,
                states=states,
                districts=districts,
                fy_from=fy_from,
                fy_to=fy_to,
                month=month,
            )
        )

    def get_lineage(self, fact_ids: str | Sequence[str]) -> Payload:
        return lineage.get_lineage(self._ds, fact_ids)

    def request_refresh(self) -> Payload:
        return refresh.request_refresh()


class McpProtocolError(RuntimeError):
    """The MCP server returned an error, or a response the client could not read."""


class McpStdioTools:
    """MCP-protocol backend: spawns the real server as a subprocess and calls it over stdio.

    The MCP client SDK is async and its stdio transport owns anyio cancel scopes that must be
    entered and exited in the SAME task. So the session lives inside one long-lived coroutine on a
    dedicated event-loop thread, and the synchronous tool methods hand it work over a queue — the
    contract stays sync (the graph nodes and the verifier are plain Python), while the transport
    keeps its structured-concurrency invariants.
    """

    def __init__(
        self,
        *,
        startup_timeout_s: float = STARTUP_TIMEOUT_S,
        call_timeout_s: float = CALL_TIMEOUT_S,
    ) -> None:
        self._startup_timeout_s = startup_timeout_s
        self._call_timeout_s = call_timeout_s
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="mcp-stdio", daemon=True)
        self._ready: Future[tuple[str, ...]] = Future()
        self._work: asyncio.Queue[_Request | None] = asyncio.Queue()
        self._tool_names: tuple[str, ...] = ()

    # --- lifecycle ---------------------------------------------------------------------------

    def __enter__(self) -> McpStdioTools:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def start(self) -> None:
        """Spawn the server, open the session, and block until it is initialized."""
        self._thread.start()
        self._tool_names = self._ready.result(self._startup_timeout_s)

    def close(self) -> None:
        """Close the session and reap the server subprocess."""
        if not self._thread.is_alive():
            return
        self._loop.call_soon_threadsafe(self._work.put_nowait, None)
        self._thread.join(self._call_timeout_s)

    def tool_names(self) -> tuple[str, ...]:
        """The tools the running server advertises, in the order it registered them."""
        return self._tool_names

    # --- the five tools ----------------------------------------------------------------------

    def list_datasets(self) -> Payload:
        return self._call("list_datasets", {})

    def get_schema(self, table: str) -> Payload:
        return self._call("get_schema", {"table": table})

    def query(
        self,
        table: str,
        *,
        metrics: Sequence[str] | None = None,
        states: Sequence[str] | None = None,
        districts: Sequence[str] | None = None,
        fy_from: str | None = None,
        fy_to: str | None = None,
        month: str | None = None,
    ) -> Payload:
        arguments: dict[str, object] = {"table": table}
        _put(arguments, "metrics", metrics)
        _put(arguments, "states", states)
        _put(arguments, "districts", districts)
        _put(arguments, "fy_from", fy_from)
        _put(arguments, "fy_to", fy_to)
        _put(arguments, "month", month)
        return self._call("query", arguments)

    def get_lineage(self, fact_ids: str | Sequence[str]) -> Payload:
        ids = fact_ids if isinstance(fact_ids, str) else list(fact_ids)
        return self._call("get_lineage", {"fact_ids": ids})

    def request_refresh(self) -> Payload:
        return self._call("request_refresh", {})

    # --- transport ---------------------------------------------------------------------------

    def _call(self, tool: str, arguments: dict[str, object]) -> Payload:
        if not self._thread.is_alive():
            raise McpProtocolError("the MCP stdio session is not running; call start() first")
        result: Future[Payload] = Future()
        self._loop.call_soon_threadsafe(self._work.put_nowait, _Request(tool, arguments, result))
        return result.result(self._call_timeout_s)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        finally:
            self._loop.close()

    async def _serve(self) -> None:
        """Own the stdio session for its whole life, serving queued calls until told to stop."""
        try:
            async with (
                stdio_client(_server_parameters()) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                tools = await session.list_tools()
                self._ready.set_result(tuple(tool.name for tool in tools.tools))
                while True:
                    request = await self._work.get()
                    if request is None:
                        return
                    try:
                        request.result.set_result(
                            _payload(await session.call_tool(request.tool, request.arguments))
                        )
                    except Exception as exc:  # surfaced to the caller blocked on this future
                        request.result.set_exception(exc)
        except Exception as exc:
            if not self._ready.done():  # the session never came up: fail start(), not a call
                self._ready.set_exception(exc)
            else:
                raise


class _Request:
    """One queued tool call and the future the calling thread is blocked on."""

    def __init__(self, tool: str, arguments: dict[str, object], result: Future[Payload]) -> None:
        self.tool = tool
        self.arguments = arguments
        self.result = result


def _server_parameters() -> StdioServerParameters:
    """Spawn the real server the way the repo runs it: `python -m data_platform.mcp` from the root.

    The current interpreter is reused (``sys.executable``), so the subprocess inherits this
    environment's dependencies without needing ``uv`` on PATH.
    """
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "data_platform.mcp"],
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )


def _payload(result: CallToolResult) -> Payload:
    """Read a tool result off the wire.

    A refusal is a normal, successful tool result whose payload says ``refused: true`` — it is
    returned as data. ``isError`` means the protocol call itself failed (an unknown tool, a
    malformed argument, a crashed server), which is a bug in this client, not an answer.
    """
    if result.isError:
        raise McpProtocolError(f"MCP tool call failed: {_error_text(result)}")
    if result.structuredContent is not None:
        return dict(result.structuredContent)
    for block in result.content:  # fall back to the JSON text block
        if isinstance(block, TextContent):
            parsed = json.loads(block.text)
            if isinstance(parsed, dict):
                return dict(parsed)
    raise McpProtocolError("MCP tool result carried no readable payload")


def _error_text(result: CallToolResult) -> str:
    return " ".join(b.text for b in result.content if isinstance(b, TextContent)) or "(no detail)"


def _put(arguments: dict[str, object], name: str, value: object) -> None:
    """Send only the arguments the caller actually set, so the wire call reads like the API."""
    if value is not None:
        arguments[name] = (
            list(value) if isinstance(value, Sequence) and not isinstance(value, str) else value
        )
