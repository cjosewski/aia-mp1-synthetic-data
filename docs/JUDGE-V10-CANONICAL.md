# V10 context and evidence clarification

This is a prompt-only follow-up to the [V9 result](JUDGE-V9-CANONICAL.md).
It is covered by Chad's instruction to continue P1-03 autonomously and his grant
of full Mac access. The rubric and all frozen reviews remain unchanged.

The V9 screen matched five dimensions perfectly but repeatedly conflated a wrong
answer with unclear context. Its Revit explanations also claimed present steps
were missing. V10 clarifies that D5 identifies the problem being answered rather
than scoring the truth or execution of the proposed answer. It still fails actual
ambiguity or substituted essential givens. Public justifications should cite the
decisive candidate fact and distinguish absent, incorrect and inadequate content.
This is a development hypothesis, not evidence of success or a rubric amendment.

All ten original development cases and their complete user messages are unchanged.
The canonical Judgment schema, GPT-OSS-120B weights, native Mac/build/template,
context 16384, one slot, temperature 0.1, high reasoning, 8192 output allowance and
300-second timeout are unchanged. Only the system prompt differs from V9R1.

Freeze a new package and plan before inference: at most twenty new starts after
109, cumulative ceiling 129, two attempts per case and a stop after two consecutive
failures. Unknown outcomes, changed identities, token overflow or exhausted budgets
stop dispatch. Unused V9 requests do not transfer. Preserve every raw output and
the full Mac return, and stop the separately owned server at the end.

Evaluate exact per-dimension agreement and audit every public explanation. The
fresh confirmation draft has no labels and has not been shown to the model; it
must remain separate from this tuning set. Advance only if the known-case evidence
supports doing so, then freeze the candidate before authentic blind confirmation.
No assessed judge default or qualification receipt changes automatically.

## Measured result

All ten requests produced valid first-attempt judgments. Agreement is **53/60**,
down from V9R1's 56/60. Dimension matches are **8, 8, 9, 10, 8, 10 out of ten**;
there are six false approvals and one false rejection. The identical first five
score 28/30, but that subset hides regressions in the second five.

Every dimension numerically reaches 80% on these known cases. Semantic audit still
rejects advancement: case 04 approves safety based on read-only/disposable-model
precautions despite the unguarded null dereference; case 05 approves completeness
despite its construction-approval conclusion; case 06 approves the nonexistent
attribute interface on `arcpy.da.Describe` and the incomplete CRS procedure; case
09 approves safety and context despite skipped solver checks and substituted
equation/initial condition. Case 06 also remains a false D5 rejection. Present-field
descriptions improve over V9, but accuracy regresses in other dimensions.

The server stopped and port 8081 was confirmed free. All 133 frozen files and the
returned ledger replay correctly. Cumulative starts are **119**. Raw return/audit:
`qualification/mp1-gptoss120b-v10-return-audit/`; archive SHA-256
`2631df581f433218ffc30f3799a41727ae4dd024590340f5068eaf5fc44b8112`.
No qualification receipt or fresh confirmation request is issued for V10.

Next test independent scoring of D5 and the other five dimensions, with original
candidate/reference inputs supplied to both calls and no cross-call judgments or
human labels. Both calls must succeed before a six-dimensional result exists.
This is a new protocol requiring its own frozen package and bounded allocation;
it does not repair V9/V10 outputs or combine their best known-case ratings.
