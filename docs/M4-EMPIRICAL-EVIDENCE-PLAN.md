# M4 measured-evidence supplement — design

Implementation checkpoint: [M4 retained runtime evidence](M4-RUNTIME-EVIDENCE.md).
This document preserves the design recorded before implementation.

November 17, 2026. The current recovery protocol can bind API documentation,
task text and attributed reasoning, but has no distinct authority for a retained
runtime observation. Exact-version probes now exist. They must not be relabeled
as documentation or silently admitted through a reasoning note.

This supplement proposes one additional evidence kind, `runtime_observation`,
in a separately versioned v3 plan. It changes evidence representation, not
the six rubric anchors, frozen reviews, 80%-per-dimension requirement, proposed
twenty-start ceiling or assessed allocations. At the planning checkpoint,
implementation was pending and the v2 packet remained disabled.

## Required representation

Each empirical record must bind the complete pre-execution protocol, exact
script, dependency lock, identity records and raw stdout/stderr/outcomes by
snapshot-relative paths and SHA-256. Record authorship, creation time, declared
question, all scheduled cases, timeouts/failures and limitations. Cite an exact
span in the retained raw result; keep interpretation separate from observation.
Retain any identity-capture timing limitation and environment incident.

The model view must expose the script, inputs, raw outcome, versions and limits
needed to assess the claim. A version string or an assistant-written summary
alone is insufficient. No source-role substitution: a probe cannot satisfy an
`api_contract` binding, and a documentation passage cannot satisfy an empirical
binding. Neither can supply an authentic human label.

V1/v2 schemas, fingerprints and replay remain compatible. A v3 plan must retain
the original parent/check lineage, text coverage and required dimensions. Any
child reclassification must be recorded with its reason; do not delete a difficult
claim. Unused experiment context and changed bytes must be rejected.

## Permitted conclusions and limits

A matching successful counterexample can refute a necessary-failure claim.
It does not prove that every malformed input is accepted or that the input is
valid. A failed case establishes that case's failure, not every implementation's
contract. Setup exceptions must remain distinct from analysis failures and
singularity. A numerical result alone cannot establish physical unit consistency.

For the OpenSees investigation, both the wrapper and Linux backend are pinned
to 3.5.1.3. The package's engine reports 3.5.1. The standalone examples are
assistant-authored development research, with no model call or engineering-design
acceptance implied. The original wrapper-only identity record and later isolated
native identity must not be collapsed into a fabricated contemporaneous receipt.

## Audit and verification before use

Require an explicit empirical applicability audit before any scorer consumes a
finding. Review version/build relevance, complete scheduled-case accounting,
script/output consistency, qualifier scope and limits of generalization. Legacy
fact audits must not unlock empirical findings. Unknown outcomes and missing
files remain unresolved; a fully hashed record is not automatically true or
sufficient. The existing complete-coverage scoring gate remains in force.

Tests must reject altered protocol/script/lock/output, path escapes, missing or
selectively omitted cases, wrong authority bindings, unbound records, stale plan
hashes, hidden uncertainty and legacy audit bypass. Preserve attribution and limits
in both verifier and scorer views. Test v1/v2 replay without changing old hashes.
Do not implement live transport as part of this supplement.

After implementation, prepare a new packet revision that explicitly maps only
applicable holds to the probes. Report remaining documentary gaps separately.
Only then complete source/audit review and token/runtime preflight for the bounded
development trial. No automatic fourth assessed run follows from the supplement.
