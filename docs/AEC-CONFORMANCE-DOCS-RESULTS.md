# AEC conformance documentation comparison — result

November 20, 2026. Run `api-development-qwen-conformance-docs-001`, protocol
`98ead1c0e6cfa43c1348b846528dc46f17fc8756f957b18454b2f4f0214b30da`. This was the
bounded ten-case development trial of the [conformance revision](AEC-CONFORMANCE-DESIGN.md).

**The method fails the development gate and is not promoted.**

## What ran

A fresh Mac runtime was verified before any request:

- full rehashes of both Qwen3.5-122B shards and the server binary;
- build `b12110-cd959bae9`;
- the exact owned process, its argv and its loopback listener;
- direct SSH tunnel ownership and the native thinking template.

The deployment receipt is `9ec0dafd…`. A read-only preflight then accepted the
native-schema judgment request at `/apply-template`, so the server built the
grammar. The first case's prompt was 5,611 tokens, needing 15,003 of 16,384, and
all ten lookups fit.

The score used **18 of 20 model starts** (10 lookups and 8 judgments) and **23 of
30 page requests**, all of which opened. Each case and stage had one attempt,
with no retry or repair.

Afterwards the owned server stopped (launcher exit 0) and the tunnel closed.
Offline replay reproduced report `2ac50fb5…` with the run evidence unchanged. The
parent and ancestor lineage were re-verified on replay.

## Result

| | D1 | D2 | D3 | D4 | D5 | D6 |
| --- | --- | --- | --- | --- | --- | --- |
| **Conformance (of 10)** | **0** | **3** | **7** | **8** | **6** | **4** |
| Original control | 3 | 4 | 8 | 9 | 8 | 8 |
| Completed online method | 2 | 3 | 9 | 9 | 8 | 8 |

**Validity: 8 of 10 cases produced validated judgments.** Every dispatched
judgment passed the logical overlay, the canonical `GroundedJudgment` and
`validate_grounding`. The extra-field, task-quote and page-ID failures that
stopped the wire trial did not recur.

**Both failed cases broke at the lookup stage, under the unchanged lookup schema:**

- `item-0005` requested more than three anchors on one page.
- `item-0011` repeated a search anchor.

Under the owner's continue-and-count policy, both count as non-matches. Each
consumed its start, and neither was redispatched.

**Agreement is worse than both earlier methods in four dimensions:**

- **D1 (answer completeness) is at zero, but this is mostly not a new
  regression.** Of the eight compared cases, the reviewers failed seven on D1,
  and the judge passed all seven. It also failed the one case the reviewers
  passed. The completed online method also passed D1 on all eight of these
  cases. It drops from 2 to 0 because of one changed decision (0047) and one
  lookup failure (0011), the two answers the reviewers passed. See the D1 audit
  below.
- **Changed decisions against the control:** one D3 correction and four
  regressions (D1 twice, D6 twice).
- **Changed decisions against the completed online method:** one D2 correction
  and three regressions (D1 once, D6 twice).

The gate needs complete ten-case coverage and at least 8/10 in every dimension.
It fails on coverage and on D1, D2, D3, D5 and D6. Only D4 reaches 8. The
explanation audit was not performed, because no audit could rescue the gate.

## Interpretation and limits

The native-schema contract solved the problem it targeted: response conformance
and evidence references. It did not improve judgment quality.

The lookup failures show that the unconstrained lookup stage now limits
coverage. This is a single run with eight comparisons, so it cannot separate the
effects of constrained decoding, the narrower contract and sampling variation on
D2, D5 and D6.

## D1 completeness audit (offline, no model calls)

In the frozen rubric, D1 is **Answer Completeness**: can the reader complete the
task end to end. API correctness is D3. Earlier drafts of this record wrongly
described the D1 pattern as API-correctness leniency.

All eight retained judgments were read against the blind reviews:

- **Every lenient D1 pass rests on stage coverage.** The judge's seven passes
  say, for example, "covers all essential stages" or "explains the required
  logic sufficiently". The reviewer's failures turn on whether those stages
  would actually complete the brief's obligation. The reasons given include:
  - a required field or rows left out;
  - the ordering or indexing problem the brief is about, which goes unaddressed;
  - a wrong derivative at a boundary;
  - a call that yields the default object instead of the requested one.
- **The judge's own evidence does not reach its D1 decision.** In three of the
  seven (0024, 0007, 0014), the judge recorded "contradicted" documentation
  evidence for the steps involved, yet still passed D1. Once it said
  "despite the API error in steps".
- **In the other four, the judge marked essential obligations as covered when
  the reviewer found them missing.** In one, it said the answer explains the
  very convention that the reviewer identified as the missing point.
- **The one reviewer D1 pass in the comparison (0047) went the other way.** The
  reviewer judged the workflow complete and assigned its API errors to D3. The
  judge failed D1 for missing concrete code.

The same stage-coverage pattern appears in the online method, which passed D1
on all eight of these cases. It also matches the earlier assessed finding that
the third prompt "still approved six incomplete answers". It is a property of
the judge's D1 reasoning, not of the conformance contract.

One possible direction would require the judge to propagate its own
contradicted or missing evidence on the steps into D1, and to test each core
brief obligation for whether it would work, not just whether it is present.
This is an untested hypothesis. It would need owner approval, a new frozen
protocol and a new bounded trial. The private audit table is
`d1-completeness-audit-table.txt` (`b754babb…`) in the execution folder.

**Owner clarification of D1 (November 20, 2026):** "API errors only count against D1 when they break a step." An API error that
leaves a step able to do what the task needs is a D3 matter only. One that
prevents the step from producing the required result is also a D1 completeness
failure. This clarifies how the frozen D1 anchor applies; it does not change
the rubric or any threshold. It is consistent with the blind reviews audited
above, including the one D1 pass (0047). The owner stated the rule in general
terms; the audit's per-case notes were not used to derive it.

Do not treat the conformance result as calibration progress. The assessed
baseline is still 12, 15, 12, 17, 13 and 11 of twenty, and M4 remains open.

## Evidence

- Run directory: `../artifacts/evidence/P1-03/aec-course/api-development-qwen-conformance-docs-001/`.
  It holds the protocol, deployment, runtime records, starts, raw returns,
  contracts, fits, failure receipts and report.
- Execution receipts: `../artifacts/evidence/.conformance-docs-execution-20261120/`.
  These are the preflight result, execution start, score and replay outputs, and
  the completion receipt `1f935197…`.

No human label, earlier score or raw candidate response is published here.
