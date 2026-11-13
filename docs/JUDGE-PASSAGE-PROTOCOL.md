# V7 supplied-passage feasibility protocol

Chad authorized this next step with "Go" after the v6 quote-length failures.
The application supplies stable IDs for full original text fields/list entries;
the model returns IDs and D1–D6 decisions, without copying quotations. The
application resolves valid IDs to exact frozen text for audit. The earlier
contracts, failures, rubric and human references remain unchanged.

**Measured status:** 288 offline tests passed. All five Mac responses were valid
and passage-accepted on their first attempt, with no retries or truncation.
Agreement is 27/30 (90%): one API false approval and two context false rejections.
D5 is 3/5; the judge remains unqualified. Exact passage resolution worked, but
some explanations still overlook supplied content. The
[qualification checkpoint](JUDGE-QUALIFICATION-RESULTS.md) owns the detailed audit.

## Contract

Candidate passages use C.* IDs, reference passages R.*. A model judgment has one
requirement ID, candidate evidence/counterevidence IDs, strict binary decision
and nonblank justification per dimension. Unknown IDs, tampered ID mappings,
wrong citation roles, foreign rubric anchors, missing dimensions and extra fields
are rejected. Citation existence and correct roles do not establish semantic
support; review all accepted decisions and resolved passages.

IDs represent complete original fields or list entries. They are less precise
than sentence-level quotations and do not demonstrate that every relevant passage
was considered. No model-generated quote-length or citation-table-count constraint
applies. The prompt requests concise justifications; the canonical nonblank
justification contract is used without v6's extra character bound.

Underlying candidate/reference text is unchanged. The new user message adds only
an application-generated passage_index mapping; the system prompt and response
schema also change. The frozen package binds original input hashes, augmented
messages and resolved passage catalogs. Expected labels and reviewer comments
remain excluded. This is one model request per attempt with no hidden repair.

## Bounded check

Use the same five known cases as v6, qualification-v1-01 through -05, one per
category. At most ten new requests after 77 documented starts (ceiling 87), two
per case. Stop after two consecutive unsuccessful attempts or five resolved
cases; unknown outcomes require inspection. No mid-run schema/settings changes.
Compare archived judgments on exactly this subset; preserve full historical runs.

Hold the Mac, pinned GPT-OSS-20B MXFP4 weights, llama.cpp build, embedded template,
context 16,384, one slot, temperature 0.1, 4,096-token output limit and 300-second
timeout fixed. Before execution, pass locked WSL tests, portable accounting tests,
lint, shell syntax and package/input/reference hashes. Use established SSH access
and only the project's dedicated server; no desktop control or Herd changes.

Record initial schema validity, passage acceptance, retry recovery, unresolved
coverage and actual comparison counts separately. Preserve every raw attempt and
canonical projection; resolve citations to original text without model rewriting.
After the bounded check, audit all available decisions and evidence, archive the
complete folder to the NAS and stop the owned server. No automatic extension or
second revision follows. Five accepted outputs demonstrate only small-sample
format feasibility, not reliable judgment or assessed qualification. Full
development screening, fresh blind confirmation and assessed calibration remain
separate requirements.

## Next work item

Freeze this usable passage format and prepare a controlled candidate comparison.
The next candidate must have verified local availability, model identity and a
recorded selection basis; preserve the protocol, tasks, rubric and references.
Judge evidence use and API-owner accuracy as well as label agreement. This is a
proposed model comparison, not a stronger-judge selection or a new inference run.
Further formatting changes are not supported by this successful format check.
