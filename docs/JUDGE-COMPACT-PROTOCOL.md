# V6 compact evidence feasibility protocol

Chad authorized this next step with "Go" after the v5 feasibility failure. Keep
the frozen v5 run unchanged. This experiment tests a shared citation table and
short path aliases, with citation indices in each D1–D6 record. Exact quote,
namespace, index, binary-score and canonical-projection validation remain.

**Measured status:** 267 offline checks passed (245 project tests and 22 portable
tests). The Mac run used two attempts on the first case and stopped as planned.
Both returned complete JSON within the 4,096-token limit, but quotes of 181–198
characters exceeded this protocol's 160-character bound. No judgment was accepted;
coverage is 0/5 and agreement is undefined. This is an output-contract feasibility
failure, not a rescore of the technical answers. The
[qualification checkpoint](JUDGE-QUALIFICATION-RESULTS.md) records the audit.

Unlike v5, this format does not repeat full citation objects in each dimension
or require a separate missing-information/search-declaration object. The prompt
still requires reading every field and checking counterevidence. The removed
declaration never established that a model actually performed a complete search.
The rubric and semantic standards are unchanged. Interpretation and evidence
relevance still need audit; exact text matches alone cannot establish correctness.

## Frozen feasibility scope

Use the first known qualification example from each category, in original order:
qualification-v1-01 through qualification-v1-05. This selection precedes inference
and covers GIS, CAD, simulation, AEC and structural analysis. These are development
cases with adopted references, not a blind sample. Compare archived judgments
only on these same five items; do not compare a 30-decision result with an earlier
60-decision total as if denominators matched.

At most ten new requests, two per item, after 75 documented starts (ceiling 85).
Stop after two consecutive failures or five resolved items. Unknown outcomes
consume starts and require inspection. Do not change token limits or validation
mid-run. Any remaining unused allocation is not a new revision's budget.

Use the same Mac, GPT-OSS-20B MXFP4 checksum, llama.cpp build, embedded template,
context 16,384 and one slot. Keep temperature 0.1, output limit 4,096 and timeout
300 seconds. User messages and their source/rubric/reference content are unchanged;
the system instruction and response contract change together. No labels or review
comments enter the model request. Use one call per attempt, with no hidden repair.

Before execution, pass the locked WSL suite, portable attempt-accounting tests,
lint, shell syntax, original-input/reference verification and package hashes.
Retain every start, completion or error, full evidence and canonical projection.
Record initial JSON/schema validity separately from citation acceptance, retry
recovery and unresolved coverage. Report observed comparison counts and the
five-item target separately. Review citations and explanations for all accepted
judgments, including matches.

This check ends with an audit, complete NAS archive and owned-server shutdown.
No desktop control or Herd configuration changes are needed. Even five accepted
outputs establish only small-sample format feasibility. False approvals or weak
citations remain defects; quality qualification needs the full development screen,
fresh blind confirmation and the existing assessed calibration gates. No automatic
second revision, extension to ten cases or assessed inference follows this check.

## Next design

Supply immutable passage IDs with the inputs and require the model to reference
those IDs, rather than copy and shorten quotations. The application can resolve
each ID to the exact frozen text for auditing. This would remove model-generated
quote-length constraints while retaining traceability; semantic relevance still
needs review. It is a proposed separate protocol, not a retrospective relaxation
of v6 or evidence of better judgment. Preserve v6's rejected outputs and limits.
