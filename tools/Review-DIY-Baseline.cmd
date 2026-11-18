@echo off
wsl.exe -d Ubuntu -- bash -lc "cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data && export AIA_MP1_TOOLS=$HOME/.local/share/aia-mp1-tools AIA_MP1_DOMAIN=home-diy && source tools/environment.sh && uv run --locked python -m aia_mp1 label --artifact-root ../artifacts/evidence/P1-03/home-diy --assessment-id diy-baseline-review-001 --reviewer 'Chad Josewski' --review-stage blind"
pause
