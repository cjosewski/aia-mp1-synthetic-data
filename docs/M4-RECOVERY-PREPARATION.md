# M4 recovery preparation and offline scoring

November 17, 2026. The offline scorer and ten **draft** source checklists are
prepared. No model calls or Mac use occurred. M4 remains open, the three assessed
allocations remain consumed, and the proposed twenty-start development trial is
not allocated or started.

## Selected development cases

Use two previously exposed, human-reviewed original-baseline items per category.
The selection deliberately includes all three known human D2 failures, task/tip
faults and valid-reference controls. It is targeted development, not a random
sample or independent confirmation. Selection reasons are kept outside candidate
inputs; no human ratings/comments or earlier judge decisions appear in those inputs.
The existing V15 results remain the proposed paired comparator.

All IDs below have prefix `baseline-001-`.

| Item suffix | Category | Selection purpose | Check spans | Unbound checks |
| --- | --- | --- | ---: | ---: |
| b02-item-0011 | GIS | Coordinate/geometry interface and CRS obligation | 16 | 2 |
| b03-item-0011 | GIS | Source-CRS uncertainty and known safety disagreement | 18 | 2 |
| b02-item-0007 | AEC | Nullable parameter/accessor safety disagreement | 19 | 5 |
| b02-item-0047 | AEC | Mark update sequence and technical tips | 15 | 1 |
| b02-item-0008 | Structural | Fixity validation and known safety disagreement | 18 | 1 |
| b01-item-0013 | Structural | Material/element ownership; V15 false-rejection control | 14 | 3 |
| b02-item-0014 | CAD | Parametric cone procedure | 18 | 1 |
| b02-item-0019 | CAD | Parametric sphere reference-pass control | 17 | 0 |
| b02-item-0040 | Simulation | Stiff system reference-task givens | 19 | 3 |
| b01-item-0050 | Simulation | Vectorized RHS reference-pass control | 21 | 0 |
| **Total** | **Five categories** | **Ten cases** | **175** | **18** |

The original assessment/cohort/source lineage was validated with the existing
assessment loader. All selected IDs belong to the original twenty-review
selection. Candidate text, tasks and rubric are unchanged. Forty historical
files, including source snapshots, assessment data and human-reference/label
files, were hashed before and after preparation and verified unchanged.

## What the source packet establishes

The packet reuses retained, permission-recorded sources from the V8.1 snapshot.
It makes 26 category-specific excerpt ranges available across 52 per-case
excerpt entries, with exact byte ranges, original artifact hashes, source versions
and permission/extraction lineage. It does not retrieve new online documentation
or assert new reuse permissions.

Each case contains `input.json`, `plan.json`, `CHECKLIST.md`,
`structural-report.json` and `preparation-status.json`. All non-whitespace task
and candidate text is covered exactly once. Sentence/clause segmentation is a
draft convenience, **not proof that each span contains one atomic claim**.
Source bindings are topic-based retrieval candidates, **not verified support**.
All bindings require semantic applicability review. Zero unbound checks for a
case therefore does not make that case ready.

The 18 unbound checks and the broader source limitations are retained openly:

| Area | Further evidence or review needed |
| --- | --- |
| GIS | CRS provenance/preservation, unknown-CRS handling, exact returned-value contracts, installation/workspace statements. A geometry-construction example does not settle unknown-input CRS policy. |
| AEC | Nullable area-parameter access, accessor scope, version/install claims and applicability of door-mark examples to structural-framing operations. Partial samples cannot establish that an unlisted member does not exist. |
| Structural | Invalid-argument behavior versus stability, model inspection, general unit validation and version/platform assumptions beyond the examples. |
| CAD | Full constructor/property coverage, Radius2, getObject, units, installation and invalid-dimension behavior beyond the retained samples. |
| Simulation | NumPy/plotting interfaces, exact mathematical checks and asserted exception, instability or universal solver-preference claims beyond solve_ivp's documentation. |

Some unbound entries are general advice or mathematical task alignment, not API
claims. Do not fill them with an unrelated primary quotation just to satisfy the
current conservative contract. The next source audit must separate atomic
claims, seek appropriate evidence, and document any necessary protocol revision
before freezing a live trial. Original task/rubric thresholds remain unchanged.

No observations, accepted fact audits, scores or accepted scoring audits were
invented for these real items. `execution_enabled` is false throughout. Context
fit has not been measured using the target tokenizer; input character counts are
reported only as sizes, not token estimates or a passing preflight.

## Implemented scoring integration

[recovery_scoring.py](../src/aia_mp1/recovery_scoring.py) consumes the existing
checklist validator and observations. Before building a scoring input it rechecks
source bytes, permissions, exact citations and plan identity. Every check needs
an attributed fact-audit entry; the audit must also record checklist completeness,
atomicity, source applicability/permission and absence of reference-rating leakage.
Unknown facts, source gaps or rejected audit entries block scoring.

Audit records identify their origin as `assistant_review` or `human_review`.
They are technical review receipts, **not human quality labels**. A valid receipt
is an attributed assertion, not independent proof of truth; the code cannot
authenticate a reviewer's expertise or make an incorrect audit correct.

The scoring input is fingerprinted and keeps the unchanged six rubric anchors.
Its model-facing view retains candidate/reference text, checks, observations and
primary excerpts, omitting duplicate catalog text and audit commentary. The
application supplies the fingerprint for the model to copy; the model never
has to calculate it. The two [fact](../prompts/recovery-facts-v1.md) and
[score](../prompts/recovery-score-v1.md) prompts are unmeasured drafts.

The response has fixed D1–D6 keys. Each dimension must address every check routed
to it, including all required tips; duplicate/unknown checks and source text
masquerading as candidate evidence are rejected. Each effect is `supports`,
`defect` or `not_decisive`, with an explanation. An audited contradiction cannot
be converted into supporting evidence. A decisive defect cannot accompany a
pass. A contradiction may be irrelevant to a different dimension, but that
explanation still needs semantic review.

D4 explicitly records professional-review applicability. The frozen sign-off
anchor is not replaced with task-scope consistency. Uncertain applicability or
any null dimension remains unresolved. Scores require a second audit, bound to
the exact score bytes and covering all six dimensions. Rejected dimensions are
reported; an accepting audit cannot supply missing scores.

Only a complete, accepted scoring audit permits a development `Judgment` shape
to be emitted. The surrounding report **always** says `calibration_eligible:
false`. No assessed-calibration writer, human-label writer or live transport is
connected. A new assessed allocation/qualification cannot be manufactured by
extracting the nested judgment.

## Offline operation and remaining boundary

Inside the locked WSL environment, the scorer can validate saved artifacts:

```bash
uv run --locked python -m aia_mp1.recovery_scoring \
  --input /EXTERNAL/input.json --rubric config/rubric.json \
  --sources /EXTERNAL/sources --plan /EXTERNAL/plan.json \
  --observations /EXTERNAL/observations.json \
  --fact-audit /EXTERNAL/fact-audit.json --scores /EXTERNAL/scores.json \
  --score-audit /EXTERNAL/score-audit.json
```

These are placeholders; the real draft packet intentionally has no observations
or accepting audits. Omit `--score-audit` to inspect unaudited scores without
projecting a judgment. Exit 0 means an audited development judgment was emitted,
1 means unresolved/unreviewed/rejected scores, and 2 means invalid input.
None authorizes model execution or certifies calibration. Inputs are read only;
errors avoid echoing input contents.

Evidence is outside Git at
`artifacts/evidence/P1-03/qualification/m4-recovery-preparation-20261117/`.
The preparation script, preservation receipt and packet are retained for replay.
The source audit, claim segmentation, missing evidence, durable staged transport,
token preflight and frozen live package remain. No new action is requested from
Chad at this checkpoint, and the corrected M5 packet stays intact.

Verification: **553 locked WSL tests passed in 104.73 seconds**, including 28
new synthetic scoring/audit tests. Lint, format and CLI checks pass. Tests cover
fact-audit bypasses, source/candidate role confusion, omitted tips, changed source
or audit lineage, contradiction reversal, passes paired with decisive defects,
uncertain D4 applicability, incomplete/rejected audits and withheld projection.
Synthetic accepting receipts are not applied to any real item.
