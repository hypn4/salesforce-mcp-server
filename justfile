# Salesforce MCP Server - Development Commands

# Default recipe: show available commands
default:
    @just --list

# Install dependencies
install:
    uv sync

# Install with dev dependencies
install-dev:
    uv sync --group dev

# Run the server in stdio mode (for Claude Desktop)
run:
    uv run salesforce-mcp-server --transport stdio

# Run the server with DEBUG logging
run-debug:
    LOG_LEVEL=DEBUG uv run salesforce-mcp-server --transport stdio

# Run the server with WARNING logging (quieter)
run-quiet:
    LOG_LEVEL=WARNING uv run salesforce-mcp-server --transport stdio

# Run the server in HTTP mode (for web clients)
run-http:
    uv run salesforce-mcp-server --transport http

# Run the server in HTTP mode with DEBUG logging
run-http-debug:
    LOG_LEVEL=DEBUG uv run salesforce-mcp-server --transport http

# Run with MCP Inspector for debugging
inspector:
    uv run mcp dev src/salesforce_mcp_server/server.py

# Run with MCP Inspector and DEBUG logging
inspector-debug:
    LOG_LEVEL=DEBUG uv run mcp dev src/salesforce_mcp_server/server.py

# Run all tests
test:
    uv run pytest tests/ -v

# Run tests with coverage
test-cov:
    uv run pytest tests/ -v --cov=src/salesforce_mcp_server --cov-report=term-missing

# Run linter
lint:
    uv run ruff check src/ tests/

# Run linter and fix auto-fixable issues
lint-fix:
    uv run ruff check src/ tests/ --fix

# Format code
fmt:
    uv run ruff format src/ tests/

# Check formatting without changing files
fmt-check:
    uv run ruff format src/ tests/ --check

# Type check (requires pyright)
typecheck:
    uv run pyright src/

# Run all checks (lint + format check + tests)
check: lint fmt-check test

# Clean up cache files
clean:
    rm -rf .pytest_cache .ruff_cache __pycache__ .coverage
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Show registered MCP tools
tools:
    uv run python -c "from salesforce_mcp_server.server import mcp; tools = list(mcp._tool_manager._tools.keys()); [print(f'  - {t}') for t in sorted(tools)]; print(f'\nTotal: {len(tools)} tools')"

# === Docker ===

# Build Docker image (VERSION arg required for setuptools-scm)
docker-build version="0.0.0-dev":
    docker build --build-arg VERSION={{version}} -t salesforce-mcp-server .

# Run in Docker (HTTP mode)
docker-run:
    docker run -p 8000:8000 --env-file .env salesforce-mcp-server

# Run in Docker (STDIO mode)
docker-run-stdio:
    docker run -i --env-file .env salesforce-mcp-server --transport stdio

# === Binary Build ===

# Build standalone binary (requires pyinstaller)
build-binary:
    uv pip install pyinstaller
    uv run pyinstaller --onefile \
        --name salesforce-mcp-server \
        --collect-all salesforce_mcp_server \
        --hidden-import mcp \
        --hidden-import fastmcp \
        --hidden-import httpx \
        --hidden-import msgspec \
        --hidden-import cryptography \
        --hidden-import aiofiles \
        --hidden-import simple_salesforce \
        --hidden-import py_key_value_aio \
        src/salesforce_mcp_server/server.py
