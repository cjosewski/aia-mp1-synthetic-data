# Judge qualification — November 13 checkpoint

**Latest:** [V12](JUDGE-V12-PRESENTATION.md#measured-result) completed ten valid
first attempts, matching 53/60 with two false approvals and five false rejections.
Formatting did not resolve context or evidence-reading defects. Development
starts total **149**. Next acquire and verify the pinned [Qwen3.5 candidate](QWEN35-CANDIDATE.md)
before a separate bounded screen. No qualification or assessed run is claimed.

Previous result: [V11](JUDGE-V11-ISOLATED.md#measured-result) completed all twenty
independent stage calls, composing ten judgments at 55/60. D5 remains 6/10 and
D2 introduces one false approval. Neither valid formatting nor stage separation
resolved the semantic errors. Cumulative starts are **139**; full frozen-code
replay and NAS copies are verified, and the server is stopped. Next test
[input presentation alone](JUDGE-V12-PRESENTATION.md) with the exact V9 prompt.

Previous canonical checkpoint: [V9R1](JUDGE-V9-CANONICAL.md#measured-development-result) scores 56/60
with four D5 false rejections. [V10](JUDGE-V10-CANONICAL.md#measured-result) reaches
80% in every dimension but regresses to 53/60 with six false approvals, including
an API defect. Neither advances. Both GPT-OSS-120B high-effort runs complete all ten
cases on first attempts; their full returns/audits are retained and the Mac server
is stopped. Cumulative development starts are **119**. Next isolate D5 scoring
from the other five anchors under a new bounded protocol. Frozen human ratings,
assessed thresholds and production judge defaults remain unchanged.

The [analysis tools](ANALYSIS-RUNBOOK.md) now generate verified comparisons, five
chart/table pairs and local evidence exports. The preliminary baseline reproduces
74/120 human criterion passes and four all-six passes, without inventing the fifty
missing population judgments or a corrected cohort.

## Earlier V7–V8.1 checkpoint

The fixed V7 screens now compare three candidates: **GPT-OSS-120B 23/30 agreement,
GPT-OSS-20B 27/30, and Llama 23/30**, on the same five known cases. Every response
was accepted on its first attempt, but all three models approve an API defect.
None qualifies, and no assessed judging has started. The subsequent
[source-grounded design](JUDGE-FACTCHECK-DESIGN.md) and two draft prompts are
prepared and implemented with a source bundle, Mac transport and paired reporting.
The [compact V8 comparison](JUDGE-FACTCHECK-DESIGN.md#9-compact-presentation-and-bounded-comparison)
passed preflight but stopped after three requests: one accepted control, one
schema-valid verifier response with invalid IDs/missing coverage, and a verifier
retry that exhausted its output allowance. Control covers 1/5 cases, treatment
0/5; no paired improvement is established. Cumulative starts are **95**. The
30-start allocation stopped under its two-failure rule; unused requests do not
authorize an automatic continuation. The subsequent [V8.1 revision](JUDGE-V81-VERIFIER.md#measured-result)
passes verifier ID/coverage checks on the first case, then stops on two scorer
format failures. Semantic audit also finds unsupported composite claims accepted
by the scorer. Four new starts bring the cumulative count to **99**; control
coverage remains 1/5, treatment 0/5, paired cases zero. Next strengthen atomic
evidence verification and scorer citation roles before another frozen experiment.

## GPT-OSS-120B with fixed V7

The [candidate protocol](GPTOSS120B-COMPARISON.md) records the selection basis,
capacity check, exact weights and predeclared ten-request ceiling. Slow/reset
downloads were recovered with bounded ranges; the complete 63,387,346,208-byte
file matched its published SHA-256 before loading. Acquisition logs are preserved
and temporary fragments were removed only after verification. The model remains
on the Mac. No runtime upgrade, Herd setting, system GPU limit or desktop control
was needed.

V7 messages, passage catalog, schema, validator, rubric and human reference stayed
identical. Both GPT-OSS models used MXFP4, and their recorded native chat-template
text and runtime digest matched. Mac, build, context 16,384, one slot, temperature
0.1, output limit 4,096 and timeout 300 seconds were unchanged. This remains a
single stochastic known-case screen, not proof of broad model superiority.

| Dimension / measure | GPT-OSS-120B | GPT-OSS-20B | Llama 70B |
| --- | ---: | ---: | ---: |
| D1 — Completeness | 3/5 | 5/5 | 3/5 |
| D2 — Safety | 4/5 | 5/5 | 4/5 |
| D3 — API realism | 4/5 | 4/5 | 4/5 |
| D4 — Scope | 5/5 | 5/5 | 5/5 |
| D5 — Context | 3/5 | 3/5 | 4/5 |
| D6 — Tips | 4/5 | 5/5 | 3/5 |
| Agreement | 23/30 (76.7%) | 27/30 (90%) | 23/30 (76.7%) |
| False approvals / rejections | 5 / 2 | 1 / 2 | 6 / 1 |

GPT-OSS-120B gains one match versus 20B (the Revit context) and loses five:
FreeCAD context, Revit completeness/safety/tips, and structural completeness.
It still approves the incorrect Revit API owner and rejects the clear structural
task context. D1/D5 are 60%, and safety/API false approvals remain. The declared
development advancement condition is not met.

The semantic audit inspected all thirty explanations and resolved passages.
The model correctly distinguishes Compound aggregation from Boolean union, but
approves the Revit null-guard-removal tip and treats familiar API names as valid
usage. It also counts the structural example's unsafe approval step as successful
completion while rejecting that same approval claim under D4. All requirement
citations use rubric anchors; no task/source passage is cited as the decisive
requirement, and all counterevidence lists are empty. More citations did not
establish reference checking. No human labels or historical scores changed.

All five first attempts passed; there were no retries, transport failures,
truncation, citation rejection or unknown outcomes. Total request time was 128.6
seconds (mean 25.7, range 22.9–29.2), with 1,726–2,204 completion tokens. These are
operational timings, not a hardware benchmark. Five of ten allocated requests
were used, bringing documented cumulative starts to 92. Preparation passed 288
offline tests, lint, formatting, shell syntax, fixed-contract hashes and archived
comparison checks. The independent audit validated raw projections, attempt
lineage, exact passages, coverage and all ten report rows.

Return `MP1-results-2026-11-13T224054628349+0000.zip` has SHA-256
`87b97107eaaf47179714346025072f255e7f91383012fa61403ce81952c2d099`.
Audit: `qualification/gptoss120b-v7-return-review-20261113/`.
Complete NAS archive:
`MP1-handoff/completed-runs/gptoss120b-v7-2026-11-13T224054628349+0000/`.
Candidate/acquisition provenance is separately archived under
`MP1-handoff/candidate-preparation/gptoss120b-20261113/`. The owned server stopped
before export; port 8081 had no listener afterward. The Mac working copy is retained.

Do not extend this screen or start assessed judging. Next design a separate
source-grounded claim-verification stage before rubric scoring, including API
ownership, actual hazards, tip correctness and independent context scoring.
This proposal needs its own frozen protocol and request budget; no implementation
benefit or new inference is claimed here. No additional human review is needed
now. Broader development, fresh blind confirmation and assessed calibration remain
required.

## Llama versus GPT-OSS with fixed V7

Chad's next “Go” authorized the [controlled comparison](JUDGE-MODEL-COMPARISON.md).
Llama was the previously owner-selected, locally available distinct judge
candidate. Its pinned Q4_K_M weights, served identity and native runtime
properties were verified against its earlier Mac receipt before requests. No
new model download, Herd change or desktop control was needed.

All five messages, passage catalogs, response schema and validation code are
byte-identical to GPT-OSS V7. The Mac, llama.cpp build, context 16,384, one slot,
temperature 0.1, output limit 4,096 and timeout 300 seconds are fixed. Model,
quantization and native embedded template differ. GPT-OSS's saved run is the
comparator; it was not rerun. Earlier prompt versions remain historical diagnostics.

| Dimension / measure | Llama V7 | GPT-OSS V7 |
| --- | ---: | ---: |
| D1 — Completeness | 3/5 | 5/5 |
| D2 — Safety | 4/5 | 5/5 |
| D3 — API realism | 4/5 | 4/5 |
| D4 — Scope | 5/5 | 5/5 |
| D5 — Context | 4/5 | 3/5 |
| D6 — Tips | 3/5 | 5/5 |
| Agreement | 23/30 (76.7%) | 27/30 (90%) |
| False approvals / rejections | 6 / 1 | 1 / 2 |
| First-attempt acceptance | 5/5 | 5/5 |

Llama gained one context match but lost five matches compared with GPT-OSS. It
approved the incorrect Compound/Boolean-union procedure and tip, and the Revit
procedure, ineffective safety coverage, wrong API owner and unsafe null-guard tip.
It still rejected the clear structural-approval context because the answer was
incorrect. D1 and D6 are 60%, and safety/API false approvals remain, so the
predeclared development advancement condition is not met.

All thirty explanations and resolved passages were reviewed. Llama cites more
individual fields, but often repeats a rubric anchor or accepts the candidate's
claim without checking it. Some matching failures also have misleading reasons:
the structural safety guarantee is described as generic caution, and the false
technical tip as generic encouragement. Four requirement citations use the task;
26 use rubric anchors, with no source passage cited as the requirement. No human
labels or historical scores were amended.

The run used five of ten allocated requests, without retries, transport failures,
truncation, invalid passages or unknown outcomes. Documented cumulative starts
are 87. Requests totaled 335.5 seconds (mean 67.1, range 59.8–82.2), with 367–439
completion tokens. These sequential durations are operational observations, not
a hardware benchmark. Preparation passed 288 offline tests, lint, formatting,
shell syntax and frozen-contract checks. The independent audit reproduced raw
projections, exact passage text, attempt lineage, coverage and all nine report rows.

Return `MP1-results-2026-11-13T211250375457+0000.zip` has SHA-256
`4198b4afd8c644fe3acc71ab9c180dfad7d5e83e91ca171d480eff66692585af`.
The external audit is `qualification/llama-v7-return-review-20261113/`.
The complete NAS archive is
`MP1-handoff/completed-runs/llama-v7-2026-11-13T211250375457+0000/`;
its verification receipt checks all frozen and returned files. The owned server
stopped before export, and port 8081 had no listener afterward. The Mac folder
remains preserved.

Do not extend this Llama screen or advance either model to assessed judging.
Keep V7 fixed and next prepare another distinct local candidate's availability,
identity, capacity requirements and selection basis before a new allocation.
No such candidate was selected or downloaded here. No additional human review
is needed now. A later promising result still needs broader development evidence,
fresh blind confirmation and assessed calibration.

## GPT-OSS judge-v7 supplied-passage results

Chad's "Go" authorized the [passage protocol](JUDGE-PASSAGE-PROTOCOL.md).
Application-generated IDs identify complete original candidate fields/list entries,
task/source text and rubric anchors. The model emits IDs and ratings; the application
checks their existence/roles and resolves them to frozen text. User messages add
only the deterministic passage index; underlying text and human references are
unchanged. The system instruction, input index and output contract changed together.

The same five cases, qualification-v1-01 through -05, cover all five categories.
Model weights, Mac runtime, context, slot count, temperature, output budget and
timeout remained fixed. All five responses passed schema and passage validation
on their first attempt, with no retries, transport failures, truncation or unknown
outcomes. Five of ten allocated requests were used; documented cumulative starts
are now 82. Total request time was 85.4 seconds (mean 17.1 seconds), with 1,409–2,266
completion tokens per response. Preparation passed 266 project and 22 portable
tests, lint, formatting, shell syntax, input/reference and package-integrity checks.

| Dimension / measure | V4, same five cases | V7, same five cases |
| --- | ---: | ---: |
| D1 — Completeness | 4/5 | 5/5 |
| D2 — Safety | 4/5 | 5/5 |
| D3 — API realism | 5/5 | 4/5 |
| D4 — Scope | 5/5 | 5/5 |
| D5 — Context | 3/5 | 3/5 |
| D6 — Tips | 5/5 | 5/5 |
| Agreement | 26/30 (86.7%) | 27/30 (90%) |
| False approvals | 2 | 1 |
| False rejections | 2 | 2 |

Two decisions gain agreement versus v4: the geometry-completion error and the
sheet-report safety defect. One regresses: the sheet API-owner defect is approved
because the method name exists, without checking its proposed owning object.
The two existing context false rejections persist. Historical ten-case scores
are not substituted for this five-case comparison.

All thirty explanations and their resolved passages were inspected. On the sheet
case, every dimension cites only the answer field as candidate evidence. Some
matching failure labels are justified by claiming that steps or tips are absent,
although the original record supplies them; the actual problem is their content.
Other matching judgments similarly describe incorrect guidance as missing or
repetitive rather than addressing the specific defect. All thirty requirement
citations point to rubric anchors, with no task/source passage cited as the decisive
requirement. Those IDs are structurally permitted, but do not independently ground
the technical claims. No human reference was amended during this audit.

Return `MP1-results-2026-11-13T204636583467+0000.zip` has SHA-256
`ba0aafbe1416f4cbd6a0aa86261c51e954b777a467c6d603f02d6b6c5099bd50`.
The external `qualification/gptoss-v7-return-review-20261113/` audit verifies the
frozen bundle/reference, original-text preservation and passage index, model/runtime,
five attempt lineages, raw evidence and canonical projections, exact resolved
text, coverage accounting and all eight report rows. Remote and received hashes
match. The owned server stopped before export and port 8081 had no listener
afterward. No desktop control or Herd settings changed. The complete NAS archive
is `MP1-handoff/completed-runs/gptoss-v7-2026-11-13T204636583467+0000/`.

Keep the measured passage format fixed and prepare a controlled candidate comparison
with verified local availability and a documented model-selection basis. The
remaining problem is judgment/evidence fidelity, not quote formatting. No new
candidate is selected or measured here. Do not advance to fresh blind confirmation
or assessed calibration on this five-case result; no further human review is needed
now. This single stochastic run does not establish repeatability or broad superiority.

## Prior v6 checkpoint

The v6 compact-citation feasibility check stopped after two output-contract
failures on the first of five selected cases. **Coverage is 0/5 and agreement is
undefined.** Both responses finished within the token limit; their quotes exceeded
the protocol's 160-character bound. No accepted judgment, quality improvement or
calibration result is claimed. Qualification and assessed judging remain pending.

## GPT-OSS judge-v6 compact-format results

Following Chad's "Go", the [compact protocol](JUDGE-COMPACT-PROTOCOL.md) introduced
a shared citation table, short path aliases and numeric references per dimension.
It removes repeated quote objects and the v5 search-declaration fields while
retaining exact-text, citation-role, strict-score and canonical-projection checks.
This changed the prompt and response schema together. It did not change the
rubric, adopted reviews, generator or assessed judge defaults.

The selection was frozen before inference: qualification-v1-01 through -05,
the first existing example in each of the five categories. User messages stayed
identical to their prior versions. Archived comparisons were independently
recomputed on these same five cases, with full ten-case results preserved.
The package passed 245 project and 22 portable tests, lint, formatting, shell
syntax, reference/input hashes and comparison-accounting checks.

| Measure | Observed result |
| --- | --- |
| New requests / ceiling | 2 / 10 |
| Initial items started | 1 / 5 |
| Initial schema-valid / citation-accepted | 0 / 1 started for both |
| Retry recoveries | 0 |
| Accepted / unresolved cases | 0 / 5; four never attempted |
| Criterion comparisons / agreement | 0 / undefined |
| Attempt 1 | 23.1 seconds; 2,574 completion tokens; finish `stop` |
| Attempt 2 | 20.9 seconds; 2,564 completion tokens; finish `stop` |
| Unknown outcomes | 0 |
| Documented cumulative starts | 77 |

Attempt 1 supplied three quotes longer than 160 characters (181, 198 and 194);
attempt 2 supplied two (198 and 194). Both raw responses were retained with
validation errors and null canonical judgments. The automatic two-consecutive-
failure rule stopped the phase. These are failures of a local output-format
constraint, not assignment criterion failures, transport timeouts or proof of
poor technical judgment. The judge's quality on this subset remains unmeasured.
No quote was shortened, validator relaxed or rejected output scored after the run.

Return `MP1-results-2026-11-13T203059865919+0000.zip` has SHA-256
`d588e6d07a36c3574af541dff8c2783825668f0d13331dd4b4be4fc58dcf622d`.
The audit at `qualification/gptoss-v6-return-review-20261113/` verifies the frozen
package/reference, unchanged Mac model/runtime, two attempt lineages, raw schema
rejection, null projections, stop rule, exact coverage accounting and seven report
rows. Remote and received hashes match. The owned server stopped before export;
port 8081 had no listener afterward. No desktop control or Herd settings changed.
The NAS archive is
`MP1-handoff/completed-runs/gptoss-v6-2026-11-13T203059865919+0000/`.

Next, design supplied passage IDs that the model can cite without copying text.
Resolve the IDs to frozen text in the application and continue to audit relevance.
That is an unmeasured new protocol, not permission to reinterpret v6. No further
model request or extension to the other five cases followed this audit. No new
human review is required now.

## Prior v5 checkpoint

The v5 evidence protocol is implemented, but its bounded Mac screen stopped after
two unsuccessful attempts on the first item. **Coverage is 0/10 and agreement is
undefined.** The first response was truncated at 4,096 output tokens; the retry
returned complete JSON but exceeded the candidate-citation count limit. No
judgment was accepted or repaired. Qualification and assessed judging remain pending.

## GPT-OSS judge-v5 returned results

Chad's "Go on next task." authorized the next protocol work. The
[evidence protocol](JUDGE-EVIDENCE-PROTOCOL.md) adds exact requirement/candidate
citations and counterevidence to each dimension, validates their locations and
quotes, and projects only an accepted result to the existing D1–D6 judgment.
The [v5 prompt](../prompts/judge-v5-evidence.md) and response contract changed
together. User messages, reference content, frozen reviews, model and runtime
settings remained unchanged. No model quality improvement is inferred from the
implementation or its 234 passing offline tests.

After the run, provider-shape guards were hardened with six additional synthetic
tests; the final repository/portable checks pass 240 tests. The measured bundle
retains its original code, and replay uses that frozen validator. This hardening
does not revise the failed run or establish a successful model result.

| Measure | Observed result |
| --- | --- |
| New requests / ceiling | 2 / 20 |
| Initial items started | 1 / 10 |
| Initial schema-valid responses | 0 / 1 started (nine items not attempted) |
| Initial citation-accepted responses | 0 / 1 started |
| Retry recoveries | 0 |
| Resolved / unresolved items | 0 / 10 |
| Human/model criterion comparisons | 0; agreement undefined |
| Attempt 1 | 36.5 seconds, 4,096 completion tokens, finish reason `length` |
| Attempt 2 | 25.9 seconds, 3,096 completion tokens, finish reason `stop`; schema rejected |
| Unknown outcomes | 0 |
| Documented cumulative starts | 75 |

The retry supplies four D1 candidate citations where the frozen schema allows at
most three. The application retained both raw responses and null judgments, then
stopped at its two-consecutive-failure boundary. Those are output-contract failures,
not timeouts or evidence of an unavailable Mac server. The nine unattempted items
remain unresolved, not failed technical answers. Zero recorded false approvals
or rejections means there were no accepted comparisons; it is not perfect judgment.

Return `MP1-results-2026-11-13T201505417975+0000.zip` has SHA-256
`248e57673126cb34a77afb57b18fa3cf3005bb10bb9a3b1e4eeb9321ed80eb60`.
Remote and received hashes match. The audit at
`qualification/gptoss-v5-return-review-20261113/` verifies the frozen bundle and
reference, model/runtime signature, two start/result lineages, schema rejection,
null projections, stop condition and six report rows. The owned server stopped
before export; a subsequent check found no listener on port 8081. No desktop
control or Herd changes occurred. The complete working folder is archived under
`MP1-handoff/completed-runs/gptoss-v5-2026-11-13T201505417975+0000/` on the NAS.

The next work item is to simplify the response contract and validate feasibility
under a separately frozen budget. A compact shared citation table may reduce
repeated text, but that hypothesis is unmeasured. Preserve this failed protocol,
its token limit and rejected responses. Do not relax validation retrospectively,
score incomplete output, reuse the unused allocation for another revision, or
advance to blind confirmation. No further human review is needed at this stage.

## Prior v4 checkpoint

The GPT-OSS judge-v4 Mac experiment returned **52/60 agreement, three false
approvals and five false rejections**, down from v3's 55/60. Both confirmed API
errors are detected, but the confirmed safety miss remains and context agreement
falls to 60%. The predeclared advancement condition is not met. Preserve v4 as
development evidence; do not advance it to fresh blind confirmation or assessed
judging. The generator, earlier prompts, rubric, cohort and references are unchanged.

## GPT-OSS judge-v4 returned results

After Chad directed "Go on next steps.", a separate twenty-request allocation
tested [judge-v4](../prompts/judge-v4.md) on the same ten known cases. It requires
checking API ownership and returned interfaces, matching precautions to actual
hazards, and distinguishing context from correctness. Only the system prompt
changed; all user messages, model weights, runtime settings, rubric and frozen
labels remained identical. No case identifiers, reference ratings or reviewer
comments were added to the model instructions.

All ten first attempts produced valid judgments: no retries, transport failures,
truncation or unknown outcomes. This brings documented qualification starts from
63 to 73. The dedicated server stopped before export and port 8081 had no listener
afterward. No desktop control or Herd settings changed. Offline preparation
passed 204 tests, Ruff, shell syntax and bundle integrity checks.

| Dimension / measure | GPT-OSS v3 | GPT-OSS v4 |
| --- | ---: | ---: |
| D1 — Completeness | 10/10 | 8/10 |
| D2 — Safety | 9/10 | 9/10 |
| D3 — API realism | 8/10 | 10/10 |
| D4 — Scope | 10/10 | 10/10 |
| D5 — Context | 8/10 | 6/10 |
| D6 — Tips | 10/10 | 9/10 |
| Agreement | 55/60 (91.7%) | 52/60 (86.7%) |
| False approvals | 3 | 3 |
| False rejections | 2 | 5 |

Two decisions gain agreement and five lose it. The API gains identify the actual
wrong receiver and returned-value interface. However, the same safety false
approval survives: protection against model modification is credited despite
an instruction removing a necessary access guard. Newly approved errors concern
an operation that does not accomplish the requested geometry task and inaccurate
numerical-solver advice. A previously passing report is now rejected for allegedly
missing explanations and storage handling that its answer, steps and tip contain.
Two additional context false rejections also appear.

Review of all sixty explanations shows inconsistent use of evidence, beyond the
headline scores. One item passes completeness while the model's tip explanation
correctly identifies why the core operation cannot achieve the task. Another is rejected
for missing an explanation that its own passing tip judgment acknowledges. These
are recorded against the unchanged human reference, not new human annotations.
Mean request time was 13.8 seconds (138.2 seconds total). This is one stochastic run
per prompt on known development cases; it does not establish repeatability or
isolate a reliable causal effect.

Return `MP1-results-2026-11-13T193720940768+0000.zip` has SHA-256
`5987f5cba4fe157fd9d19571aaaeaf6fd0b4cff0760c1976ec16251d2c8d263c`.
The reproducible audit at `qualification/gptoss-v4-return-review-20261113/`
verifies inputs, reference and policy hashes, model/runtime identity, all ten
attempt lineages, raw/parsed JSON equality and all five comparison rows. Remote
and received archive hashes match. The complete Mac working folder is retained
at `MP1-handoff/completed-runs/gptoss-v4-2026-11-13T193720940768+0000/` on the NAS.

### Next work item

Do not keep extending the same instruction paragraph or choose per-item results
from different prompt versions. The next design should make the decisive evidence
inspectable before each rubric decision: candidate field/excerpt, the matching
reference requirement, any contradiction, and the reason that particular anchor
passes or fails. This is a proposed protocol change, not a measured improvement
or a new rubric. It must preserve the final D1–D6 contract and count every model
request, including any separate evidence-extraction stage.

Prepare and validate that protocol separately before another bounded development
screen. Evaluate all gains, false approvals and evidence fidelity; do not rely on
pooled agreement. No new human review is requested for these already adjudicated
cases. A promising frozen protocol still needs authentic fresh blind confirmation
across all five categories before the existing assessed-calibration gates. No
second revision or additional inference followed the v4 audit.

## Completed judge-v3 human follow-up

Chad completed the [post-result review](JUDGE-V3-REVIEW-RUNBOOK.md) on November 13.
All five explicit ratings reaffirm the frozen reference: the three false
approvals and two false rejections remain. He assessed three v3 explanations as
partly supported and two as unsupported. His assistance declaration is `NONE`,
retained as self-reported; the disclosed model/reference exposure makes this
adjudication separate from fresh blind confirmation.

The submitted file was retrieved from the Mac's Documents folder, validated and
preserved with SHA-256
`05c3829f35f7a81a9a87c2ac6d530238d22b0f91d95afe3cf46f91b71e4c1320`.
The external receipt is `qualification/judge-v3-adjudication-20261113/`;
the NAS review folder includes the completed sheet and `submissions/review-001/`.
No frozen label was amended, and the historical 55/60 result remains unchanged.
Those findings motivated the separate v4 experiment above. No new prompt or model
run was created while recording the human review itself.

## GPT-OSS judge-v3 returned results

Chad authorized remote execution with "Go for it. I'll stand by." after SSH
setup. A separate twenty-request ceiling followed 53 documented starts; ten new
first attempts were used, bringing the documented total to 63. The earlier Mac
working folders matched their audited records with no additional attempts there.
No desktop control or Herd changes occurred. The dedicated server was stopped
before export, and the port was checked afterward.

Return `MP1-results-2026-11-13T174104724949+0000.zip` has SHA-256
`d856debaa0bc708ca7af367d6720cc23839c3ef4f80b1be3978a9a4bde8740b8`.
The external `qualification/gptoss-v3-return-review-20261113/` audit verifies
the frozen inputs/reference, bundle/policy/model/runtime, all attempt lineages,
raw/parsed JSON equality and all four report rows. Ten first attempts were valid,
with no errors, retries, truncation or unknown outcomes. Offline preparation
passed 204 tests, Ruff, shell syntax and package integrity checks.

Only the [judge-v3 system instructions](../prompts/judge-v3.md) changed. The
ten user messages, rubric, labels, weights, embedded template, runtime properties
and client settings were held constant. V3 requires checking evidence across all
seven fields and applying each rubric anchor independently. It contains no case
IDs, expected decisions or human comments. The default judge remains unchanged.

| Dimension / measure | GPT-OSS v2 | GPT-OSS v3 |
| --- | ---: | ---: |
| D1 — Completeness | 8/10 | 10/10 |
| D2 — Safety | 9/10 | 9/10 |
| D3 — API realism | 9/10 | 8/10 |
| D4 — Scope | 10/10 | 10/10 |
| D5 — Context | 7/10 | 8/10 |
| D6 — Tips | 9/10 | 10/10 |
| Agreement | 52/60 (86.7%) | 55/60 (91.7%) |
| False approvals | 0 | 3 |
| False rejections | 8 | 2 |

Six decisions gained agreement and three lost it. Mean request time was 13.1
seconds, totaling 130.5 seconds. This single run uses stochastic sampling; it
does not establish repeatability or a definitive causal effect for every change.

The new false approvals concern a null-dereference safeguard and two API
owner/return-interface defects. D3 predicts pass for all ten cases, including
both human-failing API cases. Its 80% agreement therefore detects neither failure;
the threshold alone is inadequate evidence of reliable judgment. D2 retains 90%
by exchanging a false rejection for a false approval. Two D5 false rejections
remain, and matching scores can still have weak explanations.

Retain v3 as development evidence rather than promote it to the assessed judge.
The human review above confirms these safety/API regressions. Address them before
selecting a frozen candidate for fresh blind confirmation. No further iteration
or model request followed during that audit; the separately authorized v4 work
is recorded above.
The NAS archive is `MP1-handoff/completed-runs/gptoss-v3-2026-11-13T174104724949+0000/`.

## GPT-OSS Mac returned results

Return `MP1-results-2026-11-13T161049817190+0000.zip` has SHA-256
`acc61d5382c9061a49c7830939e974e04ba124e6e11055dd5e70a02b5cd6e85d`.
The external `qualification/gptoss-return-review-20261113/` audit validates bundle,
policy, frozen inputs/reference, model/runtime identity, attempt lineage and
raw/parsed judgment equality. Independent recomputation matches all three rows
of the returned report. All ten GPT-OSS first attempts were valid; no errors,
retries, truncation or unknown outcomes occurred. No new inference ran during review.

| Dimension / measure | GPT-OSS Mac v2 | Llama Mac v2 | Qwen Mac v2 |
| --- | ---: | ---: | ---: |
| D1 — Completeness | 8/10 | 7/10 | 9/10 |
| D2 — Safety | 9/10 | 7/10 | 7/10 |
| D3 — API realism | 9/10 | 8/10 | 8/10 |
| D4 — Scope | 10/10 | 10/10 | 10/10 |
| D5 — Context | 7/10 | 9/10 | 8/10 |
| D6 — Tips | 9/10 | 9/10 | 9/10 |
| Total agreement | 52/60 (86.7%) | 50/60 (83.3%) | 51/60 (85%) |
| False approvals | 0 | 9 | 3 |
| False rejections | 8 | 1 | 6 |

GPT-OSS gains nine matches and loses seven versus Llama; it gains six and loses
five versus Qwen. The eight disagreements include overlooking information in the
steps/safety/tips fields and extending procedural failures into context failures.
Some matching decisions also have inaccurate explanations of what the payload
contains. These are findings against the frozen reference, not revised labels.

The same Mac, Python version, llama.cpp `b12110-cd959bae9`, one slot, context
16,384 and default sampling parameters are recorded. Client settings remain
temperature 0.1, 4,096 tokens and 300 seconds. Mean request time is 11.4 seconds
(114.0 seconds total). Model templates/reasoning differ; this is a historical
development comparison, not a controlled speed benchmark or independent calibration.

The next proposed experiment is a general instruction revision for cross-field
evidence coverage and independent rubric boundaries. Keep v2 and these results
immutable; do not insert known answers or reuse the remaining allowance for a new
experiment. Fresh blind confirmation remains necessary before qualification.
At this earlier checkpoint the supplied ledgers accounted for 53 starts. Subsequent
SSH inspection found no additional attempts in either known Mac working folder;
the v3 experiment above adds ten. This was not a whole-machine search.

## GPT-OSS preparation record — completed by the return above

The [Mac runbook](GPTOSS-MAC-RUNBOOK.md) prepares one GPT-OSS-20B MXFP4 screen,
experiment `gptoss20b-mac-development-001`. Chad requested another Mac runbook;
this is a proposed screening candidate, not a replacement owner-selected or
qualified assessed judge. Its distinct model family, local availability and
[documented reasoning/structured-output capabilities](https://openai.com/index/introducing-gpt-oss/)
provide a test rationale, not evidence of stronger engineering judgment.

The NAS file's full SHA-256 was verified against the
[publisher's pinned GGUF](https://huggingface.co/ggml-org/gpt-oss-20b-GGUF/blob/b97cbb20d1995efd41dce8c4dd1ddf86e8db375b/gpt-oss-20b-MXFP4.gguf):
`27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901`,
12,109,566,624 bytes. No weight conversion or fresh model download was needed.

The new portable package is `qualification/MP1-GPTOSS-MAC/`, also provided as
`MP1-GPTOSS-MAC.zip` on the private handoff share. It reuses the exact ten-case
v2 inputs and frozen reviews, and includes the audited Mac Llama/Qwen return as
historical comparators. Only GPT-OSS may issue new completions. The existing
Mac/server build, one slot and context are checked; each run records its model
template and default runtime settings. The model's native reasoning/template
behavior differs, and this is not a randomized or repeated-seed comparison.

The separate operator-activated allowance is at most twenty new starts after
43 earlier starts, for a cumulative ceiling of 63. Attempts remain capped at two
per item, 300 seconds and 4,096 tokens. Two consecutive unsuccessful completions
stop the run; unknown outcomes require inspection. No live candidate request was
made during preparation. At that checkpoint native model/client compatibility and
judge quality were unmeasured; the return above now supplies development evidence.
Fresh blind confirmation and assessed calibration remain later gates.

## Mac v2 returned results

The November 13 return passed bundle/policy/input/attempt validation. All twenty
raw judgments match their saved parsed records and the independently recomputed
report; both models completed ten first attempts without retries, errors,
truncation or unknown outcomes. The source ZIP is retained with SHA-256
`cf8be0a1c700ef568fc16bd3bf543f2e5febfd7511fd254bb4124947840d3fc2`.

| Dimension | Llama Mac v2 | Qwen Mac v2 |
| --- | ---: | ---: |
| D1 — Completeness | 7/10 | 9/10 |
| D2 — Safety | 7/10 | 7/10 |
| D3 — API realism | 8/10 | 8/10 |
| D4 — Scope | 10/10 | 10/10 |
| D5 — Context | 9/10 | 8/10 |
| D6 — Tips | 9/10 | 9/10 |
| Total, descriptive only | 50/60 (83.3%) | 51/60 (85%) |

Llama's false approvals fell from fourteen to nine and false rejections from four
to one. Qwen's false approvals fell from ten to three, while false rejections rose
from two to six. Llama gained eight matching decisions without losing any; Qwen
gained ten and lost seven. Matching scores sometimes still have weak reasons.
These changes do not isolate a prompt effect because the platform/runtime also
changed, and the cases were already used to develop v2.

Both Mac phases record native arm64 macOS, Python 3.12.13, llama.cpp
`b12110-cd959bae9`, one slot and context 16,384, with the original GGUF pins and
client generation settings. Startup logs establish loading/serving but do not
explicitly record Metal offload layers. Mean request time was 38.1 seconds for
Llama and 9.6 seconds for Qwen (totals 381.1 and 96.3 seconds). This is operational
evidence, not a controlled hardware benchmark or a Herd-repair result.

Llama still approves critical procedural defects. Qwen detects more of them but
introduces dimension-boundary disagreements and a new false approval of a flawed
tip. Qwen remains the baseline generator, so its pooled 85% cannot supply the
required distinct stronger judge. Neither aggregate score establishes assessed
calibration; both models have D2 agreement of 7/10 on this development set.

Keep v2 as measured development evidence. Prepare another distinct candidate's
identity and rationale for a bounded same-Mac comparison before launching it;
do not silently change prompts, enter labels, reuse unused slots for new work or
advance to assessed judging. Any promising candidate still needs fresh blind
confirmation. The original twenty assessed reviews stay frozen.

## Earlier Fedora v1 results

Both models produced ten valid first-attempt judgments, with no retries, transport
failures, truncated responses or unknown outcomes in the Fedora comparison.
The returned bundle, policy, weight-hash records, input hashes and attempt lineage
passed validation. Each raw completion matched its parsed judgment, and independent
metric recomputation matched the returned report.

| Dimension | Llama 3.3 70B | Qwen3 30B-A3B |
| --- | ---: | ---: |
| D1 — Answer Completeness | 6/10 | 7/10 |
| D2 — Safety Specificity | 7/10 | 8/10 |
| D3 — API Realism | 5/10 | 8/10 |
| D4 — Scope Appropriateness | 10/10 | 8/10 |
| D5 — Context Clarity | 8/10 | 9/10 |
| D6 — Tip Usefulness | 6/10 | 8/10 |
| Total, descriptive only | 42/60 (70%) | 48/60 (80%) |

Llama incorrectly passed 14 of the 18 human-failing criterion decisions and
incorrectly rejected four human-passing criteria. Qwen incorrectly passed ten
human-failing decisions and rejected two human-passing decisions. Higher pooled
agreement does not establish per-dimension calibration; Qwen is also the baseline
generator and cannot satisfy the distinct-judge requirement.

Mean request duration was 213.0 seconds for Llama (202.4–241.5 seconds) and 74.0
seconds for Qwen (46.0–116.1 seconds). All Llama requests exceeded the earlier
120-second deadline but completed within the new 300-second budget. This shows
that the larger client timeout accommodated these requests, not that Herd was
repaired or that a controlled hardware speed improvement was demonstrated.

Both phases used the pinned Q4_K_M weights, temperature 0.1, max output 4096 and
16,384 context on the same recorded Fedora host/server build. Model-specific chat
templates and reasoning behavior differ. Ten authored examples, with AI-assisted
reviews personally verified and adopted by Chad, do not establish general model
superiority or assessed calibration.

The earlier Windows phase remains retained: two 120-second timeouts plus one
started request with unknown outcome. Together with the twenty Fedora requests,
23 qualification requests have started. Completed cases cannot be rerun using an
old run's unused budget after changing the prompt.

## Observed failure patterns and intervention

Both judges accepted candidate claims without adequately checking the actual
procedure. Errors included approving the removal of needed guards, accepting
incorrect API ownership/interface claims, and confusing plausible step lists
with successful completion. Llama additionally missed changed task specifications.
Qwen sometimes agreed with a failing label while giving an incomplete or
unsupported reason. Llama inconsistently treated supplied environment/version
requirements as unverifiable installation claims.

`judge-v2` requests evidence tied to the exact task, checks for contradictions
across all candidate fields, distinguishes API existence from misuse, and requires
accurate tips and effective precautions. It retains the existing rubric and output
schema and does not contain the ten reference labels, comments, item identifiers
or item-specific correction keys. Its hypothesis is that these instructions will
reduce false approvals without creating blanket failures or expanding D4's
professional-review requirement.

## V2 experiment protocol and stopping conditions

Chad instructed, "Document these findings and go on next steps." Prepare one
bounded development comparison of `judge-v2` against the original ten cases,
using the same frozen input/reference content, model pins and client generation
settings. The initial Fedora plan changed only the judge instruction; the later
Mac direction below additionally changes platform/runtime. Use new artifact identities and retain both
models' raw attempts; at most two attempts per case/model, forty new requests
total. Stop a phase after two consecutive timeouts. Unknown outcomes consume their
attempt and require inspection before resuming. Record authorization in the new
experiment policy; neither this experiment nor its unused budget authorizes a
further prompt version or the assessed judge run.

### Execution moved to the Mac

Chad subsequently reserved Linux for necessary Herd updates and directed this
evaluation to the Mac. Use `MP1-JUDGE-V2-MAC`, replacing the unstarted Fedora v2
handoff within the same forty-request allocation. If any Fedora v2 requests have
already started, reconcile those records before starting Mac requests; the move
does not grant an additional budget.

The checked-in Herd Mac backend uses MLX. The Mac handoff therefore uses a separate
local llama.cpp/Metal server with the same pinned GGUF files, native Apple Silicon
Python, port 8081, context 16,384 and one request slot. It does not change Herd
services or silently substitute converted weights. The handoff records the actual
Mac runtime/build and preserves the original Fedora evidence.

Both models must use the same Mac, server build and launch flags. Comparisons with
Fedora v1 now vary platform/runtime as well as prompt, so apparent improvement
cannot be attributed solely to `judge-v2`. The within-Mac model comparison and
agreement with the fixed reference remain development diagnostics. Native Mac
execution is now recorded in the returned results above; qualification is still
pending. Twenty Mac requests bring the retained history to 43 total starts.

These cases have informed the prompt change, so the new results are **development
diagnostics**, not an independent qualification result. Compare first-attempt
validity, per-dimension agreement, false approvals, false rejections, substantive
justifications and latency with v1. Preserve regressions. No new numerical
qualification threshold is introduced, and matching labels with incorrect
justifications do not establish reliable judgment.

After the development comparison, freeze any promising protocol before preparing
fresh blind confirmation cases across all five categories. Obtain authentic human
reviews before either model sees those cases. If the intervention does not help,
record that result before proposing another model or protocol. Do not tune on or
amend the frozen 20-item assessed reference to improve scores.

Assessed judging remains gated on a defensible distinct stronger-model basis and
the existing workflow: fifty cohort items, twenty frozen human reviews, complete
coverage and at least 80% agreement in every dimension. No qualification receipt
asserting readiness has been issued.

## Evidence locations

Raw evidence is excluded from Git under workspace `artifacts/evidence/P1-03/`:

- Returned data: `qualification/MP1-results-2026-11-13T050434763053+0000/`.
- Review, reproducible audit and file hashes: `qualification/return-review-20261113/`.
- Mac return: `qualification/MP1-results-2026-11-13T150132266655+0000/`.
- Mac review, audit and hashes: `qualification/mac-return-review-20261113/`.
- Frozen original packet/adoption: `qualification/llama-vs-qwen-v1/`.
- Portable original code and packet: `qualification/MP1-LINUX-HANDOFF/`.
- Current development handoff: `qualification/MP1-JUDGE-V2-MAC/HANDOFF.md`;
  its ZIP is also in the private NAS `AIA/MP1-handoff/` folder.
- Superseded, preserved Fedora development handoff: `qualification/MP1-JUDGE-V2-DEVELOPMENT/`.

The ten-review reference remains
`b86a7b139c1077a527f9e29a189aae41821add29e28b58f534e971e2ca81c65b`;
the separate assessed reference remains
`1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8`.
