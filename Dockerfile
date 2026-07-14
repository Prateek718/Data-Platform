# The MCP server, containerized: `docker run -i` speaks JSON-RPC to it over stdin/stdout.
#
# Why stdio and not HTTP: the server IS a stdio MCP server (Stage 7), and a container does not
# change that. `docker run -i` connects the client's pipes straight to the process's, so an MCP
# client can spawn `docker run -i ...` exactly as it would spawn the local command. No transport is
# added, no port is opened, and the read-only, no-mutation-verb surface is unchanged.
#
# The dataset is NOT baked in by default: it is a 5 MB sealed release fetched at start into a
# mounted volume, verified twice on the way in. `--build-arg BAKE_DATASET=1` bakes it for offline
# use (see README).

FROM python:3.12-slim-bookworm@sha256:9c1d9ed7593f2552a4ea47362ec0d2ddf5923458a53d0c8e30edf8b398c94a31

# uv, pinned to the version the repo's CI and local toolchain use.
COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, from the lockfile, so a code change does not re-resolve the world.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the project itself.
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Optionally bake the sealed dataset into the image for offline use. Off by default: an image is a
# poor place for 68 MB of data that is already published, immutable and DOI-cited.
ARG BAKE_DATASET=0
RUN if [ "$BAKE_DATASET" = "1" ]; then uv run data-platform-bootstrap; fi

# Non-root. /data is where the dataset lives — a mounted volume by default — and the server reads
# dist/v1.0 from the repo root, so /app/dist points at it.
RUN useradd --create-home --uid 10001 platform \
    && mkdir -p /data \
    && if [ ! -e /app/dist ]; then ln -s /data /app/dist; fi \
    && chown -R platform:platform /app /data
USER platform

ENV PATH="/app/.venv/bin:$PATH"

# The dataset is fetched (and verified twice) at start unless it is already present and passes the
# server's own checksum gate; then the MCP server takes over stdin/stdout. exec so the server is
# PID 1's process and signals reach it.
ENTRYPOINT ["/bin/sh", "-c", "data-platform-bootstrap --dist-root \"${DIST_ROOT:-/app/dist}\" >&2 && exec \"$@\"", "--"]
CMD ["data-platform-mcp"]
