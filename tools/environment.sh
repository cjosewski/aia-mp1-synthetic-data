#!/usr/bin/env bash
# Source from WSL to keep the interpreter, environment and cache on Linux storage.
export AIA_MP1_TOOLS="${AIA_MP1_TOOLS:-/tmp/aia-mp1-tools}"
export UV_PYTHON_INSTALL_DIR="$AIA_MP1_TOOLS/python"
export UV_PYTHON_BIN_DIR="$AIA_MP1_TOOLS/bin"
export UV_CACHE_DIR="$AIA_MP1_TOOLS/cache"
export UV_PROJECT_ENVIRONMENT="$AIA_MP1_TOOLS/venv"
export PATH="$AIA_MP1_TOOLS/bin:$PATH"
