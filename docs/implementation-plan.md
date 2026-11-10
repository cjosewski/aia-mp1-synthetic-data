# P1-03 next slice: human labeling and judge calibration

Status: approved by Chad November 9, 2026 ("The assignment has been accepted. The plan is approved. Go."). The software slice is implemented with 166 passing offline tests and a five-item diagnostic review queue. Live judge execution met a bounded WSL connection-timeout blocker before any model request; real labels and measured calibration remain pending. Evidence: `artifacts/evidence/P1-03/labeling-judge-20261110T035628Z/`. The [SDD](SDD-P1-03.md) specifies the full project; steps below retain the approved implementation scope.

## Requirements summary

Deliver independently runnable human-labeling, judge and calibration commands in
`aia-mp1-synthetic-data`, with immutable input identities and auditable results.
Finish with verified software and a review queue ready for Chad. Actual calibration
can finish only after authentic human labels exist.

The approved kickoff ended with generation/gating and a five-item smoke result
(`aia-mp1-synthetic-data/docs/requirements.md:13`). Its D2 diagnostic is already
complete: vocabulary coverage and the `review`/`reviewed` mismatch explain the two
flags (`aia-mp1-synthetic-data/docs/smoke-d2-review-2026-11-09.md`, Reproduced cause).
Preserve that run and its failed 3/5 gate result.

The next-stage contract requires authentic labels on at least 20 baseline and 20
corrected items, six binary dimensions, independent judge prompting, and at least
80% agreement in every dimension before generator correction
(`aia-mp1-synthetic-data/docs/requirements.md:66`). All five categories and source
permission restrictions remain applicable (`docs/requirements.md`, Payload and
categories; Source permissions and benchmark decision).

## Proposed implementation

Paths below are relative to `aia-mp1-synthetic-data` unless stated otherwise.

1. **Freeze assessment inputs and separate output identities.** Add
   `src/aia_mp1/assessment.py` and `evaluation_schemas.py`. Reuse the existing
   generation-evidence validation in `generate.py:66` and provenance envelope in
   `schemas.py`. Store new artifacts under
   `../artifacts/evidence/P1-03/assessments/<assessment-id>/`, referencing the run,
   data hash, item/trace IDs, rubric hash and version, selection and code identity.
   Explicitly distinguish a diagnostic selection from a gate-retained assessment
   population. Freeze selections before labels/judgments; validate gate evidence
   and reject mismatched or missing inputs. The original run directory is read-only.

2. **Add authentic human labeling.** Add `labels.py` and CLI commands for creating
   a queue, labeling and reporting coverage. Display the complete payload and
   rubric anchors, with no judge suggestions. Accept six strict binary decisions,
   reviewer identity, timestamp and notes; skip leaves the item unresolved.
   Resume only against matching immutable inputs. Revisions append an explicit
   superseding record rather than erasing the previous label. For assessed data,
   select a reproducible balanced set of at least 20 items (four per category for
   the first 20); record seed and population before review. The five existing
   smoke items are available only as a diagnostic queue, including both rejections.

3. **Add an independent judge invocation.** Add `judge.py`,
   `prompts/judge-v1.md` and `config/judge.example.json`; extend `cli.py` and, only
   as necessary, `model_client.py` for a typed judgment response. Use the configured
   local endpoint, a separate judge prompt and lower temperature where supported.
   Judge each item on D1-D6 with a short justification per dimension. Supply no
   human labels or prior decisions. Treat item text as untrusted evaluation data.
   Retain every request start, raw completion or transport failure, bounded retry,
   model/settings and prompt/rubric identity. Missing/malformed/exhausted judgments
   remain unresolved. Reusing the generator model is disclosed; a separate prompt
   does not imply independent model errors or factual verification.

4. **Add calibration reports.** Add `calibration.py`. Join human and judge records
   only by matching assessment, item, payload and rubric identities. Report exact
   agreement numerators/denominators, coverage, confusion counts and disagreements
   for each dimension, plus category breakdowns. Incomplete required judgments or
   human coverage prevents a readiness pass. Diagnostic smoke agreement cannot
   certify calibration. A qualifying assessment needs at least 50 retained items,
   all five categories, at least 20 complete human labels, and >=80% agreement on
   every dimension. Pin the selected judge prompt/model/settings/rubric in a
   calibration receipt. Prompt revisions get separate judge-run IDs on fixed
   calibration inputs; no automatic rewriting from human labels.

5. **Document and verify.** Update `README.md`, `AGENTS.md`, `ITERATION_LOG.md` and
   the stage-boundary text in `docs/requirements.md` after implementation. Add
   focused tests for assessment lineage, labeling/resume, judge failures and
   calibration math. Preserve unrelated existing edits and untracked files.
   Do not publish, update GitHub, alter Herd or change reference dates in this slice.

## Acceptance criteria

- Creating a diagnostic queue from all five saved smoke items changes none of the
  original evidence hashes and records that it is not assessed baseline data.
- Changed data/rubric hashes, foreign trace IDs, duplicate/conflicting records,
  incomplete ledgers and output-ID collisions fail clearly without overwrites.
- Human labeling supports interruption/resume and explicit amendments; unanswered
  or skipped dimensions never become passes. No assistant-generated human labels.
- Judge response validation rejects missing/extra dimensions and non-binary values.
  Failure, retry and interruption tests prove each request is accounted for and
  credentials are absent from artifacts. No hosted-provider fallback.
- Agreement fixtures prove 16/20 reaches 80%, 15/20 does not, zero comparisons are
  undefined, and incomplete coverage cannot pass. A five-item diagnostic remains
  ineligible even at 100% agreement. Reports name all six dimensions.
- Existing generation/gating tests remain green. Locked WSL verification passes
  Ruff, pytest and each new CLI's help/error paths.
- A bounded judge smoke run against the existing five items produces auditable
  outputs if the already configured endpoint is available; otherwise retain a
  concrete connectivity failure. It never establishes human agreement by itself.

These criteria implement the measurement and runtime rules in
`docs/requirements.md:75` onward and the existing contribution rules in `AGENTS.md`.

## Risks and mitigations

- **Lexical gate bias:** keep the present gate rules fixed for this slice. Both
  rejected smoke items remain in the diagnostic queue. Do not broaden vocabulary
  or tune generation to manufacture retention; proposed gate changes need separate
  replay/versioning and the same cohort policy for baseline and corrected runs.
- **No qualifying dataset yet:** the current source manifest is smoke-only and
  there are only five generated items. Build and verify workflow mechanics now;
  assessed collection needs source/benchmark disposition and a fixed gate policy.
- **Correlated judge errors:** disclose same-model use, require authentic labels,
  preserve disagreement examples and avoid claiming that agreement proves truth.
- **Calibration overfitting:** preserve all prompt versions and fixed selections;
  distinguish calibration-set agreement from independently measured generalization.
- **Human input dependency:** software completion ends at a usable review queue;
  calibration readiness remains pending until Chad supplies sufficient labels.
- **Unresolved instructor decisions:** keep engineering benchmark disposition,
  the exact-80% improvement boundary and coaching acceptance explicit, as recorded
  in `docs/requirements.md`; this plan does not decide them.

## Verification and stop condition

Run Python and tests in WSL2 Ubuntu using the existing locked environment and
`bash tools/verify.sh`. Consult current Context7 documentation before changing
library-specific client/validation APIs. Use clearly synthetic test fixtures and
retain live output outside Git. Read back artifact hashes and exercise resumable
labeling with fixtures; never simulate a human assessment on real items.

After owner approval, implement through verified commands and the diagnostic
review queue. Continue calibration only when real labels are available. Leave
50-item baseline/corrected collection, five charts, Phase B generator correction,
demo and coaching acceptance for the following slice. No new multi-file edits
start before approval under workspace `AGENTS.md` (Settled constraints).

## Publication authorization

On November 9, 2026 Chad requested that this project be committed to GitHub and initialized as a repository. The implementation, SDD and this approved plan are published in the private implementation repository. Raw evidence and local credentials/configuration remain outside Git. Issue #4 in private aia-plan remains the execution tracker.
