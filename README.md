# MP1 synthetic data and evaluation

Repository: [cjosewski/aia-mp1-synthetic-data](https://github.com/cjosewski/aia-mp1-synthetic-data) (private).
Execution tracking: [P1-03 / issue #4](https://github.com/cjosewski/aia-plan/issues/4).

**Current M4 checkpoint — November 18:** three exact-citation recovery trials
and one [source-ID trial](docs/M4-SOURCE-ID-TRIAL-RESULT.md) stopped at technical
fact audits before scoring. A separate
[candidate-applicability diagnostic](docs/M4-CANDIDATE-CHALLENGE-RESULT.md)
correctly challenged the source-ID trial's ArcPy prerequisite error, but
produced no assessed rating. V15 remains 95/120, with D1 and D6 below the
required 80% each. The current matched comparison uses a dedicated Mac server
and tunnel, with unrelated Herd services preserved.
Chad approved a [GPT-6.2 Astra frontier judge comparison](docs/M4-FRONTIER-JUDGE-COMPARISON.md)
with a $25 cap. The [matched result](docs/M4-FRONTIER-PAIRED-RESULT.md) has
50/50 valid judgments in each arm: Astra agrees with the frozen human ratings
on 102/120 criteria and reaches at least 80% in every dimension, while local
Qwen agrees on 91/120 and misses D1/D6. Astra's token-cost estimate is $1.99.
Both arms' explanations were audited; the dedicated Mac server and tunnel are
stopped. The newly supplied
[course customization guidance](docs/COURSE-BRIEF-RECONCILIATION-20261118.md)
keeps D3/D4 adaptation and hosted judge compliance unresolved; M4 is open.

**Earlier recovery preparation checkpoint — November 18:** the separate preparation packet
has **358 checks, 342 prepared questions and 16 holds**, with no empty source
bindings. All ten packets replay. Prepared questions are not verified facts;
frozen reviews and measured agreement are unchanged. The
[recovery design](docs/M4-RECOVERY-DESIGN.md) now includes exact request
serialization, bounded durable scheduling, saved-response validation, accepting
fact/score audits, durable rejection stops and transport-failure recording that
preserves unknown outcomes, plus an internal single-request transport adapter.
The **750-test locked WSL suite passes**. Frozen request construction connects to the
packet gate and accepted fact reviews. The packet-readiness gate replays all ten cases
and reports the actual 16 holds; top-level orchestration remains.
Returned completions with missing or different model names are retained and halt
the schedule before audit; this does not replace loaded-model verification.
Read-only preflight compares frozen server properties before and after exact-wire
tokenization and reports whether the request plus output allowance fits.
The native-process wrapper checks live parent/listener ownership and frozen
arguments on both sides of preflight, hashes every frozen model shard and the
executable, and rechecks file metadata afterward. Tunnel verification remains open.
The tunnel ownership contract now has a read-only Windows process reader; live
tunnel ownership and final dispatch still need an end-to-end receipt.
The internal runner connects these gates to one saved preflight and one bounded
development attempt. A new versioned packet exposes 16 insufficient claims for
audit; the original strict packet is preserved. No model scores have been
measured under the new policy.

The [Mac capacity check](docs/M4-TOKEN-SIZING.md) fits all ten prior draft verifier
requests in 65,536 tokens, including schema/template and an 8,192-token output
allowance; the maximum is 52,498. No inference calls were made. The temporary
server and tunnel are stopped. Final source resolution, prompt/settings freeze,
model identity, scorer-input preflight and dispatch integration remain. The
proposed twenty-start development trial is not allocated; no readiness is claimed.
The [owner instruction sheet](docs/CHAD-ACTIONS-P1-03.md) records the pending
scoped Windows Python exception for the prepared ArcGIS Pro 3.7 probe.

**Final V15 baseline complete; M4 still fails.** All fifty judgments arrived on
their first attempt. Agreement is **95/120 (79.2%)**, with D1 **70%**, D2 85%,
D3 80%, D4 90%, D5 85% and D6 **65%**. D1 and D6 miss the required 80% each.
[Complete result and evidence](docs/V15-BASELINE-RESULTS.md) retain nine gains,
one regression, all 24 false approvals and one false rejection. All three
human-identified safety failures were missed. Your reviews remain frozen.

**The Mac is free.** The owned server and tunnel stopped, their ports are clear,
and Herd was untouched. Execution used local **18083** to Mac **8081**, preserving
the other session's workload on 18081. The complete archive is checksum-verified
on the NAS; all 244 frozen inputs, report replay and 990 previous seal entries
verify. The [third and final allocated assessed run](docs/V15-BASELINE-PLAN.md)
is consumed. A new judge/protocol plan is needed before further assessed calls;
no automatic rerun or repeat human review follows. The M5 packet is preserved.

**Score discrepancy:** the original V13 result stays **72.5% (87/120)**; V15 now
measures **79.2% on the same original human reference**, a gain of eight ratings
(6.67 percentage points). Its **96.7% exposed development** and **93.3% fresh
authored confirmation** scores used different examples and did not transfer.
[Discrepancy record](docs/AGREEMENT-DISCREPANCY-20261117.md).

**Current acceptance rule:** Chad [restored 80% in every dimension](docs/ACCEPTANCE-RESTORED-80.md)
on November 17. **M4 remains open:** V15 fails D1/D6; V13's earlier D1/D3/D6
failures remain preserved. Calibration and analysis CLI reports default to the original course
policy. The superseded 70%-overall receipt and all errors remain preserved.
A bounded [V15 development comparison](docs/JUDGE-V15-PLAN.md) and fresh confirmation are complete.
The existing corrected cohort and human review packet remain intact; no corrected
judging or quality-improvement claim can proceed until calibration succeeds.

**Reporting implementation:** the [analysis runbook](docs/ANALYSIS-RUNBOOK.md)
covers verified cohort reports, five charts with plotted-data tables, exact
comparison thresholds and local evidence export.
**499 WSL tests pass** with the locked analysis environment and optional PDF renderer,
including the acceptance amendment, review export/intake, PDF content preservation,
original report replay, incomplete-evidence rejection and runtime ownership guards.
The new baseline-only report has five PNGs, five SVGs and five source tables.
Its incomplete banner concerns failed calibration and the unfinished comparison;
baseline judgment coverage is complete. Corrected quality remains unmeasured.

**Previous development result:** the [approved V13/V14 comparison](docs/JUDGE-V14-RESULTS.md)
completed twenty valid first attempts. V14 matches 55/60 versus V13's 56/60, with
one improvement, two regressions and a new safety false approval. Both score 7/10
on D5. V14 did not advance; the final assessed allocation was unused at that checkpoint.
The Mac is free, and all original ratings and assessed evidence are unchanged.

**All actions needed from Chad:** [consolidated instruction sheet](docs/CHAD-ACTIONS-P1-03.md)
covers the completed reviews and selection, plus later corrected reviews, demo and coaching
handoff, with conditional instructor decisions kept separate.
The earlier instruction sheet is available as a [November 14 PDF](docs/CHAD-ACTIONS-P1-03.pdf);
the Markdown instructions contain the current completed selection and next steps.

**Fresh human review received:** Chad's revised ten-item answer sheet is frozen
with all original ratings, pass reasons and comments preserved. The authoritative
submission came from `\\192.168.0.55\aia\Handoff\P1-03\MY-ANSWERS.md`.
No further human action is needed for this confirmation review.
The [matched comparison transport](docs/CONFIRMATION-TRANSPORT.md) is implemented
offline, including a shared bounded ledger, native runtime checks and portable
packaging. The comparison is now complete and fully archived.

**Owner selection recorded:** [Qwen3.5 for assessed baseline calibration](docs/ASSESSED-BASELINE-MAC.md).
Qwen3.5 matches **56/60**, versus Qwen3's **46/60**, with ten improvements and
no regressions against the frozen human reference. Four candidate false approvals
and reasoning limitations remain recorded. Chad selected Qwen3.5 with frozen V13
and its settings. The [assessed run stopped](docs/ASSESSED-BASELINE-RESULTS.md) with
11/50 complete judgments after three token-limit failures in 14 recorded attempts.
The Mac is free. Calibration remains pending. The approved
[two-case thinking-budget probe](docs/REASONING-BUDGET-PROBE.md#measured-result)
completed both cases on their first attempt with the 4096 cap. One known human
case matched 6/6; semantic limitations remain. A
[new full baseline revision](docs/BASELINE-BUDGET-RESULTS.md) completed fifty valid
first attempts, retaining 33 false approvals and no false rejections across the
twenty human reviews. Calibration failed the original criterion; see the current
current acceptance rule above. The Mac is free. The
[V14 comparison](docs/JUDGE-V14-RESULTS.md) is complete and failed its advancement
conditions. No third assessed run or new human scoring has started.
The earlier development checkpoint had **212 starts**, including both
externally interrupted attempts; the later assessed runs have 14 and 50 starts,
and the separate thinking-budget probe has two.

**Previous development result:** [Qwen3.5 V4](docs/QWEN35-V4.md#measured-result) completed
ten valid first attempts at **57/60**, with at least 90% agreement in each dimension
and no safety/API false approvals. Three scoring errors remain explicitly recorded.
The audited screen supports fresh confirmation only; qualification and assessed
judging remain pending. Cumulative development starts are **190**. The owned Mac
server is stopped and complete returns are verified locally/NAS.

Previous Qwen result: [V3](docs/QWEN35-V3.md#measured-result) matched 56/60 in
eleven starts, preserving a token-limit failure and its successful retry.

Previous Qwen result: [V2](docs/QWEN35-V2.md#measured-result) matched 54/60 with
zero false approvals but D5 at 6/10, failing its advancement threshold.

Previous Qwen result: [V1](docs/QWEN35-CANDIDATE.md#measured-result) matched 56/60
with one safety false approval and three false rejections. It remains unqualified.

Previous result: [V12](docs/JUDGE-V12-PRESENTATION.md) preserved all input values
while changing formatting, but matched 53/60 and retained safety/API defects.

Previous result: [V11](docs/JUDGE-V11-ISOLATED.md) completed twenty valid
stage calls and matched 55/60 known ratings, with D5 at 6/10 and one safety false
approval. It remains unqualified. All returns are archived locally/NAS; cumulative
starts were 139 at that checkpoint.

Earlier canonical results: [V9R1](docs/JUDGE-V9-CANONICAL.md) matched 56/60 known
ratings; [V10](docs/JUDGE-V10-CANONICAL.md) matched 53/60 and introduced six false
approvals. Both completed ten first attempts. Semantic failures prevent
qualification even though V10 reaches 80% in each dimension. Cumulative starts
were 119 at that checkpoint. No fresh human review is needed yet.

Earlier development checkpoints follow for provenance:

**November 13 checkpoint:** the [GPT-OSS-120B V7 screen](docs/GPTOSS120B-COMPARISON.md)
completed at 23/30 agreement, versus GPT-OSS-20B's 27/30 and Llama's 23/30 on
identical five-case inputs. Every response was accepted on its first attempt,
but all three approve an API defect. None qualifies. Preparation passed 288 tests.
[Results and next step](docs/JUDGE-QUALIFICATION-RESULTS.md) record the evidence
audit. No assessed judge run has started.
**Human follow-up complete:** Chad's [judge-v3 post-result review](docs/JUDGE-V3-REVIEW-RUNBOOK.md)
reaffirms all five frozen ratings. The three false approvals and two false
rejections remain in the v3 record; no historical labels or metrics changed.
V4 remains at 52/60 over ten cases; v5/v6 produced no accepted judgments. On the
same five cases used for v7, v4 matched 26/30. The
[source-grounded judge design](docs/JUDGE-FACTCHECK-DESIGN.md) now specifies claim
verification, explicit unresolved outcomes and a matched single-stage control.
Offline contracts, lineage checks and paired reporting are implemented through a
separate [development interface](docs/JUDGE-FACTCHECK-DESIGN.md#7-implemented-offline-interface).
The source bundle and Mac transport are implemented; **344 tests pass**.
[V8.1 results](docs/JUDGE-V81-VERIFIER.md#measured-result) show an accepted verifier
on the first case, followed by two scorer format failures and the bounded stop.
Semantic audit also finds unsupported verifier claims accepted by both scorers.
Control covers 1/5 cases, treatment 0/5; no paired improvement is established.
At that checkpoint the next proposal was to revise scorer citation roles and atomic
evidence verification. Its cumulative starts were **99**; later canonical
experiments and current next steps are recorded above.
The [Mac runbook](docs/GPTOSS-MAC-RUNBOOK.md) is retained as the completed procedure.
Do not repeat completed runs/reviews or start assessed judging yet. Older dated
sections below describe their original implementation checkpoints.

The five-item diagnostic review and judge comparison are complete as of November
10. Independent agreement was 60% for D1–D4 and 100% for D5–D6; Chad's later
acceptance of the eight disagreements is preserved separately as post-review
agreement. The **[assessed collection plan](docs/assessed-collection-plan.md)** is approved
and its software is implemented. Follow the **[assessed runbook](docs/ASSESSED-RUNBOOK.md)**
for the new commands. [Source/model readiness](docs/SOURCE-READINESS.md) remains
explicit; live assessed collection has not started.

## Historical diagnostic: review the five saved answers

Use the **[step-by-step human-review runbook](docs/RUNBOOK.md)**. It explains what
you are evaluating, how to enter Ubuntu from Windows, how to apply each of the six
criteria, when labels are saved, and how to pause, resume or correct a mistake.

For this exercise you read and score the saved model-generated answers. You do not
need Herd running, API credentials, or a new clone. Finish by verifying five saved
reviews, or reporting the items you could not judge. Failed answers are valid review
results; you are not trying to make every answer pass.

The rest of this README is the developer/setup and command reference. Start with
the runbook if your task is the prepared human review.

Generate engineering-code Q&A items, preserve structural-gate evidence, collect authentic human labels, run an independent local judge and measure per-dimension agreement. These stages of P1-03 / Mini Project 1 run independently against saved artifacts.

Assessed collection and reporting tools are implemented. The baseline cohort and
human reference are frozen; qualified judging, corrected collection and measured
comparison remain pending. Chad reported assignment acceptance and approved the
labeling/judge plan on November 9, 2026; this is separate from measured pipeline
results. See the [SDD](docs/SDD-P1-03.md), [requirements](docs/requirements.md) and
[iteration log](ITERATION_LOG.md).

## Prerequisites

- WSL2 Ubuntu for Python work.
- Python 3.12 selected by `.python-version`; the bootstrap installs it when needed.
- For generation/judging: an already configured local OpenAI-compatible endpoint and served model. Human labeling and offline tests do not need a model.
- For generation/judging: an API credential supplied through the supported environment or credential-file configuration, never committed to Git.

Chad approved this slice on November 9, 2026 and reported instructor permission to start after completing Courses 1–4. Courses 5–8 and their exercises remain pending; he expects to finish them within a week. The early start does not waive the remaining course work or approve a benchmark substitution.

## Developer setup and new generation runs

Clone the repository in WSL2 Ubuntu, or use the existing workspace checkout:

```bash
git clone https://github.com/cjosewski/aia-mp1-synthetic-data.git
cd aia-mp1-synthetic-data
```

From the repository root, bootstrap the locked environment:

```bash
bash tools/bootstrap.sh
bash tools/verify.sh
```

The bootstrap installs `uv` if necessary, selects Python 3.12 and installs dependencies from `uv.lock`. Verification runs lint, offline tests and CLI help. Tools, the interpreter, package cache and virtual environment default to `/tmp/aia-mp1-tools` on Linux storage. Set `AIA_MP1_TOOLS` to another Linux directory before bootstrapping if you want a persistent location. If `/tmp` is cleared, rerun the bootstrap.

The November 9 connection setup also installed the locked tools persistently. To reuse them across WSL restarts, run `export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"` before sourcing `tools/environment.sh` or running the bootstrap/verification scripts.

Run from this repository's root in WSL2. Copy `config/local.example.json` to the ignored `config/local.json`, then replace `model` with the actual served model ID. All relative paths resolve against the working directory, not the configuration file's directory.

| Setting | Use |
| --- | --- |
| `base_url` | Explicit localhost/private-IP endpoint ending in `/v1`; the example uses port 8080 |
| `model` | Actual model served by that endpoint |
| `api_key_env` | Name of the environment variable holding the key; defaults to `AIA_MP1_API_KEY` |
| `api_key_file` | Alternative path to an existing key file; set `api_key_env` to `null` when using it |
| `mode` | `json` or `tools`, selected to match the endpoint's capabilities |
| `timeout_seconds` | Request timeout; default 60 seconds |
| `max_attempts` | Application attempt limit per item; default 3 |
| `artifact_root` | Output root, defaulting to `../artifacts/evidence/P1-03` |

Set exactly one credential source. The CLI does not load `.env` files automatically. Keep credentials out of `local.json`, prompts and command arguments; the config records only the variable name or file path. The client does not discover or start a model, change Herd settings or fall back to a hosted service.

After the configured endpoint and model are available, generate five items and run the independent gate:

```bash
source tools/environment.sh
uv run --locked python -m aia_mp1 generate --config config/local.json --count 5 --run-id smoke-001
uv run --locked python -m aia_mp1 gate --run-id smoke-001
```

Use a new run ID for each new experiment. If you changed `artifact_root` in the generation config, pass that same path to `gate` with `--artifact-root`; the gate does not read `local.json`. Counts must be multiples of five between 5 and 500.

An interrupted or incomplete run can be resumed by adding `--resume` to the original generation command. Keep its settings, prompt, source manifest, code and count unchanged. Resume verifies checkpoint hashes and matches data against successful attempts before preserving completed items. It does not grant exhausted slots extra attempts. Completed runs and runs with gate evidence are frozen; choose a new ID for another experiment. A hard process termination may leave a lock or an uncheckpointed tail; preserve and inspect the evidence instead of automatically deleting the lock or editing records.

| Exit code | Meaning |
| --- | --- |
| `0` | Generation obtained the requested schema-valid items, or the implemented gate passed |
| `1` | Generation remained incomplete, or the gate failed |
| `2` | Invalid input, configuration, artifact or file-access error |
| `130` | Interrupted; inspect preserved evidence before resuming |

## Human labeling and judge calibration

For the prepared five-item review, follow the
[operator runbook](docs/RUNBOOK.md). It contains the exact Windows/Ubuntu commands,
the six review criteria, expected output, completion checks and amendment procedure.

The queue and source run are local workstation evidence, excluded from Git. A
fresh clone must generate/gate its own run or receive the complete retained
evidence before it can review that queue. Human labeling works offline.

To create a new diagnostic queue from an existing completed, gated run:

```bash
uv run --locked python -m aia_mp1 assessment --run-id RUN_ID --assessment-id NEW_ID --label-count 5
```

Selections are deterministic and stratified by category. Assessed baseline/corrected
queues require a qualified source run/cohort. Smoke evidence cannot be promoted
by changing its purpose flag. New assessed collection uses the separate source-pack
and cohort path in the assessed runbook. See the [requirements](docs/requirements.md).

The following commands are the later judge/comparison reference. They are not
prerequisites for completing your human review.

Use `config/judge.example.json` for judge settings. The ignored
`config/judge.local.json` was prepared from the existing local endpoint and
credential-file reference, with temperature 0.1; it contains no credential value.
It selects the same model for a **diagnostic** run only. Assessed use requires a
distinct stronger judge model plus `stronger_model_basis`, documenting the owner's
selection. The inherited generation source/prompt defaults not overridden in a
judge config are not used to generate data; the assessment's frozen rubric and
items are the judge's only evaluation inputs.

```bash
uv run --locked python -m aia_mp1 judge --assessment-id smoke-review-20261110T035628Z --judge-run-id judge-v1-smoke --config config/judge.local.json
uv run --locked python -m aia_mp1 judge-status --assessment-id smoke-review-20261110T035628Z --judge-run-id judge-v1-smoke
uv run --locked python -m aia_mp1 calibrate --assessment-id smoke-review-20261110T035628Z --judge-run-id judge-v1-smoke --report-id agreement-001
```

The November 9 local check (03:56:28 UTC November 10) timed out connecting from
WSL before any judge request. This historical blocker was resolved November 10:
`judge-v1-smoke` is now complete with five valid first attempts. Its ID and
`agreement-001` already exist and must not be reused. The commands above document
that completed diagnostic; use fresh IDs for new work.
Receipt: workspace `artifacts/evidence/P1-03/labeling-judge-20261110T035628Z/`.

November 10 assessed implementation: **185 offline tests passed**, plus Ruff and
new CLI help checks. The original smoke/diagnostic files remain unchanged. The
software now supports permission-checked source contexts, bounded collection,
immutable cohorts and a blind human-reference freeze before assessed judging.
Live prerequisites and limits are in [source readiness](docs/SOURCE-READINESS.md).

Each judge call has a durable start and raw completion/error. `--resume` uses only
the original settings, prompt, code and remaining attempt budget. A started request
with unknown outcome consumes its attempt and remains disclosed. Completed runs
and calibration reports cannot be overwritten. Use new IDs for prompt revisions
and reports after label amendments. No hosted fallback is supported.

Calibration writes exact agreement counts, missing coverage, confusion counts,
disagreements and category breakdowns. Exit 1 with `status: pending` is expected
for this diagnostic queue, even with perfect observed agreement. Readiness needs
complete population judgments, the full frozen human selection, at least 20
complete labels, at least 50 balanced retained items, a qualified distinct judge,
and >=80% agreement separately in every dimension under the restored original rule. The receipt freezes effective label IDs,
rubric, judge prompt/model/settings and input hashes. It measures calibration-set
agreement, not independent generalization or professional correctness.

Assessment data, frozen rubric, human ledger/checkpoint, judge request ledgers and
calibration reports are under `<artifact-root>/assessments/<assessment-id>/`.
All commands accept `--artifact-root`; use the same root as the source run.

Continuation verification: **166 offline tests passed**, plus Ruff lint/format and
CLI help checks. The retained `verification-summary.json` in the receipt directory
summarizes the observed WSL output. It is software verification, not a human or
model-quality result.

## What the gate means

The gate validates structure, identifies duplicate questions and reports category coverage. Its implemented content checks are deliberately narrow:

- D2 screening requires at least 40 characters of hazard/precaution text plus recognized engineering hazard and precaution terms.
- D6 screening requires tips of at least 20 characters and rejects exact normalized repetitions of steps or known generic phrases.
- D1, D3, D4 and D5 remain pending review. D2/D6 screening does not assign human or judge labels either.

These local heuristics can flag obvious defects; they do not establish API correctness, professional-review scope or all-six quality. Exact equal category quotas are required for this first slice. Five requested items means one accepted item per category; 50 means ten. All current runs remain smoke evidence, including a run with 50 items.

Generation preserves malformed responses and retry outcomes. Read initial-attempt validity separately from successful retries and retained-item validity; filtering a bad response does not erase it from the evidence. See [measurement rules](docs/requirements.md#measurement-rules).

## Sources and evidence

The initial [source manifest](config/sources.json) permits only the original local smoke prompt. It contains no ingested third-party documentation and supplies no independent factual ground truth. License and version external material before adding it to an assessed corpus.

Each run stores its evidence under `<artifact-root>/<run-id>/`:

| File | Meaning |
| --- | --- |
| `manifest.json` | Run configuration, provenance and outcome |
| `events.jsonl` | Request-start records, including calls that may have been interrupted |
| `attempts.jsonl` | Completed attempts, raw responses or explicit failures |
| `data.jsonl` | Schema-valid payloads with their provenance envelopes |
| `gate-report.json` | Independently computed gate summary |
| `gate-items.jsonl` | Per-item gate decisions |

Generated datasets, labels, traces and charts belong outside Git under the workspace's `artifacts/evidence/P1-03/`. Keep each run and its attempt history intact. Do not commit credentials, raw workstation traces or private course material.

The [rubric](config/rubric.json) records the six course dimensions and disclosed engineering mappings. The required output key is `equipment_problem`, preserving the live course schema even though the copied issue uses `problem`. The loader explicitly normalizes legacy `problem` input and rejects conflicting values when both spellings are supplied. Raw response evidence is preserved separately.

## Project coordination

November 9 validation: **114 offline tests passed**, including malformed responses, request counts, retry limits, interruption/resume, changed evidence, incomplete gate reports, credential redaction and disabled environment proxies. Ruff lint/format and CLI help checks passed in WSL2 with Python 3.12.16. The probe of `127.0.0.1:8080` found both `/health` and `/v1/models` refused connections. No live model items or quality measurements were produced. Evidence is retained at workspace `artifacts/evidence/P1-03/kickoff-20261109/`.

[Issue #4](https://github.com/cjosewski/aia-plan/issues/4) owns the live execution checklist. This local implementation does not update project dates, course checkboxes or instructor acceptance. Read [AGENTS.md](AGENTS.md) for contribution and verification rules.

November 9, 17:03 EST follow-up: Herd is healthy on Windows (`/health` and authenticated `/v1/models` both HTTP 200), serving Qwen3-30B-A3B-Q4_K_M. WSL2 localhost still refuses connections, and its Windows host gateway times out. The pending five-item smoke run needs a WSL-accessible local endpoint; no generation or model-quality measurement occurred. Receipts: workspace `artifacts/evidence/P1-03/herd-ready-20261109/`.

November 9, 17:27 EST resolution: with the owner's restart approval, WSL switched from NAT to mirrored networking through `%UserProfile%\.wslconfig` (`[wsl2]`, `networkingMode=mirrored`). WSL now reaches Herd at `http://127.0.0.1:8080/v1`: health 200, anonymous models 401, authenticated models 200. Herd retained its loopback binding and existing key; no firewall rule was added. The ignored `config/local.json` records the working endpoint/model and key-file path, with a 120-second timeout and 4096-token limit; it contains no key value.

Live run `smoke-herd-20261109T222724Z` generated five schema-valid items in five first attempts, with no retries or duplicates. The independent gate retained three and rejected two on D2 heuristics, so the batch gate **failed**. Six-dimensional quality and course acceptance remain pending. Connection receipts are in workspace `artifacts/evidence/P1-03/connection-fix-20261109/`; immutable run artifacts are in `artifacts/evidence/P1-03/smoke-herd-20261109T222724Z/`. Review the D2 rejections before any subsequent generation experiment; do not weaken the gate to obtain a pass.
