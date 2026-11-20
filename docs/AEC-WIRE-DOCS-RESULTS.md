# AEC wire comparison stopped on invalid judgment

November 20, 2026. The authorized `api-development-qwen-wire-docs-001` comparison
stopped on its first judgment return. Two model starts produced two returns:
one valid lookup and one judgment rejected by the canonical schema. There are
**zero validated judgments across ten selected cases**, no unknown model outcome
and no agreement report. The rejected object's binary values are not validated
ratings and must not be adopted or rescored.

## Observed execution

A fresh verified Mac deployment served the frozen protocol. The first lookup
selected three publisher pages; all opened with HTTP 200. Three of five anchors
matched and two missed, yielding 4,600 excerpt characters. This was a new lookup
allocation, separate from the retained-page diagnostics in the
[preparation record](AEC-WIRE-DOCS-PREFLIGHT.md).

The actual first judgment request passed the exact context check: **5,355 prompt
+ 8,192 output allowance + 1,200 reserve = 14,747 tokens**, within the unchanged
16,384-token context. It made one transport call and returned with finish reason
`stop`, reporting 5,436 completion tokens and 10,791 total tokens. The scoring
process exited 1 after 159.008 seconds. It did not retry the rejected judgment or
proceed to another case.

| Retained outcome | Count |
| --- | ---: |
| Model starts / raw returns | 2 / 2 |
| Valid lookup returns | 1 |
| Judgment starts / validated judgments | 1 / 0 |
| Selected judgment denominator | 10 |
| Page allocations / successful opens | 3 / 3 |
| Anchors matched / requested | 3 / 5 |
| Unknown model outcomes | 0 |

## Why the judgment was rejected

Canonical validation rejected the extra field `safety.note_detail`. The parsed
result is null, and the incomplete receipt retains zero validated judgments with
the fixed ten-case denominator. The raw return and its durable start remain
unchanged. No validator was weakened and no altered response was revalidated.

The pipeline stopped at schema validation, before grounding validation. An
independent read of the untouched raw object identified additional conformance
failures: all four `task_quote` fields across task checks and context bindings
were not exact spans from the original task. Three documentation references used
page-only IDs (`P1`, `P1`, `P3`) instead of shown passage IDs such as `P1.E1`.
One documentation quote also changed line breaks and matched no shown excerpt
exactly. These observations explain why removing the extra field would not establish a
valid grounded result; they are not a repair or a replacement judgment.

## Scoped explanation audit

The assistant's technical audit examined this rejected return without supplying
human labels or replacement ratings. It found candidate setup and a chosen CRS
promoted into task requirements, no identified correct candidate explanation of
tuple order, and an API conclusion that listed names without checking the
workspace/dataset distinction, the required field or the datatype-specific tip.
The tip conclusion also minimized a false field-order constraint. No ArcPy code
was executed; additional official sources were audit-only and unavailable to the
judge. A search miss does not establish API absence.

The audit preserves narrower sound claims about context-manager use, the
spatial-reference parameter, the lock symptom, software-exercise scope and useful
cleanup advice, with their documented qualifications. Safety evidence IDs stayed
within `safety_info`, and closing the cursor is inferable from the warning: this
was not a mechanical field-borrowing violation. The stated reconciliation
consequence remained unsupported for the proposed disposable memory dataset.
These qualified findings do not make the rejected return eligible for scoring.

## Shutdown, partial replay and preservation

The owned server and Fedora tunnel were stopped. The launcher recorded exit 0;
Mac port 8082 and Fedora port 18082 were confirmed closed. The native log recorded
two processing tasks, consistent with the two retained model starts and returns.

After shutdown, partial offline replay exited 1 at the same retained-response
validation rejection. All 44 run files were unchanged by that replay. It issued
no new model request and reproduced no completed report. This verifies the
preserved partial history, not completion of the comparison.

All 21 frozen source hashes and the 3/48/132-file compact/grounded/online ancestor
lineage matched. The **1,031 passing tests** belong to the preparation checkpoint;
executing code remained unchanged, and no new full-suite run was performed in
this execution round.

All 16,634 original transferred files (468,620,606 bytes) were rehashed unchanged.
At the replay checkpoint, the 227 additions comprised 132 completed-online files,
48 stopped-grounded files, three compact inputs and 44 wire-run files. The
44-file figure describes that checkpoint; later audit/completion receipts are
additional records.

## Private evidence

Run evidence remains outside Git under
`../artifacts/evidence/P1-03/aec-course/api-development-qwen-wire-docs-001/`.
Protocol SHA-256 remains
`c1456135128ed96240325f84e000880430ddba8efc527bd9bdd62f85958efc08`.
The fresh deployment SHA-256 is
`d5c3b65a4000c18bf17e26b884c76e5d807a179dd074b52c2efd92e0f99fead1`.
The run's `execution-completion.json` was added after the 44-file replay
checkpoint. It binds the audit, execution, cleanup and preservation receipts;
its SHA-256 is
`40ccfbdc394b9a258c6b0afdd3902bb65914b2dcf1f5f7ec0a059aad4e10aaba`.

The separate execution directory,
`../artifacts/evidence/.wire-docs-execution-20261120/`, retains
`score-process-exit.json`, `independent-execution-review.json`,
`cleanup-receipt.json` and `partial-replay-verification.json`.
`execution-verification.json` records the counts and frozen hashes;
`original-evidence-verification.json` owns the original-file preservation check.
Independent final execution review approved the retained partial history.
`explanation-audit.json` and `explanation-audit.md` retain the scoped technical
audit and its source/uncertainty qualifications; the JSON SHA-256 is
`dc9d94b6610cfdfee8164686a94e7f7873f405481202ed390892f7c9141c3c81`. The first case's
raw lookup/judgment returns, page trace, actual fit and incomplete receipt remain
with the run. Raw outputs, source passages and human labels are not published
in this repository.

## Decision and next task

Preserve wire run 001 without repairing, adopting, rescoring or retrying the
rejected return. At this execution checkpoint, the next task was to design a
separate revision for output-schema and evidence-reference conformance. The
subsequent [conformance design](AEC-CONFORMANCE-DESIGN.md) was implemented and
executed later on November 20. That trial validated 8 of 10 judgments and scored
0, 3, 7, 8, 6 and 4 of ten, failing the development gate; see the
[conformance result](AEC-CONFORMANCE-DOCS-RESULTS.md). Keep
canonical validators and the original rubric intact; do not turn partial raw
decisions into default grades.

No quality improvement or development agreement is established. The completed
online method remains **2, 3, 9, 9, 8 and 8 matches out of ten**, versus its
control's **3, 4, 8, 9, 8 and 8**. The separate assessed baseline remains
**12, 15, 12, 17, 13 and 11 out of twenty**, with only D4 meeting 16/20. M4 stays
open. Future development promotion still requires complete ten-case coverage,
at least 8/10 in every dimension and an independent explanation audit.
