# Restart handoff — November 12, 2026

Chad reported: "All software has in the list has now been installed."
This applies to the discussed engineering-software shortlist. Exact versions,
license editions, package environments and API execution have not been verified.
Chad is restarting the machine, then completing the MP1 human reviews.

## Resume the blind reviews

Open PowerShell or Command Prompt and run:

```text
wsl.exe -d Ubuntu --cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data --exec bash
```

Then, inside Ubuntu:

```bash
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
uv run --locked python -m aia_mp1 label --assessment-id baseline-review-001 --reviewer "Chad Josewski" --review-stage blind
```

The cohort and 20-item queue already exist. Do not recreate them or rerun
collection. Herd is not required for human labeling. Use 1 for pass, 0 for fail,
s to skip an item, or q to quit. An item saves after all six judgments and notes.
The same command resumes completed-item progress; do not add --resume.

After reviewing:

```bash
uv run --locked python -m aia_mp1 label-status --assessment-id baseline-review-001
```

Expect completed: 20. Follow docs/ASSESSED-RUNBOOK.md Step 7 to declare and freeze
the reference only if the reviews were truly blind. A distinct stronger judge
still needs selection and qualification before assessed judging.

## Software and tools

- Desktop shortlist: QGIS, Blender/Bonsai, CloudCompare, ParaView, ArcGIS Pro,
  Revit, Civil 3D, Fusion, FreeCAD and SolidWorks.
- Package/solver shortlist: OpenSeesPy, SciPy, scikit-fem, CadQuery,
  IfcOpenShell, Gmsh and CalculiX. Keep separate environments outside locked MP1.
- The visual guide is .lavish/engineering-software-guide.html. Localhost worked
  for Lavish; Chad explicitly said not to pursue Tailscale troubleshooting.
- Remember remains disabled in Codex at Chad's request. This handoff does not
  invoke or re-enable that plugin. Its previously saved notes are preserved.
- Latest observed review status on November 12: 0/20 complete. Recheck on resume;
  this handoff does not claim any human labels or engineering execution results.
