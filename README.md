# MP1 synthetic data and evaluation

Generate engineering-code Q&A items, preserve structural-gate evidence, collect authentic human labels, run an independent local judge and measure per-dimension agreement. These stages of P1-03 / Mini Project 1 run independently against saved artifacts.

Assessed collection, full charts and prompt-correction comparisons remain later work. Chad reported assignment acceptance and approved the labeling/judge plan on November 9, 2026; this is separate from measured pipeline results. See the [SDD](docs/SDD-P1-03.md), [requirements and source decisions](docs/requirements.md) and [iteration log](ITERATION_LOG.md).

## Prerequisites

- WSL2 Ubuntu for Python work.
- Python 3.12 selected by `.python-version`; the bootstrap installs it when needed.
- An already configured local OpenAI-compatible endpoint and served model for generation. Offline tests do not need a model.
- An API credential supplied through the supported environment or credential-file configuration, never committed to Git.

Chad approved this slice on November 9, 2026 and reported instructor permission to start after completing Courses 1–4. Courses 5–8 and their exercises remain pending; he expects to finish them within a week. The early start does not waive the remaining course work or approve a benchmark substitution.

## Quickstart

Open WSL2 Ubuntu at this repository's root and bootstrap the locked environment:

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

From the repository root in WSL, reuse the persistent environment and start the
prepared five-item diagnostic queue (including both original gate rejections):

```bash
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
uv run --locked python -m aia_mp1 label --assessment-id smoke-review-20261110T035628Z --reviewer "Chad Josewski"
```

The labeler displays each complete item and the frozen rubric. Enter `0` for fail,
`1` for pass, `s` to skip the item or `q` to quit. A skipped/partial item stays
unresolved; rerunning resumes at incomplete items. No judge suggestions appear.
The queue currently has **zero human labels**. Check progress with `label-status
--assessment-id smoke-review-20261110T035628Z`.

To create a new diagnostic queue from an existing completed, gated run:

```bash
uv run --locked python -m aia_mp1 assessment --run-id RUN_ID --assessment-id NEW_ID --label-count 5
```

Selections are deterministic and stratified by category. `--purpose baseline` or
`--purpose corrected` requires an assessed source-run purpose, permitted sources,
a passed gate, at least 50 retained items, at least 20 selected labels and >=95%
initial schema validity. Current generation is smoke-only, so these flags cannot
promote existing smoke runs. Multi-batch assessed collection is later work.

For an explicit human amendment, obtain the current label ID from `label-status`,
then use `label --assessment-id ID --reviewer NAME --item-id ITEM --decisions
1 0 1 1 1 0 --supersedes CURRENT_LABEL_ID --notes "Reason/reference"` with the
human's actual six decisions in D1–D6 order. These are syntax examples, not labels
to apply. Prior records remain intact. Damaged, missing or uncheckpointed label
ledgers fail for inspection instead of being silently reset.

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
WSL before a judge request, so `judge-v1-smoke` has **not** been created. The judge
command above is ready for a reachable endpoint. No service/settings were changed.
Receipt: workspace `artifacts/evidence/P1-03/labeling-judge-20261110T035628Z/`.

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
and >=80% agreement on every dimension. The receipt freezes effective label IDs,
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
