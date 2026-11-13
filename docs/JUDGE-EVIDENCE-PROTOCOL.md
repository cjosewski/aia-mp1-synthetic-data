# Judge evidence protocol — v5 development

Chad directed "Go on next task." after the v4 results. This implements the next
design work item: make evidence supporting each rating inspectable and reject
untraceable citations before reporting a judgment. It does not change the rubric,
frozen human reference, generator or assessed judge defaults.

**Measured status:** 234 offline tests passed (213 project and 21 portable-runner
tests), along with lint, formatting, shell syntax, bundle hashes and unchanged
input checks. The Mac run stopped after two failures on the first item: a
4,096-token truncated response, followed by a complete response with four D1
candidate citations where the frozen schema allows at most three. No response
was accepted; all ten items remain unresolved and agreement is undefined. This
protocol is retained as a failed development experiment. Do not rerun the package
or relax its validator to count the rejected response. The
[qualification checkpoint](JUDGE-QUALIFICATION-RESULTS.md) owns the audited result.

A post-run robustness check added explicit rejection of malformed provider
message shapes. The final repository and portable checks pass 240 tests. This
guard change was not used in the measured run; the frozen bundle retains the
exact experimental implementation, and the audit imports that frozen copy.

## Contract and limits

[judge-v5-evidence.md](../prompts/judge-v5-evidence.md) asks for one response with
six evidence records. Each includes one requirement citation, one to three
candidate citations, zero to two counterevidence citations, an explicit absence
claim/search declaration if applicable, and a decision/short justification.
Citation paths point to the original candidate, task, source text or that
dimension's frozen rubric anchor. All seven candidate fields remain available.
No expected ratings, reviewer comments or item-specific correction keys enter
the model request.

[evidence_judge.py](../src/aia_mp1/evidence_judge.py) rejects extra/missing fields,
nonbinary values, malformed/truncated JSON, duplicate JSON keys, nonexistent or
disallowed citation locations, quotes not present verbatim and duplicated
citations. Absence claims require a failure and all seven searched fields. The
existing D1–D6 Judgment is projected only after validation. Full evidence and
raw completion remain in the attempt record; projection does not discard them.

These checks prove citation existence and structural consistency. They cannot
prove relevance, technical truth, that the model searched every field, or that
the evidence entails the decision. A syntactically accepted response is not a
quality pass. The result audit must inspect all sixty decisions and citations,
including matching ratings and any counterevidence. There is no automatic
semantic repair, score override, majority vote or per-item prompt selection.

The protocol uses one request per attempt. It changes both instruction and
response schema; the comparison cannot isolate those effects. The user messages
and all underlying tasks/source excerpts remain byte-identical to v4. No extra
retrieval or evidence-extraction call is hidden from the request budget.

## Bounded development experiment

Use a new package/run identity with the same ten known cases, GPT-OSS-20B MXFP4,
Mac runtime, one slot, context 16,384, temperature 0.1, max output 4,096 and
300-second timeout. Keep prior v4 and earlier records immutable. Starts previously
documented: 73. Allocate at most 20 new starts, two per item, for a cumulative
ceiling of 93. Invalid citations consume an attempt exactly like malformed JSON.
Stop after two consecutive unsuccessful attempts; an unknown outcome requires
inspection. Do not extend the output budget or repair the protocol mid-run.

Before execution: full locked WSL tests, meaningful citation/transport/lineage
failure cases, portable-runner regression tests, lint, shell syntax, frozen
package hashes and unchanged-input/reference checks must pass. Run only the
dedicated project server over the established SSH connection. No desktop control
or Herd changes are required. Stop the owned server and archive the complete
working folder to the NAS after the bounded run.

Report started requests, initial structural validity, initial citation acceptance,
retry recovery, unresolved coverage and per-dimension compared counts separately.
Never use unresolved items as passes or hide them by reducing the ten-item target.
Compare agreement, false approvals, false rejections and evidence fidelity against
the archived v4/v3/v2 results. A valid quote attached to a wrong interpretation is
still a judgment defect.

Advance only if coverage is complete, every dimension meets the existing 80%
development agreement floor, no confirmed safety/API false approval remains,
and examination of citations supports a defensible candidate. This is a screen,
not qualification. Fresh blind confirmation across all five categories and the
existing assessed-calibration requirements remain necessary. Stop after this
audit; no automatic second revision or assessed inference follows.

## Subsequent design work

The current format repeats long paths and quotes across six dimensions, increasing
response size and schema burden. Simplify the evidence representation before a
separate feasibility test: consider a bounded shared citation table with short
references from dimension records, keeping exact-quote validation and the final
canonical judgment unchanged. A larger token budget is another possible factor,
but any change must be frozen and reported as a new experiment. Neither approach
is implemented or measured here. Do not silently repair or rescore this run.
