# Proposed limited-thinking feasibility probe

**Status: approved and completed. Both cases returned valid first attempts; the
Mac is free.** Chad replied "Approved." to the prepared two-case, four-request
proposal. No full assessed rerun was authorized or started by this probe.

The [frozen assessed run](ASSESSED-BASELINE-RESULTS.md) retained three responses
that used all 8192 tokens in reasoning and returned no final ratings. The pinned
`llama-server` build's captured `--help` documents `--reasoning-budget N`: default
`-1` is unrestricted, and positive N sets a thinking-token budget.

## Exact proposed change

Add **`--reasoning-budget 4096`** to the dedicated project server's existing launch
command. Retain Qwen3.5-122B-A10B Q4_K_M, V13, JSON mode, temperature 0.1, total
output allowance 8192, timeout 300 seconds, context 16384, one slot, reasoning on
and deepseek response format. The hypothesis is that ending thinking earlier will
leave enough output allowance for the six public ratings and explanations.

Use only the two affected saved inputs, in this order:

1. `baseline-001-b01-item-0015`
2. `baseline-001-b01-item-0028`

Copy their exact messages from the original frozen native plan. Supply no human
labels, reviewer notes or earlier model judgments to the model. This is a
development-only feasibility check on known cases, not another assessed run or a
fresh independent confirmation.

## Bounds and decision rule

- At most two starts per case, four total; stop after two consecutive unsuccessful
  responses or any unknown request outcome. Preserve every response and failure.
- Verify frozen source files, exact inputs, model weights, native template,
  context fit and the owned server's actual command line before inference.
- Success requires two complete schema-valid judgments from the expected model.
  Inspect output limits and public explanations afterward; technical success alone
  does not establish accurate judging or calibration.
- The original assessed run remains interrupted and immutable. Its exhausted item
  receives no extra assessed attempt. A subsequent assessed revision requires an
  explicitly recorded runtime amendment and a new run identity.
- No automatic full 50-item run follows this probe. Report the measured outcome
  and a concrete next-step recommendation first.

## Approval and Mac use

The package refuses execution without an attributed owner-approval receipt bound
to its frozen plan. Approval is needed because the requested 4096 thinking cap
changes the runtime settings Chad explicitly froze in his selection instruction.
This requirement comes from that instruction, not a new skill approval rule.

Approval text:

> Approve the two-case Qwen3.5 thinking-budget probe with a 4096 thinking-token cap and at most four requests. Preserve the frozen assessed run and all errors.

Codex announced Mac use, ran the approved probe, verified its return and announced
release. The owned server is stopped, its PID is gone and port 8081 has no listener.

## Prepared package

The package is frozen from commit `03d439ea62ce302d86bf1ab767917057acd54b85` and
verifies 151 files. Before approval, its missing receipt was checked to block
execution. The immutable preparation receipt records that earlier zero-request
checkpoint; the approved execution result is recorded below.

- Local: `qualification/MP1-QWEN35-BUDGET-PROBE-MAC/` under the external evidence root.
- NAS archive: `\\192.168.0.55\aia\Handoff\P1-03\operator\MP1-QWEN35-BUDGET-PROBE-MAC.zip`.
- Plan SHA-256: `26432836b166d8663d79f72a7a4c8eda3b03dafb0c3dc5793cd80806f82f0e24`.
- Archive SHA-256: `6688f2f228eb83008c13fa1bb0a79409adea88e0b6cf54e748361378db9356ed`.

The attributed `owner-approval.json` records Chad's exact reply, "Approved.", at
2026-11-16 04:18 UTC, bound to the plan above. Its byte SHA-256 is
`ae7836ee05bac5700c0f1a6c3e1e5b40249292c9707d7804104e844155703495`.
Original bundle files and the prior assessed evidence remain unchanged.

## Measured result

Completed November 15 local time (November 16 UTC), with **two starts, two complete
first-attempt judgments, zero retries and zero failures**. Both returned the expected
model identity and `finish_reason: stop` with nonempty public JSON.

| Case | Request time | Completion tokens | Public content characters |
| --- | ---: | ---: | ---: |
| `b01-item-0015` | 105.9 s | 4438 | 1144 |
| `b01-item-0028` | 106.3 s | 4532 | 1846 |

Total recorded request time was 212.2 seconds. The actual owned-server command
included `--reasoning-budget 4096`; weights, native template and context-fit checks
passed. All 151 frozen package files and the approval receipt verify. Independent
ledger replay reproduces both outcomes. The original assessed attempts remain
byte-identical, including all three 8192-token failures.

All twelve public justifications were inspected against the supplied items and
reference context. The first case correctly receives D1/D5 failures for changing
the specified ODE and initial conditions. Its D3 pass explanation only establishes
API existence and does not address the candidate's incorrect row/time statement,
which conflicts with the supplied source summary. That semantic concern and its
terse D6 explanation are retained; no human rating is invented for this item.

The second case matches its existing frozen human reference on **6/6 criteria**.
That is one known human-reviewed example, not a new independent sample. Its
previously noted `nodeDisp(nodeTag, 1/2)` notation ambiguity remains disclosed.

This supports **technical feasibility on these two known cases**. It does not
establish full-cohort completion, accuracy, calibration or the absence of future
truncation. The [proposed full baseline revision](BASELINE-BUDGET-AMENDMENT.md)
would measure those requirements under a separately recorded runtime amendment.

### Retained return

- Archive: `qualification/MP1-QWEN35-BUDGET-PROBE-RETURN.zip`.
- Archive SHA-256: `8e6d687ad28694f92e60a1e616fe23bfeeb6f87d6efc770f123c59665abb7d7a`.
- NAS: `\\192.168.0.55\aia\Handoff\P1-03\operator\MP1-QWEN35-BUDGET-PROBE-RETURN.zip`.
- Audit: `qualification/budget-probe-audit-20261116/`, including verification,
  public results and the assistant's semantic review.

The runtime and implementation were unchanged during this probe. The existing
430-test checkpoint applies; no software changes or additional test claims were
needed for this execution and documentation update.
