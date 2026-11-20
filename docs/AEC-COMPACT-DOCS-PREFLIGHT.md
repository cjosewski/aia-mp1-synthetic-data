# AEC compact documentation preflight

November 20, 2026. The separate
`api-development-qwen-compact-docs-001` packet is prepared, with **zero model
starts, zero new publisher requests and no agreement report**. Its compact
presentation makes the exact previously blocked first judgment request fit.
Broader tokenizer checks still expose context failures. **The method is not ready
for a live comparison.** No inference, new labels or new scores were produced in
this round.

## What changed and what was preserved

The display projection removes normalized-text hashes and character counts,
search offsets, and excerpt offsets and redundant anchor lists from the model's
page display. It preserves all excerpt IDs and text, source URLs and editions,
requested claims and anchors, search outcomes and occurrence counts,
anchor-to-excerpt mappings, page status and search strategy. Saved full page
traces remain unchanged. Lossless JSON separators remove formatting whitespace
from the judgment user message while preserving its decoded values, including
Unicode and whitespace inside strings. Lookup requests are unchanged.

The original task, rubric, SELECT/FINAL instructions, schemas, candidate field
IDs and Qwen settings remain fixed. The original context is 16,384 tokens, with
8,192 reserved for output and a 1,200-token margin. A prospective comparison still
has at most twenty new model starts and thirty page requests, with one attempt
per stage; unknown or invalid attempts remain consumed.

Preparation ran twice with identical results. The new run contains only
`protocol.json`, `lookup-requests.json` and `review-checkpoint.json`. Its protocol
SHA-256 is
`82d431203ed6afcb7720f7f87a5b8917cd354940cd7c2bfd7869678a97d756e6`.
It pins 19 implementation files, all 48 files in stopped grounded run 001 and
all 132 files in completed online run 002. The stopped parent supplies no scored
baseline and none of its attempts is copied into the new allocation. Any later
paired comparison would use the original control and completed online run 002.

## Exact first-case measurement

The retained pages for `baseline-001-b04-item-0006` supplied diagnostic input to
the verified native tokenizer. The check did not adopt that lookup into the new
run or send a judgment request for inference.

| Presentation | Prompt tokens | Output | Reserve | Required | Result against 16,384 |
| --- | ---: | ---: | ---: | ---: | --- |
| Frozen grounded request | 7,202 | 8,192 | 1,200 | 16,594 | 210 over |
| Metadata-only diagnostic | 6,779 | 8,192 | 1,200 | 16,171 | 213 remaining |
| Compact projection and JSON | 6,590 | 8,192 | 1,200 | 15,982 | 402 remaining |

The final compact request saves 612 prompt tokens relative to the frozen grounded
request. Its exact schema-bearing wire SHA-256 is
`ff2ec6999b020688da81805ca27d513f669e395b260bdfb8a63618e9306e7761`.
The separate CLI preflight exited 0: all ten unchanged lookup requests fit, with
a maximum required size of 12,032 tokens, and the retained first-case judgment
reproduced the 15,982-token result. Those are **eleven measured requests**, not a
finding that ten future judgments fit.

## Broader pressure checks

A separate pressure check made 22 tokenizer measurements: the exact retained
first case, its metadata-only reference, ten envelopes using historical page
text, and ten synthetic three-page stress scenarios. These are distinct from
the eleven CLI checks above. Neither check made inference or publisher requests.

Six of the ten historical-text envelopes exceeded context. Three envelopes,
for cases `0006`, `0007` and `0005`, contain duplicate legacy URLs and would be
rejected by the new lookup schema; they are not admissible new lookup selections.
Among the remaining seven envelopes with admissible page selections, **three
exceeded context**. Even those envelopes use synthetic reader metadata and are
not actual future reader results.

All ten stress scenarios used three unique same-category pages with 2,300
characters per page. All ten exceeded context, requiring **16,924–17,929 tokens**.
Their repeated padding text, claims, anchors and statuses are synthetic. They
exercise request pressure; they are neither observed reader outputs nor a
universal token bound. The result shows that fitting the retained first case is
insufficient preparation for the full permitted input range. It does not predict
the pages a future lookup would choose or the model's agreement.

## Verification and private evidence

The full locked suite passed **977 tests**, including 13 new compact-runner tests.
Ruff passed and formatting checks covered 322 files. Independent implementation
review passed. Tests cover lossless projection, misses/errors, stopped-parent
lineage, a fresh attempt allocation, replay, invalid and unknown outcomes,
oversize guards, and preflight restricted to tokenizer routes without writes.

The private evidence directory is
`../artifacts/evidence/.compact-docs-preparation-20261120/`.
`pressure-preflight.json` and `pressure-scenarios.json` retain the diagnostic
measurements and synthetic inputs; `preflight.json` records the eleven CLI
checks. Test logs, repeated preparation logs and the separate runtime receipt
remain there. The prepared run itself contains no deployment, attempts or report.
Raw outputs, source passages and human labels remain outside Git.

The dedicated native server and Fedora tunnel were stopped after preflight;
the launcher recorded exit 0 and ports 8082/18082 were confirmed closed. The
native log contained zero processing-task lines, consistent with tokenizer-only
use. `cleanup-receipt.json` records the shutdown. All 16,634 original transferred
files (468,620,606 bytes) were rehashed unchanged. The 183 added files are exactly
132 completed-online files, 48 stopped-grounded files and the three compact
preparation files. The final preservation check also matched all 48 stopped-parent
files, 132 completed-baseline files and 18 earlier frozen source hashes.
`preparation-verification.json` binds the prepared packet, 977-test result and
source archive; the archive SHA-256 is
`a0dca7acf00c28803a3971d20be89572781b34970b31e99000b48a159a1aa338`.

## Commands used and next task

These commands record the completed preparation and read-only preflight. The
preflight needs a fresh verified tokenizer runtime and a protocol-bound receipt;
it does not start a service or authorize inference.

```bash
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
export AIA_MP1_DOMAIN=aec-course
uv run --locked python tools/screen_aec_compact_docs.py prepare \
  --run-id api-development-qwen-compact-docs-001 \
  --predecessor api-development-qwen-grounded-docs-001
uv run --locked python tools/screen_aec_compact_docs.py preflight \
  --run-id api-development-qwen-compact-docs-001 \
  --predecessor api-development-qwen-grounded-docs-001 \
  --preflight-receipt ../artifacts/evidence/.compact-docs-preparation-20261120/runtime/preflight-runtime.json
```

Preserve the frozen compact packet and both predecessors. At this checkpoint,
the next task was a separate context-budget solution preserving the rubric,
evidence and declared budgets. The subsequent [wire preflight](AEC-WIRE-DOCS-PREFLIGHT.md)
now records that separate revision and its measured fit, without inference.
Do not score or rewrite this compact protocol, automatically enlarge context or
reduce the output allowance.

The prior online method remains at **2, 3, 9, 9, 8 and 8 matches out of ten**
versus its control's **3, 4, 8, 9, 8 and 8**. The assessed baseline remains
**12, 15, 12, 17, 13 and 11 out of twenty**; only D4 meets 16/20. M4 stays open.
Tokenizer fit and software verification establish no new judgment-quality result.
