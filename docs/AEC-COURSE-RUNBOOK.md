# P1-03 — Blind baseline review of AEC data

Review 20 AEC questions and answers, four from each original category: GIS scripting, AEC automation, structural-analysis code, CAD APIs and simulation. Use the six course dimensions displayed for every item. The full scoring anchors and thresholds are in [the assessed rubric](../config/aec-course/rubric.json).

1. On the Windows project workstation, double-click `Review-AEC-Baseline.cmd` in the NAS AEC-baseline-review-001 handoff folder. It opens the Python CLI in Ubuntu.
2. Read the task, generated fields and supplied references. Evaluate the written response. You do not need to execute its code.
3. Enter 1 for pass or 0 for fail on each displayed dimension. D3 asks whether every listed tool meets the course's homeowner availability and affordability rule. The existence of an API alone does not satisfy D3. D4 asks whether the work fits the stated user's capability and calls for professional help where needed. Use the homeowner/DIY anchor printed in the CLI. Record a concrete reason when an AEC item fails a literal course requirement.
4. Add notes after the sixth decision. The CLI saves each finished item. Enter q to quit, then reopen the launcher to resume. If you recognize an item whose judge scores you have seen, disclose that before declaring a blind review.
5. When all twenty are saved, tell Codex whether you finished before seeing judge ratings for these items.

## D3 correction for the November 18 baseline

Chad confirmed that his 20 original D3 ratings assessed API correctness. The frozen review is retained for audit. Calibration requires human and judge decisions on the same criterion.

1. Open `\\192.168.0.55\aia\Handoff\P1-03\AEC-baseline-review-001` on the Windows project workstation and double-click `Review-AEC-D3.cmd`.
2. Confirm the opening statement if it applies. The CLI retrieves the same 20 items and carries forward your D1, D2, D4, D5 and D6 ratings with their original label IDs.
3. For each tool list, enter **1** if every tool is something a typical homeowner already owns or could buy at a general hardware store for under $50, and none is a professional, specialty or trade-only tool. Otherwise enter **0**. An optional note can identify the deciding tool. Skip an uncertain item with **s** or save your place and exit with **q**.
4. When the remaining count reaches zero, tell Codex. Keep the judge results closed until the replacement human reference is frozen.

## Open the original six-dimension review manually

From Windows Terminal, enter `wsl -d Ubuntu`. In Ubuntu:

```bash
cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
export AIA_MP1_DOMAIN=aec-course
export AEC_ROOT=../artifacts/evidence/P1-03/aec-course
uv run --locked python -m aia_mp1 label --artifact-root "$AEC_ROOT" --assessment-id aec-course-baseline-review --reviewer "Chad Josewski" --review-stage blind
```

## Evidence and next steps

The course replay verifies the original generation ledgers against their frozen AEC cohort hashes, reruns schema, six heuristic checks and deduplication, excludes all 50 items from the previously judged cohort and retains the first ten eligible items per category. The original 200 first attempts stay in the denominator. Review selection is stratified and deterministic. A fresh evidence root can reproduce this with `AIA_MP1_DOMAIN=aec-course uv run --locked python tools/prepare_aec_course_baseline.py`. The benchmark supplies its uniform distribution (20% per category) for comparison across the five AEC categories.

After the human reference is frozen, a distinct locally served judge uses Instructor/Pydantic and a lower temperature than the generator to score the same dimensions for every retained item. Calibration uses these fixed items and requires ≥80% agreement separately on D1–D6. Only then use the weakest measured segment and dimension to revise the generator and run the corrected cohort. Report all thresholds, traces, iteration history, charts and the measured before/after failure reduction. Prior engineering ratings used different anchors and cannot establish agreement on this rubric.
