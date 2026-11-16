# V13 versus V14 — completed development comparison

**Subsequent owner decision:** [70% overall calibration agreement](ACCEPTANCE-AMENDMENT-70.md)
allows the completed V13 baseline to proceed without another judge experiment.
The V14 comparison and its original non-advancement decision below are preserved.

November 16, 2026. **Do not advance V14. The Mac is free.** The owned server is
stopped, its PID is absent and port 8081 has no listener. Herd was not changed.

The [approved comparison](JUDGE-V14-PROPOSAL.md) completed twenty valid first
attempts: both prompts on the same ten previously reviewed confirmation cases.
V14 matched **55/60** human ratings versus the capped V13 control's **56/60**.
There was one improvement and two regressions, including a new safety false
approval. Both prompts also failed the context-agreement threshold.

These are exposed development cases, not fresh confirmation or assessed
calibration. No output was imported into the fifty-item assessment. The earlier
unrestricted V13 confirmation and the separate full baseline run remain distinct.

## Measured comparison

Each dimension needs at least 8/10 matches for advancement, alongside greater
total agreement than control and no new D2/D3 false approval.

| Dimension | V13 matches | V14 matches | Paired change |
| --- | ---: | ---: | --- |
| D1 — Completeness | 9/10 | 10/10 | One improvement |
| D2 — Safety | 10/10 | 9/10 | One false-approval regression |
| D3 — API realism | 10/10 | 9/10 | One false-rejection regression |
| D4 — Scope | 10/10 | 10/10 | Unchanged |
| D5 — Context | 7/10 | 7/10 | Both below threshold |
| D6 — Tips | 10/10 | 10/10 | Unchanged |
| **Total** | **56/60 (93.3%)** | **55/60 (91.7%)** | **One improvement, two regressions** |

V13 has four false approvals and no false rejections. V14 has four false approvals
and one false rejection. Equal false-approval totals conceal a changed error:
fixing C07's completeness miss does not compensate for introducing C03's safety miss.

V14 fails advancement because D5 is below 80%, total agreement is lower than the
matched control, and a new safety false approval appears. The public-explanation
audit also finds a substantive API assertion behind the new false rejection.

## Public-explanation audit

All ten supplied candidates, task briefs, authentic frozen ratings/comments and
120 public justifications were inspected. This is assistant comparison against
retained evidence, not new human scoring, external API verification or execution
of the generated engineering code.

| Case and dimension | Observed difference |
| --- | --- |
| C07, D1 | V13 recognizes invalid lowercase volume access in D3 but calls the listed workflow complete. V14 correctly explains that the invalid access prevents finishing, matching the human review. |
| C03, D2 | V13 rejects the claim that solver success proves the original problem was solved despite a changed equation. V14 passes because there is no physical hazard, ignoring the reporting/interpretation hazard required by its own prompt. |
| C05, D3 | V13 accepts the supplied read-only Revit command. V14 asserts that the Transaction attribute is unsupported, contradicting the explicit human pass rationale and rejecting this correct case relative to the frozen reference. |

All other paired decisions are unchanged. Both prompts pass D5 on C01, C04 and
C08 while the human fails it. The public explanations credit a clearly identified
subject/objective despite the answer failing the required empty-versus-exception,
failed-versus-current-step or type-versus-instance distinction. Retain this
interpretation difference without rewriting the frozen ratings or silently changing
the rubric. Aggregate agreement must not conceal those disagreements.

The remaining matching decisions generally identify details actually present in
the supplied candidate. Some explanations claim source confirmation; this audit
does not turn those claims into independent external verification. Full case notes
are retained in the external semantic-review artifact.

## Execution and verification

| Measure | Result |
| --- | ---: |
| Cases / prompt arms | 10 / 2 |
| Valid first attempts / planned requests | 20/20 |
| Retries / failed responses / unknown outcomes | 0 / 0 / 0 |
| Actual starts / approved maximum | 20/40 |
| Recorded request time | 1940.4 seconds, 32.3 minutes |
| Request duration range | 64.0–111.4 seconds |
| Completion tokens | 79,001 total; 2,572–4,521 per request |

Both arms used identical case bodies, Qwen3.5 weights and request settings. The only
prompt change was the approved V14 draft. The order was V13 then V14 within each
case. The pinned build, context 16384, single slot, 4096 thinking-token cap, 8192
total output allowance, temperature 0.1 and 300-second timeout were unchanged.

All twenty token reservations passed before inference. The owned process command,
parent PID and cap were checked before every request start. All **173 frozen files**
match the original package, the report replays exactly, and three interim inspection
snapshots match the final ledger. All **29 sealed files** from the prior assessed
audit, judge, calibration and analysis remain unchanged. Original human references
are preserved. **441 locked WSL tests**, Ruff and launcher syntax checks passed
before inference; no implementation changed during the run.

Evidence locations are relative to workspace `artifacts/evidence/P1-03/`:

- Prepared bundle: `qualification/MP1-QWEN35-V14-COMPARISON-MAC/`.
- Complete return: `qualification/MP1-QWEN35-V14-COMPARISON-RETURN.zip`, SHA-256
  `4e6bb75cadae64a3ffffd99f5b46954d612dddc4741dcdb5758b66690dd153cd`.
- Extracted return: `qualification/v14-return-20261116/MP1-QWEN35-V14-COMPARISON-MAC/`.
- Audit/replay, public review, ratings CSV, execution summary and semantic notes:
  `qualification/v14-audit-20261116/`.
- Plan identity: `83a8fbce3ec0d5b4a72cb0f52050b988995e06845bca3dbffc40e762bca40096`.
- Human-reference identity: `b8668b09e762b60599fd578ec673b07ab6f3362c7008f192ee82b5fd0341f17b`.
- Implementation: `171aa1b`, frozen before packaging and inference.
- Audit seal: `665ab2ba886d52aa024d6f705df875e0164e78f1ad5752a7c48c26d8ac215c05`.

The return and audit are copied to
`\\192.168.0.55\aia\Handoff\P1-03\operator\` with verified hashes. Raw evidence
remains outside Git. The runner's exit code 0 means execution completed; its
report explicitly sets `numerical_advancement_conditions_met` to false.

## Decision and remaining work

The approved allocation is complete and stops here as specified. Do not promote
V14, merge these outputs into assessed evidence or start the third assessed version.
The last assessed allocation remains unused. V13's previous selection is retained,
but its full-cohort calibration still fails; retaining it does not qualify it.

M4 remains incomplete. Before another assessed run, the judge approach needs a
new bounded proposal that addresses both the substantive missed errors and the
context-interpretation mismatch, with the original human labels preserved. Merely
adding more instructions has not demonstrated a sufficient improvement in this
comparison. These ten exposed cases cannot establish generalization to the baseline.
M5 correction/new human review and M6 demonstration/acceptance remain subsequent work.
