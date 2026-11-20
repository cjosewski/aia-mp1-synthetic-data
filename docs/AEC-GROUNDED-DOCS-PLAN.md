# AEC documentation and field grounding revision

November 20, 2026. Chad's “Go on next” authorizes the next improvement after the
[completed online-documentation comparison](AEC-ONLINE-DOCS-RESULTS.md). This
revision is a separate development method. It does not revise historical scores,
human labels, the rubric or assessed readiness.

## Current outcome

The November 20 bounded attempt stopped after one valid lookup and three page
opens, before the first judgment. The actual schema-bearing judgment request
needed 16,594 tokens against 16,384 available. There are zero validated judgments
across ten selected cases and no agreement report. See the
[stopped-attempt result and tokenizer diagnostic](AEC-GROUNDED-DOCS-RESULTS.md).

Preserve grounded run 001; do not resume it with changed code or inputs. The
next task at that checkpoint was a compact display projection in a separately
frozen follow-up and preflight under the original limits. The subsequent
[compact preparation and preflight](AEC-COMPACT-DOCS-PREFLIGHT.md) implemented
that display change without inference. Broader pressure checks still failed
for that compact protocol. The later [wire preflight](AEC-WIRE-DOCS-PREFLIGHT.md)
fits the measured cases under unchanged limits, while retaining exact checks
for every future actual request. No new judgment has been measured.

## Problem and hypothesis

The previous method opened 29 pages but missed twelve requested search strings.
On a miss it supplied the opening of the page. Its judgments also credited
candidate fields with instructions found elsewhere, overlooked task obligations,
and made API claims unsupported by their cited passages. Agreement was 2, 3, 9,
9, 8 and 8 out of ten for D1–D6.

The hypothesis is that bounded, explicit document searches and visible evidence
locations will make those errors easier for the judge to detect and for an
independent reviewer to audit. This is a combined method revision; a later paired
comparison cannot isolate the contribution of each change or estimate sampling
variation from one run.

## Implemented contract

The reader accepts one to three pages and one to three separate literal anchors
per page. The model chooses pages by their documented purpose and searches
individual symbols separately. It receives bounded excerpts around matches,
explicit unmatched anchors and edition information. A failed search supplies no
unrelated opening passage and is not evidence that an API is absent. Publisher
allowlists, pinned editions, request timeouts and page-size limits remain bounded.
The excerpt budget stays at 2,300 characters per page.

The scorer receives the original task, candidate, source context and six rubric
anchors. Application-supplied IDs identify original candidate fields/list entries
and the exact excerpts shown. Candidate evidence for D2 is confined to
`safety_info`; each original tip must be accounted for. Task checks describe the
model's interpretation of the existing brief, without turning a new checklist into
new requirements. Context checks compare the candidate with that original task.

The earlier quote-heavy experiments had format failures. This revision uses IDs
and optional short documentation quotations to avoid repeated transcription.
Task and context checks still require short exact spans from the original task.
A quote, when present, must resolve to the identified text. Validation establishes location
and structural coverage only. It does not establish truth, semantic support,
complete task interpretation or agreement with a human reviewer. The six binary
decisions remain model judgments under the original anchors.

## Comparison and preservation

Use the same ten development cases, two per AEC category, the original source-aware
control, frozen human reference and Qwen settings. Preserve the completed online
run and its interrupted predecessor. The new run is
`api-development-qwen-grounded-docs-001`, linked to an exact snapshot of
`api-development-qwen-online-docs-002`. New modules preserve the existing runner
and reader so that completed run 002 remains replayable with its pinned code.

The proposed live allocation is one lookup and one scoring attempt per case:
twenty model starts and at most thirty page requests. A malformed return,
invalid evidence reference or unknown outcome consumes its allocation. Do not
repair, retry or convert it to default binary scores. Preserve all raw attempts.
Human ratings and audit conclusions are excluded from model requests. No
case-specific answer keys or hand-selected verdicts are added.

Report complete coverage, each D1–D6 count, and corrections and regressions against
both the original control and completed online method. Promotion still requires
at least 8/10 in every dimension and an independent explanation audit. This is
development on previously examined items; it does not establish fresh assessed
calibration. The separate baseline remains 12, 15, 12, 17, 13 and 11 of twenty.

## Verification and execution boundary

Verify the reader with synthetic pages, including separated matches, Unicode,
missing anchors, disallowed URLs and transport failures. Verify evidence IDs,
field ownership, every-tip coverage, optional quotes, immutable lineage, unknown
attempts, malformed returns, no label leakage and offline replay. Run the locked
test suite and independent code review before freezing the new inputs.

Preparation makes no model requests. A live comparison needs a fresh verified
deployment, exact wire/context preflight and the frozen protocol. The previous
project server and tunnel were stopped. Software tests or a prepared packet are
not evidence of improved model agreement.

## Historical operator commands

The following command prepared grounded run 001 in the approved native Fedora
environment. It records the completed preparation; it is not an instruction to
prepare or restart that frozen run:

```bash
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
export AIA_MP1_DOMAIN=aec-course
uv run --locked python tools/screen_aec_grounded_docs.py prepare \
  --run-id api-development-qwen-grounded-docs-001 \
  --predecessor api-development-qwen-online-docs-002
```

The prepared protocol binds the original requests, both comparison baselines,
frozen human reference, reader menu, schemas and implementation hashes. Preserve
every predecessor file. Changes to a prepared method need a separately identified
run; do not rewrite its protocol or previously captured attempts.

The execution contract required `deployment.json` in the new run with freshly
verified model shard hashes, model path, build and reasoning budget. It must also
bind `protocol_sha256`, timezone-aware `launched_at` and `verified_at`, and
`maximum_server_lifetime_seconds` no greater than 14,400. The verified time cannot
precede launch or lie in the future. The lifetime is measured from launch, not
receipt creation. The runner checks expiry before each new model start and never
starts a service itself.

For the stopped attempt, `score` replaced `prepare` in the command above.
The runner checks the actual Instructor request, including the response schema, against
the original 16,384-token context, 8,192-token output limit and 1,200-token margin.
An oversized request stops before its model start. These limits are not silently
changed to accommodate the new contract. The first real judgment request failed this guard. Any separately frozen
follow-up still needs actual tokenizer preflight.

Every page allocation has a durable start before HTTP reads. Interrupted fetches
consume those requested pages and cannot silently be reissued. Invalid model
output or invalid evidence locations retain their start and raw return; an
incomplete receipt records the ten selected cases as the denominator. Neither a
missing passage nor a successful structural check determines a binary grade.

The `replay` stage checks saved evidence offline and the recorded deployment
identity without requiring its historical service to remain unexpired. This
partial run has no saved judgment to replay and cannot produce a completed
comparison report. After confirmed shutdown, its offline replay exited 1 at
that expected stop; the retained lookup/pages verified and all 46 run files
remained unchanged.

## Historical November 20 preparation checkpoint

The full locked suite passed **964 tests**, including 81 new tests. Lint,
formatting and independent implementation review passed. The real ten-case
packet was prepared twice with identical results and, at that checkpoint,
contained only the protocol, lookup requests and review checkpoint. It then had
**zero model starts**, no deployment receipt and no measured agreement.

Protocol SHA-256:
`468021790bcb38601d64a400051379470f7a032bb484d6d85029858f190de684`.
The protocol binds 18 implementation files and all 132 completed predecessor
files. The frozen reference remains
`64f0296b39c266dbf18f51a7fc375d27dab9b7adb88c338da4e5333407e829d3`.
The four earlier pinned source files are unchanged, and the previous method's
offline replay still produces report
`67997b908f5df163d3200613bbce88ece91d873e134447cd438978ce6e90d867`.

A separate publisher-only preflight initially made five requests, one per category:
four returned matched excerpts, while the FreeCAD anchor missed and returned no
substitute text. A sixth request with different anchors matched that same pinned
source, giving five matched results and one miss across six total requests.
These are reader checks, not model-selected pages or
candidate assessments, and are outside the proposed comparison's allocations.

Private test logs, preflight traces and preparation verification are retained in
`../artifacts/evidence/.grounded-docs-preparation-20261120/`. The next task at that checkpoint was the
bounded live development comparison, including fresh deployment and actual
tokenizer preflight. Its stopped outcome is recorded above. Software verification does not establish that the new judge
will meet either the numerical or explanation gate.
