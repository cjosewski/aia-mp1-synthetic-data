# P1-03 assessed collection and baseline calibration plan

Prepared November 10, 2026 against implementation commit `e408f91`.
Status: approved November 10, 2026. Chad stated “Approved. Go.” Software implementation
and verification are recorded in the SDD and assessed runbook; live collection
requires the source/model prerequisites and authentic reviews described below.

## Outcome and scope

Deliver a reproducible assessed-baseline workflow: permitted, versioned reference
material; bounded runtime generation; an immutable balanced cohort of 50 retained
answers; a blind 20-item human-review queue; and calibration using a qualified,
distinct judge. Finish software and setup work first, then collect real evidence
as the reference/model prerequisites and human reviews become available.

This implements SDD milestones M3–M4. It prepares the same collection machinery for
a later corrected cohort, but does not perform Phase B generator correction, the
five final comparison charts, the demo or coaching acceptance. All five categories,
six dimensions, seven payload fields and course thresholds remain unchanged.
Sources: [SDD §8.2](SDD-P1-03.md#82-delivery-sequence-and-stop-conditions),
[requirements](requirements.md#full-pipeline-and-evidence).

The existing implementation plan remains the historical approved M2 plan.
This document owns sequencing for the proposed M3–M4 slice; the SDD continues to
own component contracts. Raw data and decision receipts remain outside Git.

## Verified starting point

| Observation | Evidence or implementation reference |
| --- | --- |
| Five human reviews and five valid first-attempt judge responses are complete | Local assessment `smoke-review-20261110T035628Z`, judge `judge-v1-smoke`; receipt `diagnostic-judge-20261110T153913Z/verification.json` |
| Independent agreement was 3/5 for D1–D4 and 5/5 for D5–D6 | Immutable `calibration/agreement-001/report.json` under that assessment |
| Chad accepted all eight disagreements after reading judge notes; five explicit item amendments preserve the original ledger | Receipt `human-adjudication-20261110T154551Z/verification.json`; `agreement-002-post-review` records 100% post-review agreement, not independent calibration |
| Generation hard-codes `purpose: smoke`; source loading accepts only local-smoke permission | [generate.py](../src/aia_mp1/generate.py), `generate_run`, line 179; [config.py](../src/aia_mp1/config.py), `load_inputs`, lines 101–123 |
| Assessments currently accept one completed run; assessed input requires a passed batch gate | [assessment.py](../src/aia_mp1/assessment.py), `source_snapshot`, line 63, and `population_for`, line 129 |
| Batch gating fails if any planned quota is missing; accepted items still have individual decisions | [gate.py](../src/aia_mp1/gate.py), `evaluate_gate`, line 80 |
| Generator input currently contains the prompt/category/slot, but no reference excerpts | [generate.py](../src/aia_mp1/generate.py), `generate_run`; source metadata alone does not ground the answer |
| Calibration consumes latest effective labels; it has no separate blind-label snapshot or post-feedback eligibility check | [calibration.py](../src/aia_mp1/calibration.py), `calibration_report`, line 76; [labels.py](../src/aia_mp1/labels.py), `load_labels`, line 13 |
| SDD already proposes bounded multi-batch cohorts and a distinct stronger judge | [SDD §5.2](SDD-P1-03.md#52-gate-and-assemble-a-cohort), [§5.4](SDD-P1-03.md#54-judge-execution) |
| Source clearance and engineering benchmark disposition remain open | [sources.json](../config/sources.json); [SDD decisions MP1-D01/D03/D04/D05](SDD-P1-03.md#9-open-decisions-and-change-control); live [issue #4](https://github.com/cjosewski/aia-plan/issues/4), read November 10 |

All receipt paths above are relative to workspace `artifacts/evidence/P1-03/`,
except the calibration paths, which are below its assessment directory. The live
issue and older handoff still describe earlier progress; their historical text
does not override the new local evidence. No board state, dates or estimates are
changed by this plan.

## Approved implementation decisions

### Collection policy

Freeze the following defaults before any assessed model calls. They implement the
bounded collection contract in [SDD §5.2](SDD-P1-03.md#52-gate-and-assemble-a-cohort).

| Setting | Proposed value |
| --- | --- |
| Cohort target | Exactly 50 retained items: ten per category |
| Human selection | Exactly 20 initially: four per category, seeded before judge results |
| Batch size | 50 planned slots: ten per category; preserves existing round-robin generation |
| Maximum batches | Five per cohort, including the initial batch |
| Maximum attempts | Two per slot; at most 500 generation requests per cohort |
| Call timeout | 120 seconds initially; explicit timeout and token settings frozen in the collection manifest |
| Stop condition | Finish the current batch; stop when quotas are full, an integrity/prerequisite check fails, or the batch/request budget is exhausted |
| Selection order | Declared batch order, then slot order; earliest eligible unique items fill each quota |
| Gate | Freeze current D2/D6 heuristics and normalization as version 1; no vocabulary tuning in this slice |
| Initial schema validity | Valid first responses / planned slots; at least 95% in each batch and in the aggregate across all admitted batches |
| Baseline generator | Existing Qwen3-30B-A3B Q4_K_M, with a new versioned source-grounded prompt; exact model artifact/settings pinned before collection |

Run complete balanced batches for replenishment rather than introducing uneven
per-category generation in this slice. Record accepted surplus as `quota_excess`;
it is not a quality rejection. The budget is a ceiling, not a performance forecast.
Do not automatically increase it or restart a failed experiment under a new ID
to conceal its outcomes.

Terminal batches may contain exhausted slots or failed batch-level quotas. Validate
all attempt/data lineage and preserve their original failure status. They can
contribute individually accepted items to a new aggregate cohort, but pending
requests with unknown outcomes and nonterminal runs block freezing. Unresolved
slots count against first-attempt validity. Do not weaken the legacy single-run
assessment path to implement this separate cohort path.
An individual batch below 95% prevents this collection from qualifying even if
later batches raise the aggregate rate. Preserve it; do not drop it from membership
or the denominator. This retains the per-run requirement in the course checklist.

Cross-batch deduplication uses the existing normalization, in frozen batch/slot
order, across all schema-valid generated questions, including rejected questions.
The first occurrence reserves the normalized question, matching current gate
semantics. Persist duplicate-of IDs and reasons. Never select by human/judge score.
These rules extend, rather than rewrite, the preserved batch decisions in
[gate.py](../src/aia_mp1/gate.py) and [cli.py](../src/aia_mp1/cli.py), `gate_run`.

### Sources and benchmark

Build a small reference pack with at least ten distinct task briefs per category,
versioned API facts, installation assumptions and cited evidence. Treat this as a
minimum coverage target, not a verified source inventory. Candidate subject areas
are QGIS for GIS, Dynamo/IfcOpenShell for AEC, OpenSees for structural analysis,
FreeCAD for CAD, and an open nonmedical numerical-simulation reference for simulation.
These are candidates to screen against permissions and the agreed topic scope;
none is declared cleared merely by appearing here. The live issue also names
ArcPy/Revit references; preserve those requirements or document the disposition
of any proposed substitution before claiming source-scope completion.
Sources: [issue #4](https://github.com/cjosewski/aia-plan/issues/4),
[requirements: permissions](requirements.md#source-permissions-and-benchmark-decision).

For every included excerpt/brief record source URL, exact version/revision,
retrieval date, content hash, license/terms evidence, permitted generation and
export uses, attribution obligations and category coverage. Verify the terms for
the documentation itself, separately from the software license. Missing or
ambiguous permission keeps that source pending. Do not ingest employer/client,
proprietary physiology or medical-simulation material.

Store full reference content outside Git with hashes and provenance. Commit only
metadata and material whose publication permission is established. Bind the actual
excerpt IDs and hashes to each generation request and generated-item envelope;
the seven-field payload stays unchanged. Supply the same allowed factual context
to the human reviewer and judge, without human labels, judge scores or answer-key
scores in either model input. Context is untrusted data, not tool instructions.
This fills the grounding gap visible in [generate.py](../src/aia_mp1/generate.py)
and [judge.py](../src/aia_mp1/judge.py), `messages_for`.

Retain the uniform distribution target. MP1-D01 asks whether an engineering
replacement benchmark is required; it does not block offline implementation.
Existing owner-reported assignment acceptance remains recorded. Do not infer a
specific benchmark waiver from it. Record any existing written or owner-reported
disposition before final assignment conformity is claimed; otherwise keep that
qualification explicit. No automatic benchmark download is part of this plan.
Source: [SDD §9](SDD-P1-03.md#9-open-decisions-and-change-control).

### Judge selection and deployment

Keep the generator model fixed for the baseline/corrected experiment. Select a
distinct local judge using a recorded capability basis; a new prompt, model alias,
different quantization of the same weights or a larger parameter count alone does
not establish stronger engineering judgment. Preserve the local endpoint boundary
and owner control of Herd settings. Source: [SDD §5.4](SDD-P1-03.md#54-judge-execution).

Read-only inventory on November 10 found Qwen3-30B-A3B Q4_K_M, Llama-3.1-8B Q4_K_M
and GPT-OSS-20B MXFP4 in the configured model share (including subdirectories).
Two RTX 5070 Ti devices each reported 16,303 MiB. Availability is established;
comparative judge quality, serving compatibility and sufficient free runtime
memory are not. The inventory is limited to that share, not every machine.

Qwen3-32B is a candidate for qualification, not the selected judge. Its official
[model card](https://huggingface.co/Qwen/Qwen3-32B) and
[release description](https://qwenlm.github.io/blog/qwen3/) identify a distinct dense
model and Apache-2.0 release. That supports investigating it, not a claim that its
quantized deployment is superior to the existing generator. Verify the chosen
conversion's provenance, license, checksum, memory/context limits and Herd support
before acquisition or serving. No model was downloaded or switched during planning.

Before selection, prepare a separate, human-verified qualification set covering
all five categories and known API/scope errors, excluded from the assessed cohorts.
Start with ten examples (two per category), two attempts per example per model,
and one candidate against the generator: at most 40 requests. This small probe
supports a selection decision; it is not a statistical proof of superiority.
Record the generator and candidate's blind rubric results under the same reference
context, schema success, unsupported claims, latency and failed attempts. Combine
that evidence with applicable official model evaluations and a documented owner
selection. Do not use the already-adjudicated five items as independent evidence
of stronger quality. If evidence does not support a stronger candidate, leave
selection pending; implementation and baseline human review can still proceed.

Freeze upstream and deployed model identities, quantization/checksum, reported
endpoint ID, context/thinking mode, prompt, token limit, timeout and temperature.
Verify requested/reported identity and structured output with a bounded preflight.
The judge temperature must remain below the generator's; record actual supported
settings. Run models sequentially if necessary. No hosted fallback or Herd/platform
changes are authorized by the plan itself. These operational choices must be
concrete before the live judge step, as required by
[judge.py](../src/aia_mp1/judge.py), `judge_run`, line 125.

### Independent labels and adjudication

The diagnostic exercise exposed a measurement gap: `calibration_report` currently
uses the latest effective labels, including post-feedback amendments. Preserve
that diagnostic report and fix assessed semantics with a separate frozen human
reference snapshot. Source: [calibration.py](../src/aia_mp1/calibration.py), line 84;
[labels.py](../src/aia_mp1/labels.py), `record_label`, line 51.

Before the first assessed judge run, require 20 complete blind reviews and freeze
their label IDs, ledger prefix/hash, selection, rubric and reference context in an
immutable `human-reference.json`. Record the reviewer's declaration that judge
output was not consulted; software timestamps alone cannot prove blindness.
Assessed judge execution requires this freeze. Later judge revisions compare to
the same frozen human reference; prompt tuning is still calibration-set tuning,
not held-out generalization.

Subsequent human amendments remain permitted and append-only. Report them in an
explicit adjudication view; they cannot silently replace the readiness denominator
or turn a failing independent calibration into a passing one. If a genuinely wrong
reference label needs correction after feedback, retain the finding, invalidate
the old readiness claim and obtain fresh blind evidence before qualifying a new
reference set. Unchanged original label records remain readable.

Add versioned optional amendment context to new labels (review stage and consulted
judge/report IDs), without reserializing or rehashing old envelopes. Legacy labels
remain diagnostic-compatible, with unknown exposure rather than an invented blind
claim. Assessed reports name their human-reference hash and separate independent
agreement from post-review agreement. This extends the immutable history contract
in [SDD §4.3](SDD-P1-03.md#43-human-label--implemented).

## Implementation sequence and ownership

Codex implements and verifies the software after approval of this plan. Chad owns
source-use decisions, model selection and authentic human scores. Instructor-only
assignment dispositions remain instructor decisions. Existing publication
authorization covers this repository's reviewed code/docs; evidence stays local.
Sources: [AGENTS.md](../AGENTS.md), [SDD §9](SDD-P1-03.md#9-open-decisions-and-change-control).

1. **Record prerequisites and contracts.** Update the SDD, requirements boundary,
   AGENTS and iteration log with the actual diagnostic outcome and the approved
   source/cohort/reference contracts. Add source-pack and collection configuration
   examples with no credentials or fictional approvals. Keep unresolved source,
   benchmark and model decisions machine-readable. Reconcile program tracking in
   a separate tracking pass with its required read-only audits.
2. **Implement assessed inputs and request grounding.** Extend `config.py`,
   `generate.py`, `schemas.py` and `cli.py`; add a focused `sources.py` for pack
   validation. Purpose is explicit and defaults to smoke. Snapshot actual reference
   bytes/hashes; fail source-purpose mismatches before calls. Include the chosen
   task/reference context in logged request inputs and resume fingerprints. Version
   new source-grounded prompts without changing the original smoke prompt.
3. **Implement bounded collection and immutable cohorts.** Add `collection.py` and
   `cohort.py`; expose independently runnable collection/status/freeze operations
   through the CLI. Keep `gate.py` decision behavior fixed, with a stable rule
   identity separate from incidental CLI edits. Keep original run IDs, gate reports
   and data unchanged. Store collection state and final cohort manifest under the
   external artifact root, with ordered member identities, hashes, policy,
   rejection/surplus/duplicate decisions, all batch denominators and remaining
   budget. Checkpoint/lock collection writes; fail unknown or interrupted evidence
   for inspection rather than guessing outcomes.
4. **Connect cohorts to review and preserve independent reference labels.** Extend
   `assessment.py` and `evaluation_cli.py` with a mutually exclusive cohort input
   alongside legacy `--run-id`. Version the manifest source type, validate all member
   lineage on read, and create the balanced seeded 20-item queue. Extend
   `evaluation_schemas.py`, `labels.py`, `judge.py` and `calibration.py` for the human
   reference freeze and separate post-review reports described above. Existing
   diagnostic commands/IDs remain readable without migration writes.
5. **Verify software and hand off the assessed runbook.** Extend existing
   `tests/test_generation.py`, `test_gate.py` and `test_evaluation.py`; add focused
   collection/source tests. Update `tools/verify.sh` for new CLI help paths if
   needed. Provide `docs/ASSESSED-RUNBOOK.md` with Windows-to-Ubuntu setup, preflight,
   collection status/budget meanings, reference use, 20-item review, freeze,
   model-switch handoff, judge/calibration and recovery. Link it from README;
   retain `docs/RUNBOOK.md` for the original diagnostic exercise. Exact new commands
   are implementation output, not commands to run from this proposed plan.
6. **Execute M3–M4 when prerequisites are satisfied.** Freeze the source pack,
   generator/prompt, collection budget and gate; collect the baseline and create
   its review queue. Chad completes 20 independent reviews with reference notes.
   Freeze those reviews, qualify/select the judge, then judge all 50 retained
   items. Compare against the frozen human reference; revise only judge prompts
   if required, retaining every run and iteration entry. Allow at most three
   measured prompt versions initially, with two attempts/item/version; stop and
   reassess after that budget rather than repeatedly sampling for a passing score.
   Freeze a successful judge receipt only when all six dimensions reach 80%.

The primary code references for steps 2–4 are listed in the starting-point table;
the existing test files and [verification script](../tools/verify.sh) define the
current test surface. Planned new filenames above do not imply existing features.

## Acceptance criteria

| ID | Testable outcome |
| --- | --- |
| A1 | Smoke remains the default; invalid purpose, missing source rights/version/hash or changed reference bytes cause zero model requests; a smoke run cannot be promoted by editing a purpose flag |
| A2 | Every assessed attempt identifies the actual task/reference context; changing it prevents resume; no human/judge decisions enter generation or judge requests |
| A3 | Replenishment never exceeds five batches, 250 planned slots or 500 generation requests per cohort; restart accounts for already-started requests, including unknown outcomes |
| A4 | A valid fixture with batch quota failures can freeze exactly ten unique eligible items/category across batches; individual batch failures remain unchanged; missing/tampered/foreign evidence and unknown requests prevent freezing |
| A5 | Stable member ordering, cross-batch deduplication and surplus reasons are reproducible; low-validity/failed batches stay in the denominator; each batch and the aggregate must meet 95% using exact counts |
| A6 | Frozen cohorts reject mutation, concurrent writers and reused output IDs; resume uses identical sources, prompt, model, rules and budget |
| A7 | A 50-item cohort selects four items/category for 20 human reviews; skipped items remain pending; all six decisions and permitted amendments are auditable |
| A8 | Assessed judging requires a frozen blind human reference and qualified distinct model; post-feedback amendments cannot change the independent score or readiness; legacy diagnostic ledgers/reports retain their original bytes |
| A9 | New calibration reports bind cohort, reference/label IDs, rubric, source context, judge prompt/settings and model identity; 16/20 passes and 15/20 fails each dimension; missing coverage cannot pass |
| A10 | Live baseline has 50 retained items, 20 authentic independent reviews and 50 resolved judge outputs, or reports the exact unmet condition without claiming M3/M4 completion |
| A11 | The assessed runbook's setup/status and recovery steps are exercised; all required offline tests and Ruff checks pass in locked WSL; no credentials/raw evidence enter Git |
| A12 | Original smoke run, both diagnostic comparison reports and original label-ledger prefix remain unchanged; archived evidence remains readable after the implementation upgrade |

A1–A9/A11/A12 are software acceptance. A10 and real >=80% agreement are evidence
acceptance; tests or post-feedback agreement cannot substitute for them. These
criteria implement [SDD §8.1](SDD-P1-03.md#81-test-strategy) and the
[measurement rules](requirements.md#measurement-rules).

## Verification and risks

Run `bash tools/verify.sh` in the locked WSL environment. Use synthetic fixtures
for malformed outputs, source/manifest tampering, interrupted request recovery,
cross-batch duplicates, deficits, surplus, partial writes, locks and immutable
reports. Add meaningful end-to-end fixture coverage from collection through a
20-label reference freeze and calibration, including adversarial labels changed
after feedback. No fixture becomes human or model evidence.

Before live collection, retain a prerequisite receipt containing source permissions,
model identity, frozen policy, budget and code identity. Before changing code,
snapshot hashes of the existing diagnostic artifacts; verify unchanged bytes
afterward. Live label entry remains Chad's action. The five-item outcome and the
166-test checkpoint are historical evidence, not a claim that future code passed.
Sources: [AGENTS verification](../AGENTS.md#verification),
[SDD §7.1](SDD-P1-03.md#71-failure-handling).

| Risk | Mitigation and consequence |
| --- | --- |
| Insufficient permitted references in a category | Keep it pending; implement/test with synthetic inputs, but do not collect an assessed cohort with a missing category |
| Gate inflections or source constraints make quotas difficult | Preserve version 1 and bounded outcomes; review an exhausted collection explicitly; any later rule change requires a versioned experiment and comparable replay |
| Different models share errors or reference context is incomplete | Require source-backed human review, separate qualification evidence and explicit uncertainty; parameter count and agreement do not prove correctness |
| Label changes after judge exposure inflate agreement | Frozen blind human reference, explicit adjudication reports, no automatic replacement of readiness labels |
| Stronger model cannot run reliably | Stop assessed judging with a concrete preflight result; keep collection/reviews available; no hidden model/provider switch |
| Baseline failure is below 15% or zero | Preserve actual results and seek instructor disposition; never introduce defects to satisfy the target |
| Requirements imply a stronger benchmark/substitution constraint | Retain the open decision and exact source; do not claim assignment conformity from local technical readiness alone |
| Scope grows into the full project | Stop this slice at baseline calibration; corrected generation, charts and demo remain the next plan |

## Handoff and stop condition

The software handoff is executable collection/cohort/reference-freeze tooling,
passing checks and an assessed operator runbook. The live M3–M4 handoff adds a
qualified source pack, frozen baseline, 20 independent labels, full judge coverage,
calibration reports and the selected frozen judge, or a precise remaining blocker.

Once independent agreement is >=80% in every dimension, report the baseline's
six-dimensional and overall failures and identify the worst segment using the
SDD tie-break policy. Plan Phase B around that measured finding. The final baseline/
corrected comparison must preserve sources, gate, rubric and judge identity; a
post-review 100% score does not authorize generator correction by itself.
Source: [SDD §5.6](SDD-P1-03.md#56-phase-b--correct-and-compare).

Implementation approval was granted November 10. This approval does not
change the approved schedule, claim new instructor decisions, select a model on
Chad's behalf, start assessed generation or require another human labeling session.
