# Analysis and local evidence export

This offline procedure reads existing frozen cohorts, labels and judge ledgers.
It never requests model output or supplies human labels. A baseline-only report is
useful now, but cannot establish improvement or project completion.

New reports default to `course-per-dimension-80-v1`: at least 80% agreement in
**every** dimension, [restored by Chad November 17](ACCEPTANCE-RESTORED-80.md).
Pass `--acceptance-policy owner-overall-70-20261116` only to reproduce the historical
November 16 amendment. Saved reports replay their recorded policy; older reports
replay the original rule. Dimension rates, missing coverage and errors remain visible.

## 1. Open Ubuntu and prepare the locked environment

From Windows Terminal or PowerShell, enter `wsl -d Ubuntu`. Run the remaining
commands inside Ubuntu:

```bash
cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
uv sync --locked --extra analysis --group dev
```

## 2. Inspect the baseline without claiming missing judge measurements

Use a new report ID each time; reports cannot be overwritten:

```bash
uv run --locked --extra analysis python -m aia_mp1.analysis_cli report \
  --baseline baseline-review-001 --report-id baseline-human-summary-001
uv run --locked --extra analysis python -m aia_mp1.analysis_cli charts \
  --report-id baseline-human-summary-001
```

Expected status is **pending**, exit code **1**. This means the report was written
successfully but the comparison is incomplete. Exit 2 indicates an input, evidence
or file error that needs inspection. Exit 0 means the implemented measured
comparison criteria pass; it does not certify instructor acceptance.

Files appear under workspace
`artifacts/evidence/P1-03/analysis/baseline-human-summary-001/`:

- `report.json` contains separately named human-sample and population-judge
  metrics, raw integer denominators, source hashes and generation/gate accounting.
- `charts/` contains five PNGs, five SVGs, five source CSV tables and a chart receipt
  with captions, package versions and file hashes.
- Missing judge/cohort measurements appear as **NA**, never zero-percent scores.
  Human sample results do not fill the missing population judge measurements.

The charts cover dimension pass rates and corrected thresholds, category/dimension
heatmaps, frozen human/judge agreement, candidate/retained category counts, and
overall pass/fail bars. The final bars compare independent cohort aggregates;
they do not imply paired questions or paired statistical tests.

## 3. Produce the assessed comparison when both cohorts are ready

Replace the uppercase placeholders with the actual frozen assessment and judge
run IDs. Do not run this example before those records exist:

```bash
uv run --locked --extra analysis python -m aia_mp1.analysis_cli report \
  --baseline baseline-review-001 --baseline-judge BASELINE_JUDGE_ID \
  --corrected CORRECTED_ASSESSMENT_ID --corrected-judge CORRECTED_JUDGE_ID \
  --correction "Describe the frozen generator prompt correction and its hypothesis" \
  --report-id comparison-001
```

The report revalidates both source collections, cohort membership, rubric, human
ledgers, frozen references and judge attempts. Calibration is recomputed without
writing an extra calibration report. Baseline/corrected sources, gate policy,
sampling and model settings must match. The judge prompt, qualification and code
identity must match; the generator prompt must have a declared change. Endpoint,
authentication and local file paths do not themselves change the sampling policy.

Each population needs complete qualified judging, at least 50 balanced items and
20 frozen authentic reviews with at least 80% agreement in each dimension D1–D6. The
report also checks initial schema validity, baseline failure, corrected overall
and dimension pass rates, and relative failure reduction using exact fractions.
Zero baseline failures make relative reduction undefined. Exactly 80% reduction
is disclosed separately and remains pending under the conservative strict rule.

The worst baseline category/dimension uses highest failure fraction, then larger
observed N, then the declared category and dimension order. It is unavailable
until every segment has complete judge coverage. Its selection is a correction
target, not independent evidence that a correction worked.

## 4. Verify and export the record locally

```bash
uv run --locked --extra analysis python -m aia_mp1.analysis_cli verify \
  --report-id comparison-001
uv run --locked --extra analysis python -m aia_mp1.analysis_cli export \
  --report-id comparison-001 --export-id comparison-package-001
```

The export includes separate baseline/corrected JSONL when present, the report,
charts/tables, source manifests, human ledgers, judge records, gate decisions and
all original generation attempts. `export-manifest.json` seals file hashes.
It is a **local-only** evidence package; source permissions must be reviewed before
external sharing. No upload or publication occurs. Use `--no-charts` for a data-only
export without the optional plotting dependencies.

Later amendments never rewrite an old report. Verification detects the changed
ledger; preserve the old record and create a new report. The frozen blind reference
continues to govern independent agreement. An interrupted export may leave an
unsealed directory: preserve it for inspection and choose a new export ID.

Demo recording, coaching approval and unresolved instructor decisions remain
separate human deliverables even when the measured comparison status is ready.
