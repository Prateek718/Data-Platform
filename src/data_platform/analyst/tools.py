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

from collections.abc import Sequence
from types import TracebackType
from typing import Protocol

from data_platform.mcp.loader import Dataset

Payload = dict[str, object]


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
        raise NotImplementedError

    def get_schema(self, table: str) -> Payload:
        raise NotImplementedError

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
        raise NotImplementedError

    def get_lineage(self, fact_ids: str | Sequence[str]) -> Payload:
        raise NotImplementedError

    def request_refresh(self) -> Payload:
        raise NotImplementedError


class McpStdioTools:
    """MCP-protocol backend: spawns the real server as a subprocess and calls it over stdio."""

    def __enter__(self) -> McpStdioTools:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    def tool_names(self) -> tuple[str, ...]:
        raise NotImplementedError

    def list_datasets(self) -> Payload:
        raise NotImplementedError

    def get_schema(self, table: str) -> Payload:
        raise NotImplementedError

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
        raise NotImplementedError

    def get_lineage(self, fact_ids: str | Sequence[str]) -> Payload:
        raise NotImplementedError

    def request_refresh(self) -> Payload:
        raise NotImplementedError
