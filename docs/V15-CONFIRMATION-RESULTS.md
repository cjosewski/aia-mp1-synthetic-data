# V15 fresh confirmation results

**Subsequent assessed result:** [V15 completed the original fifty-item baseline](V15-BASELINE-RESULTS.md)
at 95/120 (79.2%), failing D1 and D6. The 93.3% confirmation result below did not
transfer. The final assessed allocation is now consumed; M4 remains open.
The following sections preserve the earlier confirmation decision and evidence.

November 17, 2026. Chad submitted all ten reviews and sixty ratings before
either model received the confirmation examples. His exact answer sheet,
comments and declarations are preserved. This authored challenge screen is
separate from assessed calibration and does not close M4.

## Candidate result

Qwen3.5-122B-A10B matches **56/60 ratings (93.3%)** with frozen V15. All ten
responses were valid on their first attempts; no retries or transport failures
occurred. Candidate request time was 937.60 seconds (15.63 minutes).

| Dimension | Matches | Agreement | False approvals | False rejections |
| --- | ---: | ---: | ---: | ---: |
| D1 — Completeness | 10/10 | 100% | 0 | 0 |
| D2 — Safety | 8/10 | 80% | 2 | 0 |
| D3 — API realism | 10/10 | 100% | 0 | 0 |
| D4 — Scope | 10/10 | 100% | 0 | 0 |
| D5 — Context | 8/10 | 80% | 0 | 2 |
| D6 — Tips | 10/10 | 100% | 0 | 0 |

The two safety false approvals are consequential. In C04 the judge credits
read-only precautions while overlooking parameter access before a null check.
In C10 it credits a shape check that enforces the wrong shape contract.
It detects **0/2 human-rated safety failures**, despite 80% D2 agreement.
Both examples also receive D5 false rejections: the judge treats an incorrect
operation as unclear context where Chad credits the stated problem framing.
All four errors remain scored; no human ratings or rubric anchors were revised.

All sixty candidate public explanations were inspected against the exact
answer, task, source context and human comment. This audit creates no human
labels and does not claim execution of generated engineering code. Matching
ratings can still have limited explanations; the detailed audit retains those
qualifications, including a malformed shape notation in the C10 D5 explanation.

## Matched comparator and selection

Qwen3-30B-A3B received the same ten messages, V15 prompt and numerical settings.
It matches **47/60 (78.3%)**: D1–D6 counts are **7, 8, 8, 10, 10, 4** out of ten.
It has twelve false approvals and one false rejection. It misses required API
linkage and state preparation, accepts incorrect tips, and credits an incorrect
cooling result without checking the formula. Its C06 tip rejection misdescribes
advice present in the payload. Both models miss the same two safety failures.

The candidate gains eleven matches and loses two (C04/C10 D5), a net nine.
There is no new candidate safety/API false approval relative to this comparator.
All **120 public explanations** were inspected, including matching decisions.

**Decision:** select pinned Qwen3.5 with frozen V15 and the 4096 reasoning cap
for the remaining assessed-baseline evaluation. Codex records this technical
selection under Chad's standing instruction to pursue completion at the original
80%-per-dimension requirement. It is not a new owner quote or instructor approval.
The basis is the complete matched comparison, per-dimension coverage and better
API/tip discrimination, with both safety misses and context regressions retained.
Do not tune V15 on these now-exposed examples or describe selection as calibration.

## Interpretation and next gate

These ten assistant-authored examples cover all five categories but are not a
representative random sample. Shared source/task families and the models' shared
Qwen family limit independence. Candidate-first execution is a fixed-order
comparison. Every human D4 and D5 rating is a pass, so these dimensions do not
test detection of human-rated failures in this sample. The human quality count
is 43/60 passes, a different measure from model agreement.

Keep the [score discrepancy](AGREEMENT-DISCREPANCY-20261117.md) visible:
the assessed V13 result remains **87/120 (72.5%)**; V15 exposed development was
**58/60 (96.7%)**; this fresh candidate result is **56/60 (93.3%)**. Different
samples cannot establish a before/after prompt improvement. A supported model
selection must still be followed by the original fifty-item baseline, compared
against the same twenty frozen human reviews, with **16/20 matches in every
dimension** and complete eligible coverage. The final assessed version has not
been spent. The corrected cohort and its pending twenty human reviews remain
preserved.

## Evidence identities

Twenty starts produced twenty valid initial responses, without retries, failures
or unknown outcomes. Combined request time was 1,063.33 seconds (17.72 minutes);
the comparator used 125.73 seconds. Cumulative recorded starts are **338**.
All 195 frozen files verified and the final report replayed exactly. All 471
entries in five previous preservation records remain unchanged. A new seal
covers 266 files. Both owned Mac servers stopped successfully; their PIDs were
absent and port 8081 was clear. No Herd service or setting changed.

The complete 267-file archive is verified locally and on the NAS:
`operator/MP1-QWEN35-V15-CONFIRMATION-001-COMPLETE.zip`, SHA-256
`0a8374d7d0089cccf6f17b083aa9b2f2d7522b493d7bfc0693f92085d8e20645`.
The preparation's 483 locked WSL tests remain the implementation verification;
no code changed during inference.

| Identity | Value |
| --- | --- |
| Frozen implementation | `e773879e83390333fb711a74b2c38aa54773226e` |
| Plan SHA-256 | `10eda16b095e19310ecf59f204626cd9f5c0310c15aeeef7318c9cfda7e4ae7a` |
| Human reference SHA-256 | `3c58e84f1debb011ed8c42b1f6d10a864253ced06aebedc7cbd4f6b030690de7` |
| Exact submission SHA-256 | `5d53da6ebdc16c4fc51c30944972a5242992f83d9b6a7e682e19d1aa04f82408` |
| V15 prompt SHA-256 | `0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d` |

Raw evidence stays outside Git under workspace `artifacts/evidence/P1-03/`:
`qualification/MP1-QWEN35-V15-CONFIRMATION-001/` contains the frozen package and
ledger; `qualification/v15-confirmation-intake-20261117/` contains the exact
submission, intake, replay and semantic audit. The protocol and runtime checks
are specified in the [operator procedure](V15-CONFIRMATION-TRANSPORT.md).
