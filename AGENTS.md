# MP1 synthetic data and evaluation

This repository owns the implementation, [SDD](docs/SDD-P1-03.md) and [operator runbook](docs/RUNBOOK.md) for P1-03 / Mini Project 1. The runbook owns the step-by-step human-review procedure; `README.md` provides the entry point and developer/CLI reference. Program coordination and the live checklist remain in private `aia-plan` / issue #4. Read `docs/requirements.md`, the SDD, runbook and `README.md` before changing behavior.

## Current boundary

On November 9, 2026 Chad stated, "The assignment has been accepted. The plan is approved. Go." Record assignment acceptance as owner-reported. The approved next slice adds immutable assessment snapshots, authentic human labeling, independently prompted local judging and calibration reports to generation/gating. Multi-batch assessed collection, full analysis/charts and generator correction remain subsequent work. Owner-reported acceptance does not fabricate missing labels or model measurements. Courses 5–8 and their exercises remain separately pending.

## Implementation rules

- Run Python, dependency resolution and tests in WSL2 Ubuntu. Use Pydantic v2 and Instructor with the configured local OpenAI-compatible endpoint. Do not silently fall back to hosted models or change Herd services/settings.
- The canonical payload has seven fields: `question`, `answer`, `equipment_problem`, `tools_required`, `steps`, `safety_info`, `tips`. Metadata lives outside the payload. The portal field `equipment_problem` takes precedence over the copied issue's `problem` spelling.
- Persist every generation attempt and its raw completion or explicit transport failure. Bound retries and timeouts. Never overwrite an existing run. Report initial-attempt schema validity separately from retry recovery and gate retention.
- Assessment artifacts live in `artifacts/evidence/P1-03/assessments/`, separate from immutable generation runs. Validate source hashes, the frozen rubric/selection and ledger checkpoints. Human labels are append-only with explicit superseding IDs; interrupted writes require inspection. Judge resume consumes previously started attempts, including requests with unknown outcomes. Diagnostic agreement never qualifies as assessed calibration.
- A stronger judge selection needs a recorded basis and a distinct model for assessed use. Same-model smoke judging is diagnostic only. Never supply assistant decisions as human labels. Readiness requires complete coverage and at least 80% agreement in every dimension, with at least 20 human labels and 50 retained items across all five categories.
- Cheap quality checks are heuristics. Pending rubric checks are not passes. Do not fabricate human labels, baseline failures, model measurements or instructor acceptance.
- Only licensed open sources or standalone personal material may enter datasets. Public access alone is not reuse permission. Exclude employer/client material, proprietary physiology and medical simulation. Keep source permission/provenance records.
- Raw generated data, labels, traces and charts belong outside Git under the workspace's `artifacts/evidence/P1-03/`; examples/tests must be clearly synthetic. Never log API credentials, request authorization headers or credential-file contents.
- Keep all five categories. Preserve the six-dimensional rubric and all course thresholds; record ambiguities and instructor decisions instead of silently weakening criteria.
- Chad authorized GitHub repository initialization and publication on November 9, 2026. This implementation repository is private at `github.com/cjosewski/aia-mp1-synthetic-data`; its SDD and approved implementation plan live in `docs/`. Keep raw evidence and local configuration excluded. Program tracking stays in private `aia-plan` / issue #4; preserve manual Status, reference dates and unrelated fields. Changes to Herd/shared-platform services remain outside this work. Commit as Chad Josewski <cjosewski@gmail.com>.
- You may be working alongside other agents. Respect file ownership, preserve unrelated edits and coordinate interface changes.

## Verification

Use the locked environment and run `python -m pytest -q`. Test invalid/malformed outputs, retry exhaustion, trace lineage, duplicate/category gates, denominator accounting and CLI failures. Use a real local smoke run only when an already available endpoint is reachable. Do not create tests that merely repeat implementation details.
