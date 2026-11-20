# AEC documentation wire preflight

November 20, 2026. The separate wire revision fits **all 21 measured judgment
inputs** under the original 16,384-token context, 8,192-token output allowance
and 1,200-token reserve. The exact retained first case requires 14,703 tokens;
the largest synthetic stress case requires 16,374, leaving only ten tokens beyond
the existing reserve. These are measured inputs, not a universal bound on future
requests. **No inference, new publisher requests, human labels or scores were
produced in this round.**

## Subsequent execution status

This page preserves the preparation and tokenizer-only checkpoint. The later
[authorized comparison](AEC-WIRE-DOCS-RESULTS.md) made one lookup and one judgment
call, then stopped because the judgment violated the canonical schema. Its actual
request fit, but zero judgments validated across ten selected cases. Preserve
the frozen run and rejected return. At that checkpoint the next task was a
separate conformance design, not resuming this trial or adopting raw decisions.
That design was later implemented and executed; see the
[conformance result](AEC-CONFORMANCE-DOCS-RESULTS.md).

## What the representation changes

The revision builds on the compact page display and preserves all substantive
task, candidate, reference, documentation and rubric text. It makes three
structural changes to the model request:

- Page, search and excerpt tables share column names. Search anchor indices refer
  to each page's unchanged requested anchors; explicit URL references avoid
  repeating a request URL already present on that page. Identical common metadata
  is shared. The decoder restores every original value, including ordered arrays,
  passage IDs and text, missed searches, error fields, nulls and absent fields.
- The displayed response schema shares identical property schemas and uses short
  local definition names. Expanding the references reproduces the original
  constraints **and every annotation**, including titles. Unsupported reference
  structures are rejected. Schema JSON is serialized without indentation.
- Only whitespace outside values is removed from the original rubric JSON.
  Every rubric value and anchor string, the surrounding instructions, and the
  scoring criteria remain unchanged. An explicit table legend is included in
  every measured judgment request.

The canonical Pydantic response model and evidence-location validation are
unchanged. Evidence checks use the canonical page objects, not table cells.
Lookup requests are unchanged. The model still makes the six independent binary
decisions; reversible encoding and successful parsing do not certify semantic
support or judgment quality.

A guarded transport allows one dispatch only, verifies the original Instructor
request against its expected body and forwards exactly the transformed request
that was preflighted. Durable starts retain the original and transmitted wires
and their hashes. Unknown outcomes, malformed returns and invalid grounding
remain consumed attempts. Existing frozen implementations and evidence are
preserved in their separate runs.

## Frozen packet

`api-development-qwen-wire-docs-001` was prepared twice with identical results.
At preparation it contained only three input files: `protocol.json`, `lookup-requests.json` and
`review-checkpoint.json`. Its protocol SHA-256 is
`c1456135128ed96240325f84e000880430ddba8efc527bd9bdd62f85958efc08`.
It pins 21 source files, its compact parent's three files, the stopped grounded
ancestor's 48 files and the completed online baseline's 132 files. No prior lookup
or judgment is adopted into the new run's attempt allocation. The original
control and completed online method remain the two scored comparison baselines.

## Native tokenizer measurements

The final diagnostic measured the exact retained grounded first case, ten
historical-text synthetic envelopes and ten synthetic three-page stress inputs.
The actual runner's constructed wires matched all 21 native diagnostic wires
exactly in the subsequent offline comparison.

| Judgment input | Earlier compact representation | Final wire representation | Result |
| --- | ---: | ---: | --- |
| Exact retained first case | 15,982 required | 14,703 required; 5,311 prompt | Fits; 1,681 remaining |
| Largest synthetic stress case | 17,929 required | 16,374 required | Fits; 10 remaining |

Both rows retain 8,192 output tokens and the 1,200-token reserve. The first-case
transmitted-wire SHA-256 is
`f0de570375efa692839f78a79ee7be20615ddea9dfc282f2903ef42f3eec45b5`.

The final CLI preflight also exited 0. Its eleven checks covered all ten unchanged
lookup requests (maximum 12,032 required tokens) and the retained first judgment,
which reproduced the exact 14,703-token wire above. These checks are separate
from the 21 judgment diagnostics and allocate no new model or page attempts.

All ten historical-text envelopes fit. Three, for cases `0006`, `0007` and `0005`,
contain duplicate legacy page URLs and remain inadmissible under the new lookup
schema. Therefore seven have admissible page selections. All are synthetic
reader envelopes using historical text, not observed future reader outputs.

All ten stress scenarios fit, requiring 15,435–16,374 tokens. They use three
unique same-category pages with 2,300 characters per page, synthetic repeated
padding, claims, anchors and search statuses. They test context pressure; they do not establish a universal
token bound or predict a future lookup's selection. The final ten-token margin
beyond the unchanged reserve is small. Every actual request still needs exact
schema-bearing preflight before its durable model start; an oversized request
must stop rather than change the declared budgets.

## Evidence and verification

Private diagnostics are retained in
`../artifacts/evidence/.wire-docs-preparation-20261120/`.
`factored-table-preflight.json` records the final native measurements and
`factored-table-wires.json` retains their exact requests. Intermediate diagnostic
variants remain preserved. No intermediate variant was submitted for inference.
Raw source passages and human labels remain outside Git.

The full locked suite passed **1,031 tests**, including 40 new helper tests and
14 new runner tests. Ruff passed and formatting checks covered 328 files.
Independent implementation review and review of the 21 native wires passed.
The helper tests cover typed round trips, missing versus null
values, errors, misses, aliases, ordering, literal marker-like data, unsupported
schema references, unchanged annotations and rubric values, exact wire guards,
raw returns, invalid responses and unknown transport outcomes. These checks
establish software behavior, not model agreement.

The dedicated tokenizer server and Fedora tunnel were stopped after the checks.
The launcher recorded exit 0, the owned server was confirmed stopped, and Mac
8082/Fedora 18082 were closed. The native log contained zero processing-task
lines. `cleanup-receipt.json` records these observations.

All 16,634 original transferred files (468,620,606 bytes) rehashed unchanged.
The 186 additions are exactly 132 completed-online files, 48 stopped-grounded
files, three compact inputs and three wire inputs. All 19 prior source hashes
and the 3/48/132-file predecessor lineage matched.
`original-evidence-verification.json` records the original-file and 186-addition
checks. `preparation-verification.json` binds the source hashes, lineage, packet,
software results and archive. The source archive SHA-256 is
`70a18ef0b171b9f1cf10a46e0684e57e144a66d2edfb3b0fa17ac88b82cbcd53`.

The completed preparation and tokenizer-only check used these historical
commands in the approved Fedora environment; they are not instructions to
restart the now-stopped trial:

```bash
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
export AIA_MP1_DOMAIN=aec-course
uv run --locked python tools/screen_aec_wire_docs.py prepare \
  --run-id api-development-qwen-wire-docs-001 \
  --predecessor api-development-qwen-compact-docs-001
uv run --locked python tools/screen_aec_wire_docs.py preflight \
  --run-id api-development-qwen-wire-docs-001 \
  --predecessor api-development-qwen-compact-docs-001 \
  --preflight-receipt ../artifacts/evidence/.wire-docs-preparation-20261120/runtime/preflight-runtime.json
```

That tokenizer runtime is now stopped. A future check or bounded comparison needs
a fresh verified runtime and receipt; the commands above do not start a service.

## Historical next-task boundary

With software and packet verification complete, the next task at that checkpoint
was a separate ten-case development comparison with a fresh verified Mac runtime
and exact preflight of every actual request. That attempt subsequently stopped
on its first invalid judgment, as linked above. Keep one lookup and one judgment attempt
per case: at most twenty model starts and thirty page requests. No repair retry
or default verdict may replace an invalid or unknown outcome. Preserve the
prepared packet and all predecessors; presentation changes require another
separately frozen protocol.

The development gate remains complete coverage and at least **8/10 matches in
every D1–D6 dimension**, plus an independent explanation audit. The exact context
checks permit testing the method; they do not demonstrate that it meets either
gate. The subsequent attempt produced no validated judgment or agreement report.

The completed online method remains **2, 3, 9, 9, 8 and 8 matches out of ten**,
versus its original control's **3, 4, 8, 9, 8 and 8**. The separate assessed
baseline remains **12, 15, 12, 17, 13 and 11 out of twenty**, with only D4 meeting
16/20. M4 remains open; no human decisions or historical scores changed.
