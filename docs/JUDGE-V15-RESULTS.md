# V15 development result and fresh confirmation handoff

November 17, 2026. The [bounded development comparison](JUDGE-V15-PLAN.md)
completed all twenty requests on their first attempt. V15 meets the predeclared
conditions to advance to **fresh blind confirmation**. It has not passed full
assessed calibration. The original requirement remains **at least 80% agreement
in each of D1–D6**, and M4 remains open. The owned Mac server has stopped; the Mac
is free.

## Measured development result

**Discrepancy recorded:** the assessed baseline remains **87/120 (72.5%)**.
The **58/60 (96.7%)** below uses a different, exposed development set. V13 already
scores **57/60 (95%)** on this same set, so V15's paired gain is one matching
rating, not an assessed increase from 72.5% to 96.7%. See the
[measurement reconciliation and unresolved transfer risk](AGREEMENT-DISCREPANCY-20261117.md).

Both arms used Qwen3.5-122B-A10B Q4_K_M, the same ten exposed development examples,
the unchanged frozen human reference, identical user messages and the same
runtime/settings. Only the judge prompt differed. No assessed item was judged.

| Dimension | Matched V13 | V15 |
| --- | ---: | ---: |
| D1 — Answer Completeness | 9/10 (90%) | 9/10 (90%) |
| D2 — Safety Specificity | 10/10 (100%) | 10/10 (100%) |
| D3 — API Realism | 10/10 (100%) | 9/10 (90%) |
| D4 — Scope Appropriateness | 10/10 (100%) | 10/10 (100%) |
| D5 — Context Clarity | 8/10 (80%) | 10/10 (100%) |
| D6 — Tip Usefulness | 10/10 (100%) | 10/10 (100%) |
| Total | 57/60 (95%) | 58/60 (96.7%) |

V15 corrected three false approvals and introduced two false rejections. There
were no new safety/API false approvals. All ten cases and all 120 public
justifications were inspected, including explanations accompanying matching
ratings. The two remaining errors are **C05 D1 and D3**: V15 incorrectly rejects
the valid Revit `Transaction` attribute with `TransactionMode.ReadOnly`.
The pinned reference sample demonstrates that attribute. These are scored errors,
not waived discrepancies. Minor attribution issues in other explanations are
retained in the semantic review. The control also differed from its previous
run, demonstrating run-to-run variation.

The result satisfies the declared advancement test: complete coverage, at least
8/10 per dimension, more matches than the matched control and no new D2/D3 false
approval. It supports another independent check with disclosed limitations;
ten exposed examples and a net one-rating gain do not establish generalization
or full-baseline readiness.

## Execution and audit

- Twenty starts, twenty valid initial responses, zero retries, failures or
  unknown outcomes. The forty-start maximum was not exhausted.
- Request time: 974.98 seconds for V13 and 945.96 seconds for V15; 32.02 minutes
  combined. This is inference-request time, not total project effort.
- WSL2 ran Python and the locked dependencies. The Mac ran only the owned native
  server, reached through a loopback SSH tunnel. Herd services were unchanged.
- Both weight shards, native build/template, context and token reservations were
  verified. Ownership was rechecked before dispatch. The run ended successfully,
  the owned server stopped and its port was verified clear.
- All 191 frozen input files verified unchanged; the report replays from the
  complete request/result ledger. Original assessed ratings and human labels are
  unchanged. The final assessed-baseline version remains unused.
- All 171 prior sealed entries verified unchanged after execution. A new seal
  covers 300 evidence files, excluding the new editable answer sheet.
- Preparation passed 468 locked WSL tests, Ruff and launcher syntax checks.
  After the review-instruction updates, 33 relevant review/intake/acceptance tests
  passed in 12.99 seconds.
  Cumulative recorded starts are now 318, including historical failed and
  interrupted attempts. None of the fresh confirmation examples has been sent
  to either model.

| Identity | Value |
| --- | --- |
| Frozen implementation | `415b32dad21228ddbfe1667be4671082b74272c8` |
| Plan SHA-256 | `6a78c8846259222babd1d5f4664cafc4bc1f9692a3e857492f30039231b0b59a` |
| V15 prompt SHA-256 | `0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d` |
| Human-reference SHA-256 | `b8668b09e762b60599fd578ec673b07ab6f3362c7008f192ee82b5fd0341f17b` |

Raw evidence remains outside Git under `artifacts/evidence/P1-03/qualification/`:
`MP1-QWEN35-V15-20261117` contains the frozen implementation, inputs and returns;
`restore80-v15-20261117` contains the replay, semantic review, advancement decision
and preservation checks. Human-readable summaries do not replace these records.

## Completed subsequent confirmation

November 17: Chad completed the review below. The [fresh matched result](V15-CONFIRMATION-RESULTS.md)
is 56/60 versus 47/60, with two safety false approvals and two context false
rejections retained. Full assessed calibration is next. No repeat of this review
is needed; the original preparation instructions follow for traceability.

## Original human-review instructions

Open `\\192.168.0.55\aia\Handoff\P1-03\qwen35-v15-blind-confirmation-v1`.
Read `RUNBOOK.md` and the 21-page `REVIEW-PACKET.pdf`, then complete that folder's
`MY-ANSWERS.md`. Only the answer sheet needs editing. No software installation,
model server or execution of engineering code is required.

These are ten new assistant-authored challenge examples, two per category, with
the unchanged rubric and permission-cleared reference context. They are distinct
from assessed cohorts and contain no suggested ratings. Exact payload duplicates
against the old confirmation and both fifty-item cohorts were excluded; related
task families remain, so no claim of semantic independence or representative
sampling is made. Authorship and preparation lineage are recorded in the packet.

The packet manifest SHA-256 is
`1098fb60c1497828deae342a7dc68a7647ae49f4952ee95258417947c7db1c07`.
The PDF preserves all task, payload and supplied source strings; its identity is
recorded separately without modifying the frozen packet manifest.

After Chad's authentic review is frozen, prepare and freeze the executable matched
confirmation transport using V15 for Qwen3.5 and Qwen3-30B-A3B on identical inputs.
The [separate V15 runner and operator procedure](V15-CONFIRMATION-TRANSPORT.md)
are implemented offline; real package creation still requires that review.
The packet bounds this to twenty initial requests and forty starts maximum, with
the same 4096 reasoning cap and explicit ownership/identity checks. Preserve and
inspect every outcome before a stronger-judge selection. A successful selection
then permits the remaining assessed-baseline run, which must reach at least
16/20 agreements in **every** dimension. Freeze that qualified judge for the
baseline/corrected comparison and recheck the worst category/dimension before
claiming the existing generator correction meets Phase B.

The existing twenty-item `M5-corrected-review-001` packet remains intact and can
wait while the ten-item confirmation is completed. No corrected judge outputs or
quality-improvement results have been claimed.
