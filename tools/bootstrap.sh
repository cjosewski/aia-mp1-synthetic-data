#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source tools/environment.sh
mkdir -p "$AIA_MP1_TOOLS"
if ! command -v uv >/dev/null; then
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    https://astral.sh/uv/install.sh --output "$AIA_MP1_TOOLS/uv-install.sh"
  UV_INSTALL_DIR="$AIA_MP1_TOOLS/bin" UV_NO_MODIFY_PATH=1 sh "$AIA_MP1_TOOLS/uv-install.sh"
fi
uv --version
uv python install 3.12
if [[ ! -f uv.lock ]]; then
  uv lock
fi
uv sync --locked --group dev
