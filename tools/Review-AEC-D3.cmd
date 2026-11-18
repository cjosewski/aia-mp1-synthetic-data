@echo off
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data && export AIA_MP1_TOOLS=$HOME/.local/share/aia-mp1-tools AIA_MP1_DOMAIN=aec-course && source tools/environment.sh && uv run --locked python tools/review_aec_d3.py"
pause
