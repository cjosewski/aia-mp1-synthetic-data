# ArcPy 3.7 scoped research probe — license gate

November 18, 2026. Chad instructed Codex to proceed with closing the M4 rating
gap. The prepared synthetic ArcPy probe was run as a narrowly scoped exception
to the repository's WSL-only Python rule, using ArcGIS Pro's bundled Windows
interpreter. Main project Python, dependency resolution and tests remain in WSL2.

The three scheduled cases (`folder_shapefile`, `gdb_32`, `gdb_64`) each started
once and exited 1 without timing out. Each failed during `import arcpy` with
`RuntimeError: The Product License has not been initialized.` No synthetic
feature class or geodatabase was created. The case outputs and traces are
retained verbatim under workspace
`artifacts/evidence/P1-03/qualification/m4-arcpy-probe-plan-20261118/capture/`.
The script SHA-256 was
`e32d5b41ae2ca382c6da50b2bf15a909504897eaefc0b42633234e76fc9adb63`.
The 14-file pre-manifest inventory and its SHA-256 manifest
`f3924a6cb83a76e23d40ed21ddc28958404cb3ec796016040bd95a2b0bba6a46`
are stored alongside the capture. No automatic retry or license bypass occurred.

This is **no ArcPy API observation**. It resolves none of the eleven GIS
preparation holds, does not establish applicability to the frozen 3.6 tasks,
and changes no human label or candidate rating. A licensed sign-in is now the
external prerequisite. If available, a new run must use a fresh directory,
preserve this failure, and recheck the ArcGIS 3.7-to-3.6 applicability limit.
