# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1: Builder - Install dependencies with uv
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Use copy link mode for efficient layer caching
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (layer caching optimization)
# Copy only dependency-related files first
COPY pyproject.toml uv.lock ./

# Install dependencies without the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application
COPY src/ ./src/
COPY README.md ./

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.14-slim-trixie AS runtime

# OCI Labels for GHCR metadata
LABEL org.opencontainers.image.title="Salesforce MCP Server"
LABEL org.opencontainers.image.description="Salesforce MCP Server with multi-user OAuth PKCE support for AI agents"
LABEL org.opencontainers.image.source="https://github.com/hypn4/salesforce-mcp-server"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="hypn4"

# Create non-root user for security
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home mcp

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder --chown=mcp:mcp /app/.venv /app/.venv

# Set up environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER mcp

# Health check - verify the server can start
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import salesforce_mcp_server; print('healthy')"]

# Default entrypoint
ENTRYPOINT ["salesforce-mcp-server"]

# Default port (cloud platforms set PORT automatically)
# Can override with: docker run -e PORT=3000 ...
ENV PORT=8000

# Expose default HTTP port
EXPOSE 8000

# Default to HTTP mode (port is read from PORT env var)
CMD ["--transport", "http"]
