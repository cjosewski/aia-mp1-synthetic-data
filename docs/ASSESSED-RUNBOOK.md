# Assessed baseline: collection, blind review and calibration

Use this procedure for a new assessed baseline after its source pack is prepared.
The original five-item exercise remains in [RUNBOOK.md](RUNBOOK.md). Its two
reports are preserved; its post-review agreement cannot qualify this baseline.

**Current handoff:** the software is implemented. A cleared 50-task reference
pack and selected stronger judge have not yet been supplied. No assessed baseline
or 20-item review queue exists. You do not need to label anything now. The example
configuration deliberately fails until real source/model decisions are filled in.

## 1. Open Ubuntu and check the environment

In Windows PowerShell or Command Prompt:

```text
wsl.exe -d Ubuntu --cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data --exec bash
```

In Ubuntu Bash, run each line:

```bash
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
uv run --locked python --version
uv run --locked python -m aia_mp1 --help
```

Expect Python 3.12 and the commands `source-check`, `collect`, `collection-status`,
`cohort`, `cohort-status`, `assessment` and `freeze-human-reference` alongside the
existing commands. If tooling is missing, run `bash tools/bootstrap.sh` from this
directory and retry. Keep all subsequent commands in Ubuntu, at this directory.

## 2. Prepare and validate permitted references

Codex prepares the pack; Chad supplies source-use decisions where needed. Keep it
at `../artifacts/evidence/P1-03/references/engineering-v1.json`. The metadata shape
starts at [reference-pack.example.json](../config/reference-pack.example.json);
that pending template is not a valid corpus and must not be marked approved
without actual evidence. See [SOURCE-READINESS.md](SOURCE-READINESS.md).

The pack must include ten distinct task briefs for each of the five categories.
Each task has exactly `id`, `brief`, `category`, `source_refs`. Each source has:

| Field | Required content |
| --- | --- |
| `id`, `url`, `version`, `retrieved_at` | Stable source identity, original location, exact version/revision and retrieval date |
| `license`, `license_evidence`, `attribution` | Documentation-use terms, supporting reference and notices to preserve |
| `installation` | Required software/components and version assumptions |
| `text`, `content_sha256` | Actual permitted excerpt and SHA-256 of its UTF-8 text |
| `allowed_uses` | Include `assessed_generation`, `human_review`, `judge_context`, `local_evidence` only when supported |
| `export_permission` | `permitted` or `local_only`; local permission does not authorize redistribution |

The pack also records `approved_by`, `approved_at`, `approval_basis` and
`permission_status: approved_for_assessed_generation`. These are attributed human
decisions, not legal conclusions made by the validator. All references remain
outside Git. No answer-key scores, human labels or judge results belong in a pack.

Validate it offline:

```bash
uv run --locked python -m aia_mp1 source-check --pack ../artifacts/evidence/P1-03/references/engineering-v1.json
```

Expect `status: ready`, at least 50 tasks and the pack hash. A missing file,
permission, category or changed excerpt stops here before model calls. Resolving
that error means preparing the real missing evidence, not bypassing validation.

## 3. Prepare the generator configuration

Codex prepares ignored `config/assessed.local.json` using
[assessed.example.json](../config/assessed.example.json), preserving the existing
Herd endpoint and credential-file reference. It must contain the exact served
model ID, a pinned upstream `model_identity` and `model_sha256`, the pack path, baseline
purpose, two attempts per slot and the versioned assessed generator prompt.

The intended baseline generator remains Qwen3-30B-A3B Q4_K_M. Verify its artifact
checksum and reported endpoint ID before starting. Never paste the API key into
this document, Git or a command argument. A source pack with `local_only` content
keeps all resulting reference-bearing evidence local until export is resolved.

Chad starts the chosen model in Herd. Codex checks authenticated connectivity from
Ubuntu. A running server is needed for generation and judging, not human labeling.
Source and model preflight receipts belong beside the new evidence.

## 4. Collect the baseline

After Steps 2–3 are complete, choose a fresh collection ID. These commands use
`baseline-001`; use it only if it has not already been created:

```bash
uv run --locked python -m aia_mp1 collect --config config/assessed.local.json --collection-id baseline-001
```

The collector runs complete 50-slot batches, stopping once ten eligible unique
answers per category are available. It allows at most five batches and two
attempts per slot: 250 slots and 500 generation requests total. It retains raw
failures, rejections, duplicates and surplus items. Any batch below 95% initial
schema validity stops qualification; retries do not erase first-attempt failures.

After it exits:

```bash
uv run --locked python -m aia_mp1 collection-status --collection-id baseline-001
```

Expect `status: ready` and ten items in each `counts` entry. Read `planned_slots`,
`started_attempts`, `remaining_batch_budget`, validity and `reasons`. Exit 1 means
incomplete; exit 2 means a validation/setup error. No status here certifies answer
quality or assignment acceptance.

For a clean, resumable interruption, rerun the original collect command with
`--resume`. It requires identical code, sources, model/settings, prompt and budget.
An unknown request outcome, damaged checkpoint or existing writer lock requires
inspection. Do not remove evidence or expand the budget to force a ready result.

## 5. Freeze the cohort and create the review queue

Only after collection reports ready:

```bash
uv run --locked python -m aia_mp1 cohort --collection-id baseline-001 --cohort-id baseline-cohort-001
uv run --locked python -m aia_mp1 cohort-status --cohort-id baseline-cohort-001
uv run --locked python -m aia_mp1 assessment --cohort-id baseline-cohort-001 --assessment-id baseline-review-001
uv run --locked python -m aia_mp1 label-status --assessment-id baseline-review-001
```

Expect a frozen 50-item cohort and a queue with `selected: 20`, `completed: 0`.
The selection contains four items per category. The cohort's baseline/corrected
purpose is inherited; do not supply legacy single-run selection/purpose overrides.
Do not recreate these IDs or edit the frozen files.

## 6. Complete the 20 blind human reviews

Before seeing any judge results, Chad runs:

```bash
uv run --locked python -m aia_mp1 label --assessment-id baseline-review-001 --reviewer "Chad Josewski" --review-stage blind
```

Read each full answer and its displayed reference context. Apply the D1–D6 anchors
as in [the diagnostic rubric instructions](RUNBOOK.md#step-6--enter-your-six-judgments).
Use `1` for pass, `0` for fail, `s` to skip the whole item, or `q` to quit at a
dimension prompt. An item saves after all six judgments and the notes prompt.
Record reference/version evidence and uncertainty honestly. Resume with the same
command; do not add `--resume` to `label`.

When complete:

```bash
uv run --locked python -m aia_mp1 label-status --assessment-id baseline-review-001
```

Expect `completed: 20` and no pending items. Do not adopt model decisions merely
to achieve agreement. If you already saw judge output for these items, disclose
that; do not declare the reviews blind.

## 7. Freeze your independent reference

Chad runs this only if the declaration is true:

```bash
uv run --locked python -m aia_mp1 freeze-human-reference --assessment-id baseline-review-001 --reviewer "Chad Josewski" --declare-blind
```

This records your declaration and freezes the 20 label IDs, ledger prefix, rubric
and reference-pack identity. It refuses incomplete/unknown-stage reviews and a
queue with prior judge evidence. Later amendments preserve this original reference.
Software can record your declaration; it cannot verify what you saw elsewhere.

## 8. Qualify and select the stronger judge

Codex prepares the comparison evidence and an external qualification receipt using
[judge-qualification.example.json](../config/judge-qualification.example.json).
Chad selects the model based on that evidence. The receipt records upstream and
served model identities, model checksum, generator identity, the stronger-model
basis, settings and hashes of supporting files. It must name a distinct model,
not another alias/quantization of the generator. The ten-item qualification probe
and owner selection described in the approved plan are separate from calibration.

Prepare ignored `config/judge-assessed.local.json` with `model_identity`, `model_sha256`,
`qualification_path`, `stronger_model_basis`, the exact served model ID and the
existing credential source. Set temperature below the generator's and exactly
two attempts per item. Match the receipt's mode, temperature, token and timeout
settings. Preserve local-only serving; a hosted fallback needs separate scope.

Chad loads the selected model in Herd. Codex verifies the endpoint and identity.
There is no qualified stronger model selected at this checkpoint.

## 9. Judge and compare

Once Steps 7–8 are complete:

```bash
uv run --locked python -m aia_mp1 judge --assessment-id baseline-review-001 --judge-run-id baseline-judge-v1 --config config/judge-assessed.local.json
uv run --locked python -m aia_mp1 judge-status --assessment-id baseline-review-001 --judge-run-id baseline-judge-v1
uv run --locked python -m aia_mp1 calibrate --assessment-id baseline-review-001 --judge-run-id baseline-judge-v1 --report-id baseline-agreement-v1
```

The judge must resolve all 50 items. A reported model mismatch is retained as a
failed attempt. The comparison uses your frozen 20-item independent reference.
`status: ready` requires complete coverage and at least 16/20 matches in each of
the six dimensions, plus source/model eligibility. Otherwise read the exact
`readiness_reasons`; pending is a valid measured outcome.

Codex investigates disagreements and records a hypothesis before revising only
the judge prompt. Each revision gets a fresh run/report ID against the same frozen
items and labels. The initial assessed budget is three judge runs, two attempts
per item each. An interrupted run uses its original ID with `--resume`; completed
runs and reports cannot be overwritten. Unknown requests remain disclosed.

## 10. Amendments and handoff

If you correct a label after seeing judge output, use the explicit amendment
procedure in [RUNBOOK Appendix A](RUNBOOK.md#appendix-a--correct-a-saved-human-review),
with this assessment ID and your actual six decisions. Add `--review-stage
post_review --consulted-report-id baseline-agreement-v1`. The CLI preserves the
original record; it never supplies human scores for you.

A new report retains independent scores in `summary` and displays current amended
scores separately in `adjudication_summary`. Any amendment after freeze leaves
readiness pending for inspection. Correcting a genuinely wrong reference requires
fresh independent evidence; accepting judge notes does not prove calibration.

Report the collection/cohort/assessment IDs, number of completed reviews, judge
coverage and per-dimension counts. Codex retains the successful calibrated judge
identity before planning generator correction. Charts, the corrected cohort and
demo are subsequent work. No final assignment pass is implied by software checks.

## Where evidence lives and how to get help

Under workspace `artifacts/evidence/P1-03/`: `collections/<id>/` holds the budget
and frozen inputs; each `<collection-id>-bNN/` holds raw generation/gate evidence;
`cohorts/<id>/` holds the immutable membership; `assessments/<id>/` holds items,
rubric, labels, human reference, judge runs and comparison reports. Keep all of
them together. The CLI refuses missing or changed lineage.

For assistance, provide the shell, exact command, error and relevant IDs, without
credentials. A collection/report ID collision means choose a genuinely new
experiment ID or inspect the existing output; it does not mean delete the old run.
While a collection/judge writer is active, a status command can refuse its lock;
wait for the active command to finish. Do not bypass the lock.
