# SDD-P1-03 — Synthetic Data and Evaluation

| Document control | Value |
| --- | --- |
| Revision | 0.10, November 13, 2026 |
| Status | Approved sources, 50-item baseline cohort and 20-item human reference frozen; judge development comparisons ongoing; qualified judge and assessed calibration pending |
| Project | P1-03 / Mini Project 1, engineering code Q&A |
| Implementation home | `aia-mp1-synthetic-data` |
| Owner / human reviewer | Chad Josewski |
| Execution checklist | [aia-plan issue #4](https://github.com/cjosewski/aia-plan/issues/4) |
| Purpose | Full-project software design and requirement-to-evidence traceability, requested by Chad November 9 |

This SDD describes all six assignment stages, including work beyond the current
implementation plan. On November 9 Chad stated, "The assignment has been accepted.
The plan is approved. Go." Assignment acceptance is recorded as owner-reported;
implementation measurements and missing evidence remain independently identified.
The [requirements record](requirements.md) owns dated source reconciliation and
course criteria; this document owns the proposed implementation design. The
[README](../README.md) owns executable instructions. The
[next-slice plan](implementation-plan.md) sequences a
subset of this design and is approved. Requirements changes must be reconciled
with their source before this design or that plan is updated.

## 1. Problem, scope and sources

Produce engineering-code question/answer data through a repeatable process that
shows whether it is structurally valid, whether people and a model judge agree
about its quality, and whether a documented generator correction improves it.
Filtering, retrying or changing the judge must not conceal failures or manufacture
an improvement. The deliverable is a measured pipeline with inspectable evidence.

The five categories are `gis_scripting`, `aec_automation`, `structural_analysis`,
`cad_apis` and nonmedical `simulation`. All remain required. The original course
topic is home DIY repair; the engineering mapping preserves the seven-field schema,
six dimensions, libraries, stages and thresholds recorded in the sources.

| Source | Authority and verification boundary |
| --- | --- |
| [Requirements record](requirements.md) | November 9 portal reconciliation of schema, rubric and success criteria; lower visualization/example-log sections were not independently reread |
| [Issue #4](https://github.com/cjosewski/aia-plan/issues/4) | Live execution checklist, re-theme, stronger judge selection and deliverables; read November 9 for this SDD |
| [Rubric](../config/rubric.json) | Machine-readable anchors and thresholds, `engineering-v1`; adaptation acceptance remains pending |
| [Source manifest](../config/sources.json) / [assessed source decision](REFERENCE-PACK-REVIEW.md) | Smoke manifest stays separate; external engineering-v1 pack approved November 10 for local noncommercial assessed coursework |
| [Program source record](https://github.com/cjosewski/aia-plan/blob/main/docs/research/track-program-requirements.md) | Dated generic Evidence Pack requirements; not a newly verified assignment template |
| [P1-03 checkpoint](https://github.com/cjosewski/aia-plan/blob/main/docs/progress/P1-03.md) | Authorization, observations and retained evidence; not a second live checklist |

No separate instructor SDD template is present in these records. This document
fulfills Chad's request for a project SDD and maps the recorded assignment
requirements; a prescribed template or subsequent instructor amendment takes
precedence when supplied.

### 1.1 Boundaries

This project builds a local, single-operator CLI pipeline. It does not execute
generated engineering code, approve engineering work, modify Herd, train a model,
implement the shared gateway or certify the capstone's numerical gates. Generated
answers are evaluation subjects, not instructions for this software to execute.

The program's 26-hour reference is neither an implementation estimate for this SDD
nor actual effort. Dates and hours remain in
[project.json](https://github.com/cjosewski/aia-plan/blob/main/project.json). This mini-project design adds no hours
to the existing SDD-00–16 component ledgers or the four unbooked addenda.

## 2. Requirements and acceptance traceability

All rows are required for the complete project unless explicitly identified as a
local design control. A proposed test or artifact below is not passing evidence.

| ID | Requirement | Design | Acceptance evidence |
| --- | --- | --- | --- |
| MP1-R01 | Generate seven-field items through Python, Instructor and Pydantic; retain category, variant, model and raw attempts | §3–4 | Schema/transport tests; runtime generation ledgers |
| MP1-R02 | Independently gate structure, duplicates, cheap quality checks and category distribution; report rejection and bounded batch regeneration | §5.1–5.2 | Gate tests, reports, cohort manifest and regeneration lineage |
| MP1-R03 | Separate baseline/corrected datasets, each at least 50 retained items; initial schema validity at least 95%; all five categories | §5.2, §6 | Dataset manifests, exact counts and initial-attempt denominators |
| MP1-R04 | Resumable authentic human labels on at least 20 baseline and 20 corrected items, D1–D6 and trace IDs | §4.3, §5.3 | Label records, reviewer/timestamp/rubric identity and coverage |
| MP1-R05 | Independent structured judge prompt, all six dimensions for every assessed item, lower temperature than generator and recorded model identity | §4.4, §5.4 | Judge request ledger, outputs and model-selection record |
| MP1-R06 | Phase A tunes the judge on fixed items until every dimension has at least 80% human/judge agreement | §5.5, §6 | Versioned prompts, disagreement reports and calibration receipt |
| MP1-R07 | Phase B corrects the worst category/variant × dimension; freeze the calibrated judge for baseline/corrected evaluation | §5.6 | Frozen comparison specification, corrected prompt and iteration entries |
| MP1-R08 | Genuine baseline overall failure at least 15%; corrected D1–D6 and overall rates meet the rubric | §6 | Complete per-item judgments and exact aggregate counts |
| MP1-R09 | Measure relative failure reduction; disclose the conflicting exact-80% boundary | §6, §9 | Before/after report with formula, operands and explicit boundary verdict |
| MP1-R10 | Category/variant analysis and all five prescribed charts using Matplotlib/Seaborn | §6.2 | Report, chart files and plotted-data tables with source hashes |
| MP1-R11 | Malformed output produces bounded retries and recorded failure, not uncontrolled termination or silent success | §7 | Failure, exhaustion and interruption tests; raw failure records |
| MP1-R12 | Preserve stage 1–4 traces, versioned generator/judge prompts and iteration log | §4, §7 | Trace joins and prompt hashes; log with date/change/hypothesis/result/decision/next step |
| MP1-R13 | Deliver README, prerequisites/dependencies, reproducible evaluation, code identity/history, 90–180 s demo and coaching review | §8 | Reviewed Evidence Pack and explicit instructor acceptance record |
| MP1-R14 | Use permission-cleared material; preserve benchmark/adaptation decisions and exclude prohibited corpora | §7.2, §9 | Provenance manifest and instructor disposition where needed |
| MP1-C01 | Local audit control: immutable completed runs, strict lineage, no fabricated human labels or model measurements | §4, §7 | Tampering/collision tests and evidence hash readback |

### 2.1 Quality rubric

An item passes overall only when **all six** dimensions pass. Schema validity and
heuristics do not supply these judgments. [rubric.json](../config/rubric.json)
contains the full pass/fail anchors; its version and hash accompany every review.

| Dimension | Meaning | Corrected pass-rate minimum |
| --- | --- | ---: |
| D1 | Answer completeness | 85% |
| D2 | Task-specific hazard and concrete precaution | 90% |
| D3 | API/library realism and availability in the stated installation/version | 95% |
| D4 | Appropriate licensed-engineer review or sign-off boundary | 95% |
| D5 | Clear context that addresses `equipment_problem` | 90% |
| D6 | Useful task-specific advice beyond repeated steps | 85% |
| Overall | All six pass for the same item | 80% |

D3/D4 engineering interpretations are disclosed adaptations. Early-start
permission does not establish instructor approval of those interpretations.

## 3. Architecture and runtime

```mermaid
flowchart TD
    S[Versioned prompts, rubric and permission records] --> G[1 Generate]
    H[Configured local Herd endpoint] --> G
    G --> R[Immutable run artifacts and raw attempts]
    R --> Q[2 Structural and heuristic gate]
    Q --> C[Frozen cohort and selection]
    C --> L[3 Human label CLI]
    C --> J[4 Independent judge]
    H --> J
    L --> A[5 Agreement and analysis]
    J --> A
    A --> I[6 Iteration decision]
    I --> JA[Phase A: new judge version on fixed items]
    JA --> J
    I --> GB[Phase B: new generator version and new run]
    GB --> G
    A --> E[Charts and Evidence Pack]
```

The model-call boundary is shared infrastructure; generation and judging use
different prompts, output types and artifact identities. The judge must not read
human labels, generator reasoning, or previous judge decisions as hints. Human
labeling displays the item and rubric without suggested model scores.

| Component | Responsibility | Current state |
| --- | --- | --- |
| [schemas.py](../src/aia_mp1/schemas.py) | Canonical payload and generated-item envelope | Implemented |
| [config.py](../src/aia_mp1/config.py) | Local endpoint, credential source, source permission and generation settings | Implemented for smoke and explicitly assessed source packs |
| [model_client.py](../src/aia_mp1/model_client.py) | Bounded structured model call, raw response capture and redaction | Implemented for generation |
| [generate.py](../src/aia_mp1/generate.py), [tracing.py](../src/aia_mp1/tracing.py) | Attempts, checkpoints, identity and resume validation | Implemented for smoke and explicitly assessed source packs |
| [gate.py](../src/aia_mp1/gate.py), [cli.py](../src/aia_mp1/cli.py) | Saved-data gate and CLI | Implemented for kickoff checks |
| [assessment.py](../src/aia_mp1/assessment.py), [evaluation_schemas.py](../src/aia_mp1/evaluation_schemas.py), [labels.py](../src/aia_mp1/labels.py) | Single-run assessment snapshots, review contracts and human CLI | Implemented for legacy single-run and multi-batch cohort inputs |
| [judge.py](../src/aia_mp1/judge.py), [calibration.py](../src/aia_mp1/calibration.py) | Audited judge execution and agreement reports | Implemented; five-item diagnostic measured; assessed evidence pending |
| [collection.py](../src/aia_mp1/collection.py), [cohort.py](../src/aia_mp1/cohort.py), [sources.py](../src/aia_mp1/sources.py) | Permission-checked contexts, bounded collection and immutable cohorts | Implemented |
| [human_reference.py](../src/aia_mp1/human_reference.py), [qualification.py](../src/aia_mp1/qualification.py) | Blind-label freeze and attributed judge selection evidence | Implemented |
| `analysis.py`, `iteration.py` | Full comparison/charts and Phase B controls | Subsequent slice |
| [evidence_judge.py](../src/aia_mp1/evidence_judge.py) | Experimental citation validation and projection to the existing judge result | Development-only v5; offline verified, live screen produced no accepted judgments |
| [compact_evidence.py](../src/aia_mp1/compact_evidence.py) | Shared citations and short references using the same canonical projection | Development-only v6; five-case feasibility check stopped on output-format failures |
| [passage_evidence.py](../src/aia_mp1/passage_evidence.py) | Application-supplied passage IDs and exact source-text resolution | Development-only v7; measured status owned by the qualification checkpoint |

Run Python, dependency management and tests in WSL2 Ubuntu. The existing locked
environment uses Python 3.12; [pyproject.toml](../pyproject.toml) and
[uv.lock](../uv.lock) own dependency declarations and resolution. Matplotlib and
Seaborn are declared as the analysis extra and must be installed for chart work.
Current model configuration accepts an explicit local endpoint ending in `/v1`.
Credential contents do not enter prompts, manifests or logs.

The workload is 50 or more retained items per assessed cohort, not an online
service. Use sequential model calls and JSONL plus JSON manifests; no database,
distributed queue or additional server is needed. Current generation accepts
5–500 requested slots in multiples of five, up to five attempts per slot, timeout
up to 300 seconds and token ceiling up to 8192. These are implemented input bounds,
not latency targets. Record elapsed time and request/token use when available;
unavailable usage stays null. Do not promise throughput without measurements.

## 4. Data and interface contracts

### 4.1 Generated item — implemented

| Payload key | Type / constraint |
| --- | --- |
| `question`, `answer`, `equipment_problem`, `safety_info` | Nonblank strings |
| `tools_required`, `tips` | Lists with at least one nonblank string |
| `steps` | List with at least three nonblank strings |

Reject extra fields. Emit `equipment_problem`; legacy input `problem` is normalized
explicitly and conflicting dual values fail. Raw completion text remains preserved.

The separate `GeneratedItem` envelope contains `schema_version`, `run_id`,
`trace_id`, `item_id`, `attempt_id`, optional `parent_attempt_id`, `category`,
`prompt_variant`, `prompt_hash`, `model`, `source_refs` and `item`. This separation
keeps the course payload at exactly seven fields. Request/attempt ledgers hold
timestamps, raw responses and errors; the manifest records configuration, source
snapshot, code hashes and dependency versions.

### 4.2 Cohort and assessment — implemented

The `assessment` command accepts either a legacy single run or a frozen cohort.
Version 2 cohort assessments bind the cohort hash, reference pack, pinned generator
identity/checksum, 50-item population, seeded 20-item selection, rubric and code.
Legacy diagnostic manifests remain readable without rewriting evidence.

A collection checkpoint freezes sources, grounded prompt, generator settings,
implementation and gate rule identity before calls. It allows five 50-slot batches
and two attempts per slot. Stable batch/slot ordering fills ten items per category;
all rejected, duplicate and surplus items remain accounted for. Each batch and the
aggregate must meet 95% initial schema validity; unknown requests prevent freezing.

The cohort manifest wraps its collection identity and frozen summary. These bind
the baseline/corrected purpose, ordered member records (run/item/trace/payload),
source batch file hashes, category counts, stable selection decisions, source pack,
generator settings, gate rules, creation time and code identity. The subsequent
assessment binds the rubric and human selection. A member cannot come from
unvalidated/altered evidence. Failed batch quotas remain failed even when the
aggregate cohort qualifies; smoke inputs cannot be promoted.

The human-review selection records a deterministic seed, algorithm/version and
selected IDs before labeling or judging. The implemented 20-item sample is stratified
four per category. Additional samples use a recorded allocation. This is a local
sampling policy, not an inferred course mandate. Diagnostic selections can include
gate-rejected items, but cannot enter assessed cohort metrics by accident.

### 4.3 Human label — implemented

Each append-only record contains `label_id`, `assessment_id`, `item_id`, `trace_id`,
`payload_sha256`, `rubric_version`, `rubric_sha256`, `reviewer`, UTC `timestamp`,
D1–D6 decisions, notes and optional `supersedes_label_id`. Completed decisions are
strict integers 0/1; booleans, strings and extra dimensions are invalid. A skipped
or unfinished review is unresolved and is not a completed label.

Amendments identify the record they supersede; histories are never overwritten.
An unknown target, branching amendment or mismatched item/rubric is an error.
Reports freeze the effective label IDs and ledger hash, so later amendments require
new reports. Reviewer identity is attribution, not a claim of identity verification.

The implemented ledger wraps each label in a SHA-256 chain and maintains a separate
atomic `labels-checkpoint.json` with the assessment identity, ledger hash and record
count. A missing ledger, shortened prefix or append not committed to the checkpoint
fails for inspection. It is not silently repaired or treated as an empty review set.

For assessed cohorts, `human-reference.json` freezes complete explicitly blind
reviews before any judge run. It pins the original ledger prefix, effective IDs,
reviewer declaration, rubric and source pack. New optional review-stage/consulted-
report fields leave old label serialization unchanged. Subsequent amendments appear
in a separate adjudication summary and leave readiness pending; they never replace
the independent comparison. The reviewer's declaration is recorded, not inferred
from timestamps.

### 4.4 Judge result — implemented

The model returns exactly D1–D6, each with a binary decision and short justification.
Application metadata wraps it with `judge_run_id`, assessment/item/trace identity,
payload/rubric hashes, prompt version/hash, requested and reported model IDs,
settings, attempt identity and timestamp. The application supplies identity fields;
the model cannot choose which item its result belongs to.

Every attempt has a request-start record and a completion/error record. Invalid
judgments preserve raw output and consume an attempt. Exhaustion produces
`unresolved`, never six default passes. Each judge revision has a new immutable
judge-run ID even when it reuses the same assessment.

The November 13 [v5 evidence experiment](JUDGE-EVIDENCE-PROTOCOL.md) adds a separate
development response contract. Each dimension includes exact requirement/candidate
citations, optional counterevidence and a declared search for any claimed absence.
Only structurally valid, verbatim citations from allowed locations can be projected
to the existing Judgment. Raw evidence remains in the attempt record. Invalid
citations consume attempts; no output is repaired or converted to default scores.
These checks establish traceability, not semantic correctness. The production
judge command and assessed defaults continue to use their existing contract.

The separate [v6 compact contract](JUDGE-COMPACT-PROTOCOL.md) stores quotes once
and uses zero-based references per dimension. Short aliases map deterministically
to the same original fields. Bounds, exact substrings, namespace/anchor ownership
and index consistency are validated before projection. This remains an experiment:
the five-case feasibility check accepted no outputs, and no assessed interface or
default changed. Shared transport validation retains the v5 contract as well.

The [v7 passage contract](JUDGE-PASSAGE-PROTOCOL.md) adds a deterministic ID-to-path
index to each model input. IDs identify complete original candidate fields/list
entries, task/source text or the dimension's rubric anchors. The model emits
references and ratings; the application validates IDs and roles, projects the
canonical Judgment and resolves each ID to original text for audit. Original
text, augmented messages and catalogs are bound by the experiment manifest.
This removes generated-quote formatting constraints, not the need to assess
whether a cited passage actually supports its rating. Assessed defaults remain
unchanged.

#### 4.4.1 Source-grounded verification — offline implementation

The [V8 design](JUDGE-FACTCHECK-DESIGN.md) separates claim verification from rubric
scoring. A typed reference bundle distinguishes task requirements, authored
summaries, primary excerpts and rubric anchors. Stage A records supported,
contradicted or insufficient findings; Stage B must address each finding against
original evidence. Material uncertainty prevents canonical projection. Every
stage binds the item, sources, runtime and accepted predecessor by hash.

A single-stage V7 control receives the same augmented evidence as the two-stage
treatment. This distinguishes workflow effects from added source coverage.
The proposed five-case experiment has 15 nominal requests and a separate maximum
of 30 new starts after 92; it is not launched by this design checkpoint. Strict
schemas, offline accounting tests, source clearance and package freeze precede
execution. Draft prompts do not change assessed commands. Model findings are
untrusted assessments, not human labels or proof of technical truth; successful
known-case development would still require fresh blind confirmation and assessed
calibration. The linked design owns contracts, acceptance criteria and stop rules.

The subsequent offline slice implements typed source catalogs, strict verifier and
scorer contracts, original-text resolution, memo lineage and canonical projection.
Its external ledger freezes schemas/code, prompts, runtime and a separate human
reference mapping hash; it writes durable starts before dispatch, revalidates saved
completions on replay and blocks unknown outcomes or damaged checkpoints. Paired
reports retain all five selected cases, separate schema validity from acceptance,
and report unresolved cases without invented ratings. The separate module CLI
also supports native Mac preflight and explicit bounded execution. Its transport
checks the exact Instructor wire request against the pinned server's tokenizer,
runtime and weights before dispatch. The prepared bundle contains 18 primary
excerpts, PDF extraction lineage and explicit source coverage gaps. Tests use
synthetic fixtures only; 341 locked WSL tests pass. Compact presentation passes
native token preflight, but the bounded run stops after one accepted control and
two verifier failures. No scorer or paired result exists; cumulative development
starts are 95. The [design's development record](JUDGE-FACTCHECK-DESIGN.md#9-compact-presentation-and-bounded-comparison)
owns the diagnosis. The subsequent [V8.1 revision](JUDGE-V81-VERIFIER.md) passes
344 tests and accepts the first verifier response, but stops on two scorer format
failures; semantic evidence overclaims remain. Cumulative starts are now 99, with
zero paired cases. M4 remains incomplete and no stronger judge is qualified.

### 4.5 Storage and commands

Raw evidence is outside Git under workspace `artifacts/evidence/P1-03/`.

| Location | Contents |
| --- | --- |
| `<run-id>/` — existing | `manifest.json`, `events.jsonl`, `attempts.jsonl`, `data.jsonl`, `gate-report.json`, `gate-items.jsonl` |
| `assessments/<assessment-id>/` — implemented | Frozen run/cohort assessment, human-label ledger/checkpoint, blind human-reference snapshot, judge runs and calibration reports |
| `collections/<collection-id>/`, `cohorts/<cohort-id>/` — implemented | Frozen inputs/budget, ordered batch evidence and immutable cohort membership |
| `comparisons/<comparison-id>/` — proposed | Frozen comparison specification, separate baseline/corrected JSONL exports, metrics, plotted tables, `visualizations/` and evidence index |

The repository's `data/`, `labels/`, `traces/` and `visualizations/` are documented
scaffold locations, not destinations for committing raw results. An export package
can retain the assignment's directory names within the external evidence root.

Existing commands are `generate --config ... --count ... --run-id ... [--resume]`
and `gate --run-id ... [--artifact-root ...]`, described in the README. Implemented
independent assessment commands are `assessment`, `label`, `label-status`, `judge`,
`judge-status` and `calibrate`. Assessed commands add `source-check`, `collect`,
`collection-status`, `cohort`, `cohort-status` and `freeze-human-reference`; see
[the assessed runbook](ASSESSED-RUNBOOK.md). `analyze` and `compare` remain subsequent interfaces.
Each assessment command accepts explicit artifact identity and validates inputs before any
write. New-output commands refuse collisions; resume is only for unfinished work
with identical settings and identities. Reports include machine-readable JSON.

Preserve the current exit convention: 0 means the requested operation met its
stated scope, 1 means failed/incomplete, 2 means invalid configuration/evidence or
access error, and 130 means interrupted. A successful diagnostic command must
still state `assessment_eligible: false`; exit 0 alone is never course acceptance.

## 5. Pipeline behavior and state transitions

### 5.1 Generate and record

Snapshot the prompt, source permissions, settings and code identity, create a new
run directory, then write the request-start event before each call. Retain every
raw response or explicit transport failure. Validate payloads independently of
quality; retry within the configured budget and keep parent-attempt lineage.
Checkpoint durable evidence after progress. Interrupted runs can resume only with
matching original inputs and remaining attempts; a completed or gated run is frozen.

Smoke remains the default. Assessed generation explicitly selects baseline/corrected
purpose, a cleared reference pack and pinned model identity/checksum. Actual task/
reference context enters every request and its item envelope; changed inputs prevent
resume. A count of 50 alone never promotes smoke evidence.

### 5.2 Gate and assemble a cohort

Validate source-run hashes and attempt/data consistency before screening. Current
checks reject normalized duplicate questions, enforce exact equal category quotas,
screen D2 for minimum length and recognized hazard/precaution terms, and screen D6
for length, exact step repetition and known generic tips. D1/D3/D4/D5 remain pending.
No lexical screen is a semantic safety or factual-accuracy judgment.

The [D2 review](smoke-d2-review-2026-11-09.md) identifies vocabulary/inflection
limitations. Keep the existing smoke result unchanged. A revised gate gets a new
version and separate replay artifacts. Freeze the same gate/selection policy for
baseline and corrected cohorts; do not select a rule because it improves a score.

Implemented assessed collection assembles at least 50 retained items, initially ten
per category, from bounded generation batches. Preserve all rejected items and
cross-batch duplicate decisions. Regenerate deficits through new run IDs with the
same frozen generator variant; exhausted collection stops as incomplete. Set the
maximum batches/requests before collection. Choose retained members by a recorded
stable order, not human/judge scores. Report per-batch gate results separately from
aggregate cohort readiness; a failed sub-batch is never rewritten as a passed run.

Once quota and permission checks pass, freeze the selected cohort and its complete
source-attempt ledger. Reject subsequent population edits. Gate configuration
changes invalidate comparison eligibility unless both cohorts are rebuilt/replayed
under one documented policy and all affected assessment evidence is regenerated.

### 5.3 Human review

Create the selection before seeing judge scores. Display the full item and rubric;
allow the human to consult authorized versioned references for API realism. Record
reference/version notes where a decision depends on them. The human may label,
skip, pause or append an amendment. Resume verifies identities and shows unresolved
items without supplying assistant labels. Require at least 20 completed reviews
for each assessed baseline and corrected cohort.

### 5.4 Judge execution

Use a separate prompt and lower temperature than the generator where supported.
Explicitly record an unsupported sampling setting rather than silently claiming
it took effect. The live issue calls for a stronger judge: select and record that
model before assessed evaluation. A same-model diagnostic can verify plumbing
but does not satisfy this model-selection checklist item by itself.

The next slice uses the existing local endpoint boundary. If a stronger model is
unavailable locally, stop assessed judging pending model selection; do not silently
substitute the generator or a hosted service. Although the issue mentions a cloud
option for public data, current runtime policy has no hosted implementation or
approval. Such a change requires explicit scope, permission and cost decisions.

Treat item content as untrusted quoted data, never instructions to the judge. The
judge has no shell, engineering tool execution or authority to change records.
Prompt isolation reduces contamination; it is not proof that injections cannot
affect a model. Test adversarial synthetic items and surface disagreements.

### 5.5 Phase A — calibrate the judge

Judge a fixed calibration selection, join it to authentic human records and report
all disagreements. Revise only the judge prompt for this phase; each revision
gets an iteration-log entry and new judge-run ID. A rubric or input change creates
a new assessment rather than silently changing the calibration target.

A calibration-ready receipt requires an eligible cohort, at least 20 complete
human reviews and complete matching judgments, with agreement >=80% in every
dimension. The receipt freezes effective labels, selection, rubric, judge prompt,
model/settings and report hashes. Five-item smoke agreement is diagnostic only.
Agreement on the tuning sample is calibration evidence, not independent
generalization; identify any held-out evaluation separately.

Assessed judging requires the blind reference, a distinct pinned model and a
qualification receipt with owner basis, matching settings and hashed evidence.
The initial cap is three judge runs, two attempts/item each. A reported model
mismatch remains a failed attempt. The calibrated receipt binds the independent
human-reference hash; any post-freeze amendment leaves readiness pending.

### 5.6 Phase B — correct and compare

Apply the frozen calibrated judge to every baseline item before selecting the worst
category/variant × dimension. Report segment sample sizes; break tied failure rates
by larger sample size, then stable category/dimension order, recording the choice.
Make a specific generator-prompt correction, document its hypothesis and create
new generation runs. Keep sources, quotas, gate policy, model/settings and rubric
fixed unless a declared experimental change requires a new comparison design.

Collect and label the corrected cohort, judge every item with the same frozen
judge, then compare. If corrected human/judge agreement drops below 80% on any
dimension, the comparison is not accepted. Recalibration requires re-evaluating
both cohorts with one new frozen judge; do not compare differently scored cohorts.
Preserve unsuccessful iterations and genuine low-failure baselines.

## 6. Measurement and charts

Let `N` be the frozen retained population and `n_d` the number of resolved judgments
for dimension `d`. Report numerator, denominator, missing count and percentage for
every metric. Missing judgments are unresolved, never silently removed or passed.
Threshold verdicts require complete judgment coverage of the cohort.

| Metric | Definition and acceptance |
| --- | --- |
| Initial schema validity | Schema-valid first attempts / all planned initial slots in the declared collection; separately report unstarted/interrupted slots, retry recovery and retention. Incomplete collection cannot pass; completed collection requires >=95% |
| Dimension rate | Passes for `d` / `n_d`, with coverage `n_d/N`; apply §2.1 thresholds only at complete coverage |
| Overall pass | Items passing all six / `N`, when all items have resolved D1–D6; corrected >=80% |
| Overall failure | `1 - overall_pass` for complete populations; baseline >=15% |
| Human/judge agreement | Exact matching binary decisions / compared labels for each dimension; report selected, completed, compared and missing counts; each dimension >=80% |
| Relative failure reduction | `(F_baseline - F_corrected) / F_baseline`, using rates rather than raw counts when sizes differ |
| Category distribution | Counts and proportions before filtering, after deduplication and in retained cohort; exact equal quotas are the current local policy |

Zero baseline failure makes relative reduction undefined. A baseline below 15%
is retained and referred for instructor disposition; never inject failures to meet
the criterion. The issue uses reduction >=0.80 while portal prose says >80% and
its numeric wording allows equality. Until clarified, report the exact value,
both interpretations and a conservative pass only when reduction >0.80. Compare
unrounded ratios for all thresholds; rounding is presentation only.

Reports additionally show schema/retry/retention counts and D1–D6 confusion counts
against human labels (human is the reference). Majority-pass behavior can inflate
agreement, so retain disagreements and confusion tables alongside agreement.
This diagnostic does not replace or lower the assignment's threshold.

### 6.1 Comparison validity

The comparison manifest names both cohort hashes, the identical judge/rubric/gate
identities, source policy and intended generator change. Refuse acceptance when
these differ outside the declared experiment, samples are missing, or populations
were selected using outcomes. Never compare an unfiltered baseline against a
filtered corrected dataset. Show gate attrition separately from retained quality.

### 6.2 Five required visualizations

| Chart | Data and interpretation |
| --- | --- |
| Dimension pass rates before/after | D1–D6 for baseline/corrected with rubric threshold lines and counts |
| Segment heatmap | Category × dimension, separately faceted by variant/run; show sample sizes and mark unresolved cells |
| Agreement by dimension | Matching/compared counts for baseline/corrected and the 80% line |
| Category distribution | Before/after gate counts and target share for each cohort |
| Before/after paired bars | Grouped baseline/corrected overall pass/failure rates; also annotate relative failure reduction |

The paired bars compare cohort aggregates: freshly generated baseline/corrected
items are not paired observations. Do not imply item-level matched statistics.
Save charts plus the exact machine-readable plotted data, metric specification,
input hashes, tool versions and figure captions. Missing values are visually
distinct from zero. Charts are proposed outputs, not current evidence.

## 7. Reliability, security and operational decisions

### 7.1 Failure handling

| Failure | Required behavior |
| --- | --- |
| Invalid config, source permission or input schema | Fail before model calls/writes where possible; identify the violated field without exposing secrets |
| Timeout, transport failure or malformed model response | Retain start/error/raw evidence, consume bounded attempt budget, retry or mark unresolved |
| Process interruption | Preserve completed records; resume only with matching identity and remaining budget |
| Partial JSONL tail, stale lock or disk-write failure | Stop and preserve evidence for inspection; never auto-delete locks, truncate history or assume a response was recorded |
| Concurrent writer or existing output ID | Refuse exclusive acquisition/creation; do not interleave ledgers |
| Hash mismatch, duplicate identity or foreign label/judgment | Reject downstream evaluation; do not repair evidence in place |
| Missing labels/judgments or incomplete charts | Report incomplete with counts; prevent acceptance |
| Model unavailable | Retain the bounded blocker; no service changes or provider fallback |

Completed evidence is immutable by application policy, not cryptographically
tamper-proof storage. SHA-256 fingerprints detect mismatches against preserved
manifests; they do not prove authorship if both data and manifests are replaced.
Retain reviewed receipts independently and record code revision plus dirty/source
hash information until the repository has a reviewed commit.

### 7.2 Data protection and source permission

Only licensed open or standalone personal material may enter generation/reference
data. Public availability is insufficient. External records require URL,
version/revision, retrieval date, license/terms, allowed uses and publication
disposition. D3 ground truth needs actual versioned engineering references, not
the generator's confidence. The smoke source manifest authorizes smoke use only.
The external engineering-v1 pack now supplies versioned references under Chad's
November 10 local noncommercial coursework approval; it does not certify every
reference fact or authorize public/commercial corpus export. See the
[source decision](REFERENCE-PACK-REVIEW.md) for immutable draft/approved identities.

Exclude employer/client material, proprietary physiology and medical simulation.
Credential values, authorization headers and credential-file contents must not be
logged; redact parsed output as well as raw responses and diagnostics. Read-only
references do not authorize redistribution. Human identities and raw evaluations
remain in external local artifacts; review and sanitize any submission/publication
package separately. Raw artifacts stay retained until an explicit retention
decision; no cleanup process deletes acceptance evidence automatically.

### 7.3 Trade-offs and reuse boundaries

| Decision | Reason and trade-off | Revisit when |
| --- | --- | --- |
| JSONL and manifests | Inspectable, appendable evidence with low setup cost; explicit locks and validation needed | Multiple concurrent reviewers or much larger datasets |
| Sequential local model calls | Bounded load and simple attempt attribution; lower throughput | Measured collection time warrants concurrency with equivalent auditing |
| Separate gate and semantic judge | Cheap defects are screened early; heuristics can create selection bias | Revised gate validated on independent synthetic cases and frozen for both cohorts |
| Human calibration | Makes disagreement visible; human review is a real dependency | Larger evaluation warrants multiple reviewers/adjudication |
| Standalone mini-project modules | Satisfies the assignment without shared-platform dependency | Reviewed reuse in MP2, datasets or eval harness |

Trace envelopes can inform the future gateway audit design, but this SDD does not
declare gateway schema compatibility. Reuse must map fields and revalidate owning
contracts. MP1 judge metrics cannot override the shared eval harness's numerical,
unit or policy failures; see [SDD-09](https://github.com/cjosewski/aia-plan/blob/main/docs/sdd/SDD-09-eval-harness.md).

## 8. Verification, delivery and implementation handoff

### 8.1 Test strategy

| Verification | Cases | Requirements |
| --- | --- | --- |
| Payload/transport | Missing/extra fields, conflicting legacy key, empty lists, malformed JSON, one request per recorded attempt, redaction and retry exhaustion | R01, R11, C01 |
| Gate/cohort | Duplicate questions within/across batches, quota deficits, fixed selection, bounded regeneration, tampered/missing evidence and immutable replay | R02, R03, R14, C01 |
| Human labels | Interrupt/resume, skipped dimensions, strict binary input, amendments/conflicts, foreign IDs and changed rubric | R04, R12, C01 |
| Judge | Missing/extra dimensions, malformed output, timeout, unsupported settings, input injection fixtures and no label leakage | R05, R11, R12 |
| Calibration | 16/20 passes 80%; 15/20 fails; zero comparisons undefined; incomplete or five-item smoke selection cannot qualify | R06 |
| Comparison | Unrounded boundary checks, zero/low baseline failure, mismatched judge/gate/source policy, missing judgment and different cohort sizes | R07–R09 |
| Analysis/export | Counts match plotted tables; all five charts exist; unresolved cells and cohort grouping correctly described; artifact lineage complete | R10, R13 |

Test fixtures are clearly synthetic and never submitted as model results or human
labels. Run the existing locked WSL verification (`bash tools/verify.sh`) and focused
tests for new behavior. Use a live local run only against an already available
endpoint. Source hashes and tests establish implementation reproducibility;
stochastic model responses need not be byte-identical on rerun.

### 8.2 Delivery sequence and stop conditions

| Milestone | Outcome | Exit condition |
| --- | --- | --- |
| M1 — kickoff | Generation, structural gate and smoke evidence | Recorded November 9 result; not full acceptance |
| M2 — review workflow | Approved slice implemented: labels, judge, calibration reporting and diagnostic queue | 166 offline tests passed; live probe timed out before judge execution; authentic labels remain a human dependency |
| M3 — assessed baseline | Cleared sources/model/gate policy, >=50 retained items and >=20 human reviews | Complete provenance, real baseline measurements and calibration readiness |
| M4 — Phase A | Calibrated judge frozen | All six agreement thresholds; fixed-item iteration history |
| M5 — Phase B and analysis | Corrected cohort, >=20 human reviews, comparison and five charts | Every quantitative criterion and comparability check passes, or explicit instructor disposition retained |
| M6 — Evidence Pack | Reproducible repository, results, demo and review | Coach approval recorded explicitly |

These milestones allocate no new estimates or dates. M2 was approved November 9.
Later multi-file implementation, model-service changes and remote publication
remain subject to their existing authorization boundaries.

The final Evidence Pack index must identify: this SDD and source decisions; README
summary/quickstart/prerequisites; declared and locked dependencies; reviewed code
revision/history; separate baseline/corrected JSONL; gate/collection reports; human
and judge labels; stage 1–4 traces; calibrated/revised judge and corrected generator
prompts; iteration log; reproducible analysis and five charts; 90–180 second demo;
benchmark/adaptation decisions; and the coaching acceptance record. Link each to
its exact version/hash. Missing entries remain open, never inferred from issue
state or a successful CLI exit.

### 8.3 Observed implementation checkpoint

Continuation, November 9: Chad reported assignment acceptance and approved the
next-slice plan. The implementation passed 166 offline tests and Ruff checks.
Assessment `smoke-review-20261110T035628Z` contains all five original smoke items,
including both gate rejections, and zero human labels. Its live judge readiness
probe encountered `ConnectTimeout` from WSL before any model call. All six original
smoke artifacts retained identical byte hashes. Receipt directory: workspace
`artifacts/evidence/P1-03/labeling-judge-20261110T035628Z/`. No model quality or
calibration agreement is inferred from software tests or owner-reported acceptance.

Historical kickoff checkpoint:

November 9 records report 114 offline tests plus Ruff/CLI checks passed. The live
run `smoke-herd-20261109T222724Z` produced five schema-valid first attempts, no
retries and no duplicates; the gate retained three and rejected two on D2, so it
failed. The diagnostic explained those lexical mismatches. No authentic labels,
calibrated judge, assessed baseline/corrected comparison or course acceptance is
claimed. This SDD did not rerun those tests or models; the
[checkpoint](https://github.com/cjosewski/aia-plan/blob/main/docs/progress/P1-03.md) and
[D2 review](smoke-d2-review-2026-11-09.md) locate the evidence.

## 9. Open decisions and change control

| ID | Decision | Owner | Blocks |
| --- | --- | --- | --- |
| MP1-D01 | Engineering benchmark replacement/requirement and adaptation disposition | Instructor, via Chad | Unqualified assignment acceptance |
| MP1-D02 | Exact-80% improvement equality | Instructor | Acceptance of an equality-boundary result; conservative >80% remains the design rule |
| MP1-D03 | Engineering-v1 source pack approved November 10 for local noncommercial coursework; public/commercial export remains outside approval | Chad | Local assessed-source prerequisite resolved; downstream export and engineering runtime verification remain separate |
| MP1-D04 | Stronger judge model and supported settings; hosted change only if separately approved | Chad | Assessed judge/model checklist completion |
| MP1-D05 | Assessed gate version, bounded collection policy and source-purpose extension | Chad through implementation-plan review | M3 collection; current smoke semantics cannot be relabeled |
| MP1-D06 | Next-slice plan approved November 9; this SDD records its implementation and later design | Chad | Resolved for M2; later slices remain separately scoped |
| MP1-D07 | Explicit instructor SDD format, if one exists beyond the supplied records | Instructor, via Chad | Claim of conformity to an unprovided template |

Record decisions with date, source and affected requirement IDs. A revised source
requirement updates the requirements record and this design together under the
workspace approval rules. Bump rubric/prompt/schema versions when their meaning
changes; preserve prior artifacts. New design work must not change the reference
schedule, shared-core contracts or acceptance conclusions implicitly.

## 10. Revision history

| Revision | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-09 | Initial full-project SDD: requirement traceability, architecture, proposed assessment contracts, all six stages, measurement rules, failure handling, delivery evidence and open decisions |
| 0.2 | 2026-11-09 | Owner-reported assignment acceptance and plan approval; implemented assessment/label/judge/calibration contracts, 166-test checkpoint, immutable diagnostic queue and bounded endpoint blocker |

| 0.3 | 2026-11-10 | Approved assessed collection: grounded source packs, bounded multi-batch cohorts, blind-reference freeze, model qualification, CLI/runbook and preserved diagnostic evidence; live corpus/model prerequisites remain open |
| 0.4 | 2026-11-10 | Actual source-use approval, approved pack, upstream-matched generator and preflight; four-batch baseline qualified, 50-item cohort frozen and 20-item blind review queue created; see BASELINE-CHECKPOINT.md |
| 0.5 | 2026-11-13 | Development-only evidence contract and canonical projection; 234 offline tests, bounded Mac feasibility failure with zero accepted judgments; assessed contract/defaults and frozen references unchanged |
| 0.6 | 2026-11-13 | Compact shared-citation contract and 267 offline checks; bounded five-case Mac check stopped on quote-length violations with zero accepted judgments; no calibration or default change |
| 0.7 | 2026-11-13 | Supplied-passage contract, exact text resolution and 288 offline checks; separate bounded five-case experiment, with results in JUDGE-QUALIFICATION-RESULTS.md; no assessed default change |
| 0.8 | 2026-11-13 | Fixed V7 candidate comparison under JUDGE-MODEL-COMPARISON.md; byte-identical messages/validation with model-specific native templates; results and advancement decision owned by JUDGE-QUALIFICATION-RESULTS.md |
| 0.9 | 2026-11-13 | Proposed source-grounded verifier/scorer contracts, explicit unresolved handling and matched evidence control; draft prompts prepared, implementation and experiment unmeasured; no assessed default or frozen-reference changes |
| 0.10 | 2026-11-13 | Implement isolated V8 contracts, source integrity checks, durable stage ledger, frozen reporting-reference hash and paired offline reports; source package and live dispatch remain pending, with no new inference |
| 0.11 | 2026-11-13 | Add primary-excerpt extraction lineage and native Mac wire/token preflight; 340 tests pass. Frozen package halted on two scorer reserve overflows before inference; full return/audit retained, M4 remains in progress |
| 0.12 | 2026-11-13 | Compact model-input metadata without altering evidence; 341 tests and all native preflight checks pass. Bounded run stops after control acceptance and two verifier failures; 95 cumulative starts, no scorer/paired result, M4 remains in progress |
| 0.13 | 2026-11-13 | V8.1 verifier ID/coverage checklist and concise prompt; 344 tests. First verifier accepted but semantic overclaims remain; two scorer format failures stop the four-request run, bringing cumulative starts to 99 with no paired result |
