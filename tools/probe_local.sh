#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source tools/environment.sh
uv run --locked python tools/probe_local.py --output ../artifacts/evidence/P1-03/kickoff-20261109/endpoint-probe.json
