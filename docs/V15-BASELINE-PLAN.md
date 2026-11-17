# Final V15 original-baseline evaluation

November 17, 2026. The [fresh paired confirmation](V15-CONFIRMATION-RESULTS.md)
supports selecting Qwen3.5 with V15 for this bounded assessment, with both safety
misses and both context regressions retained. Chad's standing authorization to
pursue completion at the original **80% in every dimension** covers this work.
No new owner quote or instructor acceptance is implied.

The question is whether V15 transfers to the original assessed baseline. The
reported 93.3% fresh-confirmation result and 96.7% exposed-development result
cannot replace its saved 72.5% V13 result. This run will evaluate the **same fifty
items against the same twenty frozen human reviews** and retain paired changes.
Do not tune the prompt further on the completed confirmation examples.

## Frozen allocation

| Control | Value |
| --- | --- |
| Assessment | `baseline-review-001`, unchanged fifty items and five categories |
| Assessment SHA-256 | `dd0cfe746464e441ce42f1dfd706af7b65e10a2c3b8b2b304709b877a4f06932` |
| Human reference SHA-256 | `1e555ed74a0417120ac4d16052c3082e02e8e03550c3e2e09a64eda89856e4a8` |
| New judge run | `baseline-qwen35-v15-budget4096-003` |
| New report | `baseline-qwen35-v15-budget4096-agreement-003` |
| Model | Pinned Qwen3.5-122B-A10B Q4_K_M, identical to fresh confirmation |
| Prompt | `judge-v15-task-contract`, SHA-256 `0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d` |
| Client | WSL2 Python; JSON mode; temperature 0.1; 8192 output tokens; 300-second timeout |
| Native server | Mac build `b12110-cd959bae9`; 16384 context; one slot; reasoning on/deepseek; 4096 reasoning-token cap |
| Budget | Third and final existing assessed version; fifty initial requests, two attempts/item, at most 100 starts |
| Stop | Two consecutive unsuccessful responses, unknown outcome, changed identity, context overflow or damaged evidence |
| Prior cumulative starts | 338, including historical failures and interruptions |

All six rubric anchors, cohort selection, generator outputs and human labels are
unchanged. The model receives each task, answer and authorized source context;
human labels/comments, prior model decisions and qualification reports are not
included in its requests. Comparing to the existing human sample establishes
calibration, not independent generalization. Disclose the known D4 interpretation
difference rather than altering labels or anchors to improve agreement.

## Preparation and execution

The new `tools/v15_baseline.py` reuses the existing assessed judge ledger,
calibration implementation, exact-wire transport and runtime guards. It adds a
separate pinned V15 plan and WSL-to-Mac preflight. Historical V13 code and bundles
remain unchanged. No automatic resume is exposed for this final allocation.
An interrupted run must be inspected without resetting its files or budget.

Preparation verification: **493 tests passed in 115.17 seconds** in the locked
WSL analysis environment with the optional PDF renderer. Ruff lint/format passed.
Ten new synthetic tests exercise original-input binding, label exclusion from
requests, evidence/settings tampering, prior-version preservation, threshold
tampering, WSL/frozen-code requirements and changed-process rejection before the
first request start. The existing native-client tests cover failure boundaries
and exact-wire/runtime changes. These are software checks, not model outcomes.

The package builder `tools/prepare_v15_baseline.py` copies committed code,
the attributed V15 qualification and the complete original baseline evidence,
including both previous assessed versions. It rejects missing/tampered reviews,
altered model/settings, extra or missing prior allocations, active source writers,
symlinks and existing output paths. The new package is
`qualification/MP1-QWEN35-V15-BASELINE-003`, outside Git. Raw source material stays
within the approved local coursework scope.

After tests pass and the implementation is committed, prepare in WSL:

```bash
uv run --locked python tools/prepare_v15_baseline.py \
  --evidence-root ../artifacts/evidence/P1-03 \
  --qualification ../artifacts/evidence/P1-03/qualification/qwen35-v15-assessed-selection-003 \
  --destination ../artifacts/evidence/P1-03/qualification/MP1-QWEN35-V15-BASELINE-003
```

Warn Chad before using the Mac. Verify its availability and port 8081, copy and
checksum the packaged launcher, and use the same owned native launcher with
argument `candidate`. The remote root is
`/Users/chadjosewski/AIA/MP1-handoff/MP1-QWEN35-V15-BASELINE-003`.
Use an SSH loopback tunnel from workstation port 18081 to Mac port 8081. The Mac
runs only inference; Python and dependencies remain in WSL. Do not change Herd.

From the frozen package's `project` directory in WSL, use a separate persistent
environment and run:

```bash
uv run --locked python tools/v15_baseline.py verify ..
uv run --locked python tools/v15_baseline.py execute ..
```

Preflight verifies both weight shards, template/build, exact owned process and
all fifty token reservations. Before each request the process and server
properties must still match. Retain the terminal/client log and every ledger
start/completion. An exit of 1 can mean calibration failed despite complete
execution; inspect the saved report before interpreting it as a transport error.

Stop only the owned server by creating `candidate/STOP` under the remote root.
Wait on the same SSH session, retrieve `candidate/runtime`, and verify the owned
PID is absent and the port is clear. Preserve all preflight/transport failures.
The launcher also has a four-hour maximum lifetime; reaching it preserves an
incomplete run and does not authorize another launch or request allocation.

## Audit, import and decision

1. Verify the complete package and replay the report with `report ..`. Inspect
   all twenty human-paired answers and 120 public explanations; preserve false
   approvals/rejections and unsupported reasoning even when a decision matches.
2. Compare V13 and V15 on the same human reference: per-dimension counts, paired
   gains/regressions, confusion counts and original failure detection. Keep the
   [discrepancy record](AGREEMENT-DISCREPANCY-20261117.md) current.
3. Recheck every copied canonical input before importing only the new judge and
   calibration directories. Refuse collisions or changed source evidence.
   Archive the complete return locally/NAS and verify checksums.
4. Require complete fifty-item coverage and **at least 16/20 agreement separately
   in D1–D6**. Preserve a failed result; no fourth assessed version, threshold
   change, post-hoc rescoring or additional allocation follows automatically.
5. If ready, freeze this judge for both cohorts, inspect the measured worst
   baseline category/dimension, and determine whether the existing generator
   correction addresses it before Phase B claims. Twenty authentic corrected
   reviews, corrected judging, all quality thresholds, charts and final demo/
   coaching acceptance remain separate requirements.
