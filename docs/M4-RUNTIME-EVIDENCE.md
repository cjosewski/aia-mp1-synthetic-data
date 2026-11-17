# M4 retained runtime evidence

November 17, 2026. The separately versioned `recovery-evidence-v3` implementation
adds empirical observations without treating them as API documentation. Ten
OpenSees preparation checks now have applicable runtime bindings. The current
packet has **358 checks, 325 prepared questions, 33 remaining holds, one empty
binding and 43 reasoning notes**. Prepared questions are not verified facts or
rubric passes. No new model measurement or human rating was produced.

## Implementation and boundaries

`recovery_runtime.py` validates snapshot-relative artifact paths and hashes for
the pre-execution protocol, script, dependency lock, identity records, raw process
captures and explicit reuse receipt. It rejects missing or reordered scheduled
cases, duplicate records, changed bytes, path escapes and incomplete captures.
Original stdout/stderr strings become separately identified `P.*` passages;
citations must reproduce exact text and remain within the check's bindings.

The verifier and scorer receive the complete retained experiment, including all
scheduled captures, author attribution and limitations. A single matching
counterexample may refute a necessary-failure assertion; it cannot establish a
universal API contract. Any unknown or timed-out case leaves that record unresolved
for scoring, even if a check cites a different successful case. Hashes establish
retention, not scientific validity. Case identifiers retain their original casing.

Every empirical record requires an explicit applicability audit covering version
and build, scheduled-case completeness, script/output correspondence, qualifiers
and limitations. Older fact audits cannot unlock this stage. The existing score
audit remains necessary, and any resulting judgment is still development-only and
ineligible for assessed calibration. Source-role separation and all six rubric
anchors remain unchanged. No live transport was added.

The original v1/v2 schemas and fingerprints are preserved. Eight cases remain v2;
two structural cases use v3. New [verifier v4](../prompts/recovery-facts-v4.md) and
[scorer v3](../prompts/recovery-score-v3.md) prompts are unmeasured drafts; older
prompts remain intact.

## Concrete migration

| Case suffix | Runtime-bound checks | Scope |
| --- | --- | --- |
| b02-item-0008 | K0008, K0009, K0010, K0014, K0019, K0020, K0021 | Recorded extra-flag constraints and analysis outcomes |
| b02-item-0008 | K0027, K0028 | Recorded duplicate-constraint failure phase and diagnostic |
| b01-item-0013 | K0012 | Recorded negative-area initialization and analysis outcome |

All check IDs, subjects, questions, dimensions, parent text and existing reasoning
notes remain unchanged. The ten reclassifications change evidence kind, bindings
and rationale in a separate revision. No accepting real-item fact audit, verifier
response, score or score audit was created. The complete original ten-case probe
is retained, including the environment incident and later native-identity capture.
The original research-only receipt remains unchanged; a new v3 reuse receipt
explicitly records admission with those limitations.

The first preparation attempt stopped because a case identifier contained an
uppercase `E`. It remains retained as incomplete. The naming restriction was
corrected, a regression test added, and `packet-runtime-r1` created separately.
No experiment or model call was rerun and no original identifier was renamed.

## Verification and remaining work

The final full suite passed **638 tests in 114.17 seconds** in locked WSL Ubuntu
with the analysis extra and optional PDF renderer. A subsequent focused run passed
**46 runtime tests**, including an added complete scoring-CLI/audit test. Thus 639
distinct tests were exercised successfully across the two runs. Ruff and diff
checks pass. These tests establish implementation behavior, not model quality.

All ten new packets replay, the preceding real v2 packets replay unchanged, and
**966 entries across six earlier seals** verify. Evidence is outside Git at
`artifacts/evidence/P1-03/qualification/m4-recovery-runtime-v3-20261117/`.
The current packet is `packet-runtime-r1`; the incomplete `packet-runtime` is
historical, not an executable replacement.

| Category | Remaining preparation holds |
| --- | ---: |
| GIS | 11 |
| AEC | 12 |
| Structural | 4 |
| CAD | 1 |
| Simulation | 5 |
| **Total** | **33** |

The remaining structural questions concern the unit convention/enforcement and
the proposed node-command inspection. The current experiment does not establish
those full contracts, so they were not cleared. Documentary gaps in other
categories remain separately recorded.

Next, resolve those shared documentary questions and review the empirical
applicability before transport/token preflight. Current serialized verifier views
range from 40,467 to 130,361 UTF-8 bytes; these are **not token counts or proof of
context fit**. Complete prompt/schema/runtime token preflight is still required.

Execution remains disabled. No Mac/Herd changes, no model calls and no new scores;
cumulative starts remain 388. The twenty-start development trial is unallocated
and unstarted, three assessed allocations remain consumed, and M5 is preserved.
M4 still fails the original 80%-per-dimension requirement in D1 and D6.
