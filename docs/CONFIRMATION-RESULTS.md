# Fresh confirmation and judge-selection decision

Completed November 15, 2026 local time (November 16 UTC). **The Mac is released:**
the owned model server is stopped and the return is verified locally and on the NAS.

Qwen3.5-122B-A10B matched **56/60** frozen human ratings, versus **46/60** for
Qwen3-30B-A3B. It corrected ten comparator disagreements with no regressions on
these ratings. This supports selecting the distinct Qwen3.5 model for the next
assessed calibration experiment. It does **not** establish calibration readiness,
universal model superiority or error-free judging.

## Owner selection recorded

Chad selected the candidate on November 15, 2026 local time (November 16 UTC):

> Select Qwen3.5-122B-A10B for assessed baseline calibration using the frozen V13 prompt and settings, with the reported errors retained.

The [attributed selection receipt and assessed run protocol](ASSESSED-BASELINE-MAC.md)
preserve that instruction and the full evidence below. Selection leaves every
course threshold unchanged and does not rewrite any human rating or declare the
judge calibrated. No new answer sheet is needed for this step.

The [first assessed baseline run](ASSESSED-BASELINE-RESULTS.md) stopped at 11/50
complete judgments after token-limit exhaustion. All six dimensions still require
at least 80% agreement against the separate 20-item human reference, with complete
coverage, before generator correction. The Mac is free; no model server remains.

## Matched results

| Dimension | Qwen3.5 matches / 10 | Qwen3 matches / 10 |
| --- | ---: | ---: |
| D1 — Completeness | 9 | 6 |
| D2 — Safety specificity | 10 | 8 |
| D3 — API realism | 9 | 8 |
| D4 — Scope | 10 | 9 |
| D5 — Context | 8 | 6 |
| D6 — Tips | 10 | 9 |
| Total | **56/60 (93.3%)** | **46/60 (76.7%)** |

Each model covered ten cases, two per category. Qwen3.5 has four false approvals
and no false rejections against the frozen human reference; Qwen3 has twelve false
approvals and two false rejections. Qwen3.5 meets 80% on every dimension of this
small confirmation set; the comparator fails that numerical boundary on D1/D5.
These ten authored examples are excluded from assessed cohort measurements.

## Errors and semantic audit

All 120 public justifications were reviewed against the supplied cases, reference
context, rubric and frozen prompt. Human labels remain the comparison reference;
the audit below is assistant analysis, not substitute human scoring.

Qwen3.5's four disagreements are:

- C01 D3: it approves the API despite the incorrect `ListFields` return-type
  claim. V13 explicitly includes return types in D3, so this is an API false approval.
- C01 D5: it credits the unchanged field-inventory objective; the human reference
  fails the answer's contextual alignment. Preserve the disagreement and the
  distinction between task context and an incorrect implementation.
- C07 D1: it approves completeness because stages are listed even while its D3
  correctly identifies an invalid property access. This contradicts V13's
  requirement that the reader can finish the requested operation.
- C08 D5: it credits the stated door-instance objective despite the procedure
  counting types. This is a second context-boundary disagreement.

One matching Qwen3.5 explanation also needs qualification: C04 D5 treats a wrong
failure-handling rule as a changed objective, unlike its C01/C08 distinction.
C04 D1 calls the success-check stage omitted although an incorrect branch is
present. These are retained reasoning limitations; matching labels are not proof
that every explanation applies the anchors consistently.

The comparator additionally approves the invalid field join, exception masking
and false field-name tip; approves the failed-step reporting procedure; misses
the altered ODE's D5 failure; approves the invalid FreeCAD property; approves the
wrong Revit filter; and rejects the OpenSees scope statement despite an explicit
design-approval disclaimer. Its C07 D6 rejection matches the human rating but
misses the decisive false capitalization claim. Full public explanations and
per-criterion audit dispositions remain in the external evidence.

The earlier development screen's zero safety/API false approvals **did not carry
over**: this confirmation has one API false approval. Selection must acknowledge
that residual error. The proposed next step measures assessed agreement; it does
not certify the model for unattended engineering decisions.

## Execution and denominator accounting

| Measure | Qwen3.5 | Qwen3 |
| --- | ---: | ---: |
| Recorded starts | 12 | 10 |
| Valid initial attempts / selected cases | 9/10 | 10/10 |
| Valid final judgments | 10/10 | 10/10 |
| Retry starts | 2 | 0 |
| Recorded request time, including failures | 1,248.5 s | 111.2 s |

There were **22 new starts**, bringing the cumulative development/confirmation
count to **212**. Two connection failures followed an external server shutdown
confirmed by Chad. A recorded [recovery amendment](CONFIRMATION-TRANSPORT.md#recorded-external-interruption-amendment--november-15-2026)
allowed one third attempt of C07 within the unchanged forty-start total limit.
All six prior valid judgments and both failures remain intact. No unknown outcomes,
truncated completions or further transport failures remain. Initial validity was
not rewritten as 100% after recovery.

The original comparator preflight rejected its native template before inference.
A separate zero-generation inspection and validator correction recognized the
pinned Qwen3 template without changing model inputs, server flags or settings.
Original, recovery and comparator code snapshots and logs are all retained.
All twenty valid responses have nonempty reasoning metadata; only public
justifications were used for the semantic audit. Native templates differ and
fixed execution order/cache history prevent interpreting timing as a controlled
hardware benchmark.

Both phases used V13, identical message bodies, JSON mode, temperature 0.1,
8192 output tokens, a 300-second timeout, build b12110-cd959bae9, context 16384
and one slot. Shared model family, authored challenge selection, conceptual overlap,
small sample size, the interruption and the validation correction limit inference.
No prompt tuning on the confirmation judgments occurred.

## Evidence and verification

The frozen human submission SHA-256 is
`68a02de544634f34ec78f4616a95cabcf2f3321695e50b2274f53251fec009d9`;
the human-reference identity is
`b8668b09e762b60599fd578ec673b07ab6f3362c7008f192ee82b5fd0341f17b`.
All submitted ratings, added pass reasons and comments are preserved.

Final archive: `qualification/MP1-QWEN35-CONFIRMATION-RETURN.zip`, SHA-256
`f03e63c70dc8fb4e5c019e967cca92a971c0376a15e80cbb1ab12e45aad8f3ba`.
NAS: `\\192.168.0.55\aia\Handoff\P1-03\operator\MP1-QWEN35-CONFIRMATION-RETURN.zip`.
Audit: `qualification/confirmation-return-audit-20261116/complete-report/`.
The original 153 frozen files, 140 recovery files and 138 comparator-fix files
verify. Full ledger replay reproduces the counts and amendment.

Implementation revisions: `24ead7b` (review intake), `a1b7607` (bounded external
interruption recovery), `ed9c8a4` (native-template validation). **419 locked WSL
tests pass**, with Ruff checks and launcher syntax validation. Raw evidence remains
outside Git. M4 assessed calibration, M5 correction/comparison and M6 acceptance
remain incomplete.
