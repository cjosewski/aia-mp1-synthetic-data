# V8.1 verifier revision

Prepared November 13, 2026 following Chad's “go” after the V8 compact2 diagnosis.
This is a new known-case development protocol, not assessed calibration.

## Change and hypothesis

The previous verifier cited source/task metadata IDs instead of passage IDs,
omitted two core steps, then exhausted its output allowance on the identical
retry. [V8.1](../prompts/judge-v8.1-facts.md) clarifies ID namespaces and adds
application-generated required-candidate and allowed-reference lists to the
verifier system message. It requires inspection of tools/installations as claims,
distinguishes task constraints from API facts, groups repeated identical claims,
and asks for short claim labels and brief evidence conclusions. It does not cap
findings by dropping claims or treat absent source evidence as a pass.

Hypothesis: explicit lists and concise output instructions improve accepted
coverage within the existing output budget. This is unmeasured until execution;
prompt instructions cannot guarantee token use or semantic completeness.

The control/scorer prompts and response schemas, candidates, task/source text,
all 18 primary excerpts, typed authority, rubric and frozen human reference remain
unchanged. The source gaps in the previous package remain disclosed. No raw output
is repaired, no metadata ID is automatically mapped to an ambiguous passage, and
the existing coverage/authority/uncertainty validators remain binding.

## Frozen run boundary

- Protocol `v8.1-development` binds **95 prior development starts**.
- Five original cases, one per category; same matched control/verifier/scorer
  schedule and odd/even ordering as V8.
- New maximum **30 starts**, cumulative ceiling **125**; two attempts per stage.
  The unused V8 allowance is not carried over.
- Stop after two consecutive failures, unknown outcomes, identity/input drift,
  token overflow, ceiling or completed schedule. Valid uncertainty is not retried.
- Same pinned GPT-OSS-20B MXFP4, Mac, build/template, 16384 context, one slot,
  temperature 0.1, 4096 output tokens and 300-second timeout. No Herd changes.
- Freeze the new package separately, pass native exact-wire token checks before
  inference, and check the actual scorer memo before dispatch.
- Preserve all starts/completions, full Mac folder and audit on the NAS. Stop the
  owned server. No automatic experiment or extra request after the stop boundary.

The [V8 reporting and advancement criteria](JUDGE-FACTCHECK-DESIGN.md#5-reporting-and-advancement)
remain unchanged. Report schema validity separately from contract acceptance,
all five selected cases in coverage, unknowns, skipped dependencies and paired
denominators. Audit every returned finding/disposition/decision; matching known
labels alone never establishes correct evidence use or judge qualification.

## Measured result

**344 locked WSL tests pass**, including protocol/allocation binding and complete
application-generated ID lists; Ruff and shell syntax checks pass. The package
proves that candidate/source/rubric/runtime/reference content and control requests
are unchanged. Native preflight passed all 15 checks. Scorer reserve totals remain
14510, 15503, 16069, 14308 and 14562 tokens in case order, within context 16384.

The run stopped after four requests under the two-consecutive-failure rule:

| Attempt | First ArcPy case | Result | Output tokens | Seconds |
| --- | --- | --- | ---: | ---: |
| 1 | Control | Accepted; six matches on one known case | 1592 | 16.17 |
| 2 | Verifier | Accepted; all candidate passages accounted for | 2619 | 24.38 |
| 3 | Scorer | Invalid requirement/evidence roles | 3991 | 38.94 |
| 4 | Identical scorer retry | Same format failures | 3280 | 28.51 |

Both scorers finish normally, with no timeout or output exhaustion. They supply
rubric prose instead of R.* requirement IDs in all six dimensions (four strings
also exceed 80 characters), and R.* source IDs where C.* candidate evidence is
required. Every supplied finding receives a disposition, but neither response
qualifies for canonical projection. No output was repaired or re-scored.

The verifier's first-attempt acceptance improves reference resolution and passage
coverage on this case, not demonstrated factual reliability. It returns 11
supported findings, many bundling several claims and classifying API-bearing
statements as procedures. It overlooks the documented Field.name, root-only
listing and exception-cleanup evidence limits. The two scorers accept every
finding, including these overclaims, without dispute or uncertainty. The semantic
audit inspects all 11 findings, both sets of 11 dispositions, the six control
decisions and both attempted six-decision scorer outputs. Correct known labels
do not resolve the source gaps or validate the explanations.

Control coverage is **1/5**, treatment **0/5**, matched pairs **0**. Four starts
raise the cumulative development count from **95 to 99**, with no unknown outcomes.
The other four cases were not attempted after the global stop. No paired gain or
judge qualification is established; the remaining allocation does not authorize
automatic continuation. The owned server stopped and port 8081 was verified free.

External evidence under workspace `artifacts/evidence/P1-03/qualification/`:

- Frozen package `MP1-GPTOSS-V81-MAC.zip`, SHA-256
  `42535ba7b9158ae9c23f4de069992f4fadc41209678d736f13a92383300ccab7`.
- Complete Mac return `MP1-GPTOSS-V81-RETURN.zip`, SHA-256
  `3b610ddab5c42c63b9cf86b821a482bab4dd1a98a9540942393a08c0748328e7`.
- `mp1-gptoss-v81-return-audit/`: replay using its frozen code, 145-file integrity
  verification, complete Mac folder, `diagnosis.json`, reproducible scripts and
  `SEMANTIC-REVIEW.md`.

Package, full return and audit are copied to `\\192.168.0.55\aia\MP1-handoff`;
all 192 copied files match their source hashes. Prior runs and human records remain
unchanged. M4 remains in progress. Next revise scorer citation roles and strengthen
atomic API-claim/evidence-limit verification before a separate frozen protocol and
allocation based on 99 prior starts. No new human review is needed for this revision.
