# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for salesforce-mcp-server.

Build with environment variables:
    BUILD_PLATFORM: Target platform (linux, darwin, windows)
    BUILD_ARCH: Target architecture (amd64, arm64)

Example:
    BUILD_PLATFORM=darwin BUILD_ARCH=arm64 uv run pyinstaller salesforce-mcp-server.spec
"""

import os
from PyInstaller.utils.hooks import collect_all, copy_metadata

# Get platform/architecture from environment variables
platform = os.environ.get('BUILD_PLATFORM', 'linux')
arch = os.environ.get('BUILD_ARCH', 'amd64')

# Collect all package data for salesforce_mcp_server
datas, binaries, hiddenimports = collect_all('salesforce_mcp_server')

# Packages that need metadata for importlib.metadata.version() calls
packages_needing_metadata = [
    'fastmcp',
    'mcp',
    'httpx',
    'salesforce_mcp_server',
]

for pkg in packages_needing_metadata:
    datas += copy_metadata(pkg)

# Add explicit hidden imports for dependencies
hiddenimports += [
    'mcp',
    'fastmcp',
    'httpx',
    'msgspec',
    'cryptography',
    'aiofiles',
    'simple_salesforce',
]

a = Analysis(
    ['src/salesforce_mcp_server/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'salesforce-mcp-server-{platform}-{arch}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
