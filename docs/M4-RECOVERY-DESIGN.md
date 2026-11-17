# M4 recovery: evidence checks before dimension scores

November 17, 2026. **Offline design and contract prototype implemented; live
execution is not enabled.** No new model calls, Mac use, review changes or assessed
allocation. Cumulative recorded starts remain 388. M4 remains open.
The subsequent [preparation/scoring checkpoint](M4-RECOVERY-PREPARATION.md)
adds ten draft checklists and offline scoring with explicit audit lineage;
source completeness and live execution remain pending.

## Problem and intended change

[V15's original-baseline result](V15-BASELINE-RESULTS.md) is 95/120 (79.2%),
including D1 70% and D6 65%. It misses all three human-identified safety failures.
The 93.3% small confirmation result did not transfer. Repeating a wording-only
change is not the next experiment.

The [V8.1 verifier](JUDGE-V81-VERIFIER.md) exposed a second problem: the model
could produce valid source IDs while bundling claims, overlooking source gaps,
or classifying API statements as procedures to avoid the primary-source rule.
Its scorer then confused candidate, source and rubric roles in two failed outputs.
Neither a JSON-valid response nor a matching final rating establishes a sound
explanation. V15 also produced matching ratings with incorrect reasons.

This recovery separates three questions:

1. Did the application account for the task and every candidate passage, including
   every tip, using unchanged text and permitted retained sources?
2. Does each cited source actually support the specific claim for the required
   version, object, parameter type, prerequisites and units?
3. Given those findings, what does each **unchanged rubric dimension** require?

Only the first question has an automated structural answer. The other two need
semantic review and measured evaluation. Facts alone cannot become judgments.
The subsequent offline scorer can emit an audited development judgment shape,
but never human labels or an eligible calibration receipt.

## Implemented offline boundary

The isolated [recovery_checks.py](../src/aia_mp1/recovery_checks.py) reuses V8's
source-artifact, exact excerpt, permission-receipt and typed-catalog validation.
Historical V8/V8.1 validators and assessed defaults are unchanged.

A separately prepared `recovery-offline-v1` checklist pins the exact fact input
and rubric hashes. Application IDs `K0001`, `K0002`, etc. identify fixed checks.
Each check contains an exact subject span, question, dimension review routing and
allowed source/version bindings. The model cannot change those roles or routing.
The whitelist schema has no rating, reviewer or human-reference fields. Text
fields still require an audit for accidental answer-key leakage.

Every non-whitespace character in `R.task` and every candidate passage must be
covered exactly once, without overlapping spans. Offsets are zero-based Unicode
character offsets into the retained passage, with an exclusive end. They are
distinct from V8's UTF-8 byte offsets into original source files. Quotes preserve
whitespace exactly. Checks should separate atomic claims; character coverage
**does not prove semantic completeness or atomicity**.

| Subject | Fixed kind / minimum dimension review | Permitted evidence |
| --- | --- | --- |
| Reference task | `task_obligation`, D1 | Frozen task or retained primary excerpt |
| Question / equipment problem | `context`, D5 | Frozen task or retained primary excerpt |
| Answer, tools and steps | `technical_claim`, D1 and D3 | Retained primary excerpts |
| Safety text | `technical_claim`, D1, D2 and D3 | Retained primary excerpts |
| Every tip | `technical_claim`, D1, D3 and D6 | Retained primary excerpts |

These mappings require review in the listed dimensions; they do not assign a
failure to every dimension when a claim is wrong. Extra review dimensions may
be included. D4 professional-review applicability still needs explicit treatment
in the scoring stage; the fact checklist alone is not a six-dimension judgment.
Technical assertions embedded in a question/problem must receive primary-source
bindings during preparation and semantic audit, rather than using task agreement
as proof of API behavior. The parser does not recognize technical prose.

An empty binding list is an explicit source gap. It is valid to record the gap,
but it blocks a conclusive observation. Authored summaries, rubric text and
candidate assertions cannot stand in for primary technical evidence. Binding a
version proves only that the retained version label is unchanged, not that the
source applies to the task's version or that its licensing assertion is correct.
Those judgments remain part of the source audit.

The response supplies only the canonical checklist hash and exactly one
observation per check: `supported`, `contradicted` or `insufficient`, exact source
citations and a public explanation. Non-insufficient conclusions need at least
one bound citation. Missing, duplicate, foreign and altered references fail.
Uncertainty remains unresolved; it cannot silently become a pass. Contradictions
are retained without automatic dimension ratings. Even a fully valid response
reports `calibration_eligible: false` and `semantic_audit: required`.

## Semantic audit and proposed scoring stage

Before inference, prepare checks from task, candidate, rubric and permission-cleared
sources, excluding human ratings/comments and earlier judge outputs from model
inputs. Development cases are already exposed to the project team; disclose this
as targeted development, never independent confirmation. Freeze and inspect the
checklist before sending it to a model. No checklist should encode an expected
rating or tell the verifier which answer to reach.

For each technical claim, inspect API owner, returned object/value, storage type,
argument contract, prerequisites, units and version as applicable. Split compound
claims. Identify source gaps explicitly. A member absent from a partial excerpt
is not evidence that the member does not exist. A quotation about a neighboring
method is not support. Inspect task obligations against the **whole candidate**
before declaring an essential step missing; code snippets are not universally
required by the rubric. Keep mathematical givens unchanged and independently
check any decisive numerical claim. Record every unsupported decisive conclusion.

The offline scorer receives the frozen checklist and findings. Its output
has six application-defined dimension keys and check-ID dispositions;
it is not asked to reproduce rubric text as an ID or choose interchangeable
candidate/source namespaces. Application code must attach the frozen rubric and
original candidate evidence. All relevant findings, including tips and conflicts,
must have dispositions. An unresolved decisive fact prevents canonical projection.
A disagreement about a finding needs evidence and a recorded explanation, not
silent omission. Contradictions do not mechanically determine unrelated scores.

Do not redefine D4 to resolve the known difference between task-scope comments
and the frozen professional-sign-off anchor. Retain that discrepancy, the original
human ratings and their effect on agreement. Similarly, never change human D1/D6
ratings to fit the new checklist. Explanation accuracy and binary agreement are
separate reported outcomes.

**Implemented offline:** ten draft source/checklists, semantic-audit receipt
contracts and simplified scoring/projection; see the preparation checkpoint.
Actual semantic audits, complete source coverage, staged transport integration,
token preflight and a frozen execution package remain pending. The CLI below has
no execution switch. This is not a repaired live V8 run or a qualified judge.

## Proposed bounded development trial — not allocated or started

Prepare ten previously exposed original-baseline cases, two per category. Include
all three known human D2 failures and cases that distinguish missing obligations,
invalid tips and valid API claims wrongly rejected. Publish the exact item list
and selection rule before any calls. This deliberately targeted set is biased
toward known failures and cannot establish assessed readiness.

Use the already saved V15 decisions for those same items as the paired comparator;
do not spend new control calls or describe the comparison as a contemporaneous
randomized experiment. Candidate model proposed: pinned Qwen3.5-122B-A10B, so the
experiment changes verification procedure rather than model and procedure at
once. Freeze weights/build/template/settings anew before execution; current
runtime availability is not assumed. Do not fall back to hosted models.

Proposed ceiling: **20 starts total**, one verifier and one scorer per case,
**one attempt per stage**, no retries. A failed/unresolved verifier skips its
scorer without donating that allowance. Stop on two consecutive structural
failures, any unknown request outcome, source/runtime drift, context overflow or
the ceiling. Also stop on the first semantic audit finding of an unsupported
decisive claim or ignored decisive uncertainty; inspect each verifier before its
scorer. A stopped run retains all scheduled cases in the coverage denominator.
No schema repair, truncated context, selective rerun or silent budget extension.

Carry forward durable start/outcome records, exact requests/raw completions,
single-writer protection, unknown-outcome accounting and explicit transport
failure retention from the existing staged implementation. Exact wire token
preflight must include sources, checklist, response schema and downstream memo.
If it will not fit, revise and freeze the protocol **before** a request; do not
silently drop claims. Changes to Herd services remain outside this project.

Advance only with ten complete audited pairs, at least 8/10 agreement in every
dimension, no D2/D3 false approvals, more total matches than paired saved V15,
no dimension decrease, no increase in false approvals, and no unsupported
decisive findings. Report false rejections, rationales, source gaps and exposure
limitations even if those gates pass. This is a development screen, not a claim
that a sample of ten certifies reliability.

Passing supports a separately frozen confirmation design, not automatic assessed
calls. The previous three assessed allocations remain consumed. A further full
baseline needs an explicit recorded allocation extension and the unchanged
>=80%-in-each-dimension rule, with fifty retained items and twenty authentic
reviews. No repeat human review is requested for this offline task. M5 remains
preserved and unqualified until M4 succeeds.

## Offline use and verification

Run inside the repository's locked WSL Ubuntu environment:

```bash
uv run --locked python -m aia_mp1.recovery_checks \
  --input /EXTERNAL/fact-input.json \
  --rubric config/rubric.json \
  --sources /EXTERNAL/retained-sources \
  --plan /EXTERNAL/check-plan.json \
  --observations /EXTERNAL/observations.json
```

Paths are placeholders, not a prepared operator packet. Omit `--observations` to
inspect source coverage only. Output goes to stdout; inputs are never written.
Exit 0 means structural checks completed without source gaps/unresolved findings,
**not** truth, calibration or permission to execute. Exit 1 reports known gaps;
exit 2 reports invalid input without echoing its contents. Preserve any real
plans/responses/reports outside Git, separately from sealed historical artifacts.

Synthetic adversarial tests exercise skipped tips/task/steps, source-role
substitution, changed versions and bytes, overlapping spans, incomplete responses,
invented citations, foreign checklist lineage, unresolved evidence, and misleading
but structurally valid citations. Full-suite validation is recorded with the
implementation commit. No real source finding or model quality measurement is
produced by these tests.

Verification: **525 tests passed in 109.98 seconds** in locked WSL Ubuntu with
the analysis extra and optional ReportLab renderer, including 26 new recovery
tests. Ruff lint/format and the offline CLI help check pass. No live requests.
