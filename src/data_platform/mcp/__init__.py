"""Read-only MCP server over the sealed MGNREGA canonical series v1.0.0.

Serves the checksum-verified ``dist/v1.0`` release artifacts (see ``SHA256SUMS.txt``) as a
constrained, lineage-aware query surface. The core (loader, catalog, query, lineage, refusals) is a
pure library with no MCP or async dependency; the protocol adapter is a thin layer over it.
"""
