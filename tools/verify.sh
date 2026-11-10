#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source tools/environment.sh
uv sync --locked --group dev
if [[ "${1:-}" == "--fix" ]]; then
  uv run --locked ruff check --fix .
  uv run --locked ruff format .
fi
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m pytest -q
uv run --locked python -m aia_mp1 --help
