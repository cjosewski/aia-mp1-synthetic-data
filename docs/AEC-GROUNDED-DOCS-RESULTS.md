# AEC grounded documentation attempt

November 20, 2026. The separate development run
`api-development-qwen-grounded-docs-001` stopped at its context guard before the
first judgment. One lookup returned a valid page selection and three requested
pages opened. There were **zero judgment starts and zero validated judgments
across ten selected cases**. No agreement report was produced. This attempt does
not measure whether the grounding revision improves the model's decisions.

## Where the attempt stopped

The method retained the same ten development answers, human reference, original
source-aware control and Qwen settings. Its protocol pins the completed online
comparison as its predecessor. The [method and preparation record](AEC-GROUNDED-DOCS-PLAN.md)
describe the new literal-anchor reader and structured field attribution.

On the first case, `baseline-001-b04-item-0006`, the lookup fit the original context
and returned valid structured output. Its three pages contained seven requested
anchors: five matched and two missed, with 4,687 excerpt characters retained.
After those publisher pages opened, the
runner measured the actual schema-bearing judgment request with the verified
server's tokenizer. The request exceeded the unchanged limit:

| Request | Prompt | Output allowance | Reserve | Required | Context | Fits |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Frozen judgment request | 7,202 | 8,192 | 1,200 | 16,594 | 16,384 | No; 210 over |
| Diagnostic compact display | 6,779 | 8,192 | 1,200 | 16,171 | 16,384 | Yes; 213 remaining |

The scoring command exited with status 1 before writing a judgment start or
sending that request for inference. Its incomplete receipt records the ten-case
denominator, zero validated judgments and null judgment start/return hashes.
The lookup return, page allocation, page results and failed fit remain preserved.
The twenty-model-start and thirty-page-request limits were not expanded; neither
the output allowance nor the reserve was reduced.

## What the diagnostic establishes

A separate, read-only tokenizer diagnostic removed display metadata from the
first case's proposed judgment request: normalized-text hashes and character
counts, search offsets, and excerpt offsets and redundant anchor lists. It kept
every excerpt ID and text, source URL and edition, requested claim and anchors,
search outcome and occurrence count, anchor-to-excerpt mapping, page status and
search strategy. The full page trace was unchanged.

That display variant saved 423 prompt tokens and fit **this observed request**.
It was neither submitted for inference nor adopted into the frozen run. Other
cases were not measured, and no improvement in judgment validity or agreement
can be inferred from token counts. The result supports testing a compact display
projection in a separately frozen follow-up; it does not establish that all ten
cases will fit.

## Shutdown and partial offline verification

The dedicated Mac server and Fedora tunnel were stopped; ports 8082 and 18082
were confirmed closed. The server launcher recorded exit 0. After shutdown,
offline replay verified the retained lookup and page results, then exited 1 as
expected because the judgment had never started. All 46 run files were unchanged
by that check. This is a verified partial history, not reproduction of a completed
agreement report. No missing request was dispatched and no scores were invented.

The run's `cleanup-receipt.json` and the separate execution directory's
`partial-replay-verification.json` retain those checks.

## Evidence and prior results

The run evidence is private, outside Git, under
`../artifacts/evidence/P1-03/aec-course/api-development-qwen-grounded-docs-001/`.
Its protocol SHA-256 remains
`468021790bcb38601d64a400051379470f7a032bb484d6d85029858f190de684`.
The first case's `-grounded_judgment-fit.json` and
`-grounded_judgment-incomplete.json` record the stop. Deployment and execution
receipts bind the runtime used for the attempt. The deployment SHA-256 is
`f0725af27eaa488fff05f6119cd6536227a46102b986db4153f0f1845527fe0e`. The diagnostic is separate at
`../artifacts/evidence/.grounded-docs-execution-20261120/context-diagnostic.json`.
Raw model outputs, page traces and human labels remain outside Git.
The completion receipt binds the stopped execution, diagnostic, partial replay,
cleanup and independent accounting. Its SHA-256 is
`6380dd0dc9814aa4242695eff30183fbfedbb738d17fa9bdf431a83d26836b88`.
After the attempt, all 16,634 original transferred files (468,620,606 bytes), all
132 predecessor files and all 18 frozen source hashes were reverified unchanged.

The preparation checkpoint remains **964 passing locked tests**, including 81
new reader, grounding and runner tests, with independent implementation review.
Those checks established software behavior; the real tokenizer exposed this
request-size limit during execution.

The completed online method still has **2, 3, 9, 9, 8 and 8 matches out of ten**
for D1–D6, versus **3, 4, 8, 9, 8 and 8** for its control. Its numerical and
explanation gates failed. The separate assessed baseline remains **12, 15, 12,
17, 13 and 11 out of twenty**, with only D4 meeting 16/20. M4 remains open.
No scores or human labels were replaced by this stopped attempt.

## Decision and next task

Preserve frozen grounded run 001 and do not resume it with changed code or
presentation. At that checkpoint, the next task was a separately frozen compact
display projection and schema-bearing preflight under the same context, output
and reserve limits. The [subsequent compact preparation and preflight](AEC-COMPACT-DOCS-PREFLIGHT.md)
implemented that display revision without inference. Its broader pressure
checks still failed. The subsequent [wire preflight](AEC-WIRE-DOCS-PREFLIGHT.md)
fits the measured inputs under unchanged limits, but every future request still
needs exact context checks and no new agreement is established. Generator correction and assessed judging remain downstream of
calibration.
