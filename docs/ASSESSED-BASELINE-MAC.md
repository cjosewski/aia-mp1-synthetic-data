# Selected Qwen3.5 assessed baseline calibration

Chad selected Qwen3.5-122B-A10B on November 15, 2026 local time (November 16 UTC):

> Select Qwen3.5-122B-A10B for assessed baseline calibration using the frozen V13 prompt and settings, with the reported errors retained.

The attributed receipt is retained outside Git at
`qualification/qwen35-assessed-selection-001/qualification.json`, with byte SHA-256
`66fc2d669c3365c08c30d651a800c4a2165ca9d42ac3e6f951a8b56211092a48`.
It includes the [matched comparison and its errors](CONFIRMATION-RESULTS.md).
The owner selection is complete. The [first assessed run and replay](ASSESSED-BASELINE-RESULTS.md)
are now recorded: 11/50 complete judgments, three retained token-limit failures,
and an enforced stop. Calibration remains pending; the Mac is free. The approved
[two-case budget probe](REASONING-BUDGET-PROBE.md#measured-result) now completes
both first attempts. The [proposed full-run amendment](BASELINE-BUDGET-AMENDMENT.md)
needs approval to apply that runtime change to assessed judging. No new human
ratings are requested.

## Frozen experiment

- Assessment: `baseline-review-001`, all 50 retained items across five categories.
- Human comparison: the original frozen 20 reviews, not the ten confirmation cases.
- Judge run: `baseline-qwen35-v13-001`.
- Prompt: `judge-v13-hazards`; SHA-256
  `66e59f09239a13e5a99919e95fbadff5094b30f4b309068e2bdfffba63efd000`.
- Same selected Q4_K_M weights and native thinking template; llama.cpp build
  `b12110-cd959bae9`, context 16384, one slot, reasoning on / deepseek format.
- JSON mode, temperature 0.1, 8192 output tokens, 300-second request timeout.
- At most two starts per item / 100 total. Two consecutive unsuccessful judgments
  stop the run. Each start and its completion or failure remain in the canonical
  assessed ledger. An unknown outcome requires inspection before any continuation.
- All six dimensions need at least 16/20 matches (80%), with complete 50-item judge
  and 20-item human coverage. Selection alone does not satisfy this gate.

The portable bundle copies the entire baseline provenance chain, original labels,
qualification evidence and committed implementation. Hash verification, model
weight verification and native token-fit checks precede inference. Human ratings
are available only to validation/reporting; model requests contain the frozen
rubric, generated item and task reference context.

## Operator execution

Codex prepares and verifies `MP1-QWEN35-BASELINE-MAC`, announces Mac use, and runs
`bash run-on-mac.sh` from that bundle. The launcher refuses an occupied port 8081
or an existing invocation marker. It starts an owned loopback server and stops
only its own child process when finished or interrupted. It makes no Herd changes.
The native wrapper checks server identity and health before recording each new
request start, preventing a known stopped server from creating phantom requests.

An interruption preserves all files. Do not delete markers, edit ledgers, change
the frozen code or rerun the launcher to clear a stop. Codex inspects the outcome
and remaining attempt budget first. A deliberate continuation must use the same
frozen bundle and the wrapper's explicit `--resume` after owned-server preflight;
the two-failure and unknown-outcome stops remain enforced.

When the run ends, Codex releases the Mac, archives results, verifies unchanged
inputs and replays the assessed ledger locally before importing new judge and
calibration directories. No existing source or human-reference file is overwritten.
The next action depends on the measured agreement; generator correction follows
only when the assessed calibration gate passes.
