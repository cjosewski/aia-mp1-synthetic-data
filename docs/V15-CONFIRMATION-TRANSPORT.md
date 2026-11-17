# V15 fresh confirmation: operator procedure

This procedure is for Codex after Chad completes the new ten-item review. It
replaces the old V13 transport for this packet only; historical bundles and
ledgers remain unchanged. Python runs in WSL2 Ubuntu. The Mac runs only the owned
native inference server. No production default or Herd setting changes.

The distributed packet is `qwen35-v15-blind-confirmation-v1`, manifest SHA-256
`1098fb60c1497828deae342a7dc68a7647ae49f4952ee95258417947c7db1c07`.
The V15 prompt hash is
`0ff6b3170ff6a412d5c7846dc936e5ff699820c1f212d5592419eba2abe8b28d`.
Both identities are pinned in the runner. The packet remains immutable; only
Chad's answer sheet is editable until it is submitted and frozen.

## Protocol and limits

Qwen3.5-122B-A10B Q4_K_M is the candidate; Qwen3-30B-A3B Q4_K_M is the comparator.
Both receive the same ten exact V15 messages, rubric and source context. Human
ratings, reviewer comments and prior judgments are reporting inputs only.
The candidate runs first, then the comparator, so fixed order remains a limitation.

Both phases use temperature 0.1, 8192 total output tokens, 4096 reasoning tokens,
16384 context, one slot, native thinking and a 300-second timeout. Model weights,
build `b12110-cd959bae9` and each model's own template are checked before dispatch.
The client also validates all ten requests against the context limit without
truncation. It verifies the exact owned server command and parent, then requires
the same process identity before every request.

One append-only ledger covers twenty initial requests and at most forty starts
after the recorded prior total of **318**. Two attempts per case/model maximum;
stop after two consecutive invalid/transport outcomes. Switching models cannot
reset failures. An unknown outcome, identity change or context overflow prevents
new dispatch. The old externally interrupted V13 recovery does not authorize
recovery here. Preserve failures and obtain a specific disposition instead of
deleting markers, restarting the ledger or spending another allocation.

## 1. Verify and freeze the actual human submission

Use the NAS answer file in
`\\192.168.0.55\aia\Handoff\P1-03\qwen35-v15-blind-confirmation-v1`.
Preserve its exact bytes locally after Chad submits it. Check all ten item IDs,
sixty ratings, comments and truthful assistance/exposure declarations. Never fill
missing ratings or declarations on Chad's behalf.

From the repository in **WSL**, after setting `AIA_MP1_TOOLS` and sourcing
`tools/environment.sh`, run the existing `aia_mp1.confirmation_review` module
with the pinned packet/hash, exact submitted answer file and a new freeze
destination `../artifacts/evidence/P1-03/qualification/qwen35-v15-human-reference-001`.
Inspect the preserved submission and reference hash. The builder below fails
before creating output if that complete authentic reference is missing.

## 2. Freeze committed code and the comparison package

Commit and publish reviewed code before preparing the bundle. In **WSL**, from
the repository:

```bash
uv run --locked python tools/prepare_v15_confirmation.py \
  --packet ../artifacts/evidence/P1-03/qualification/qwen35-v15-blind-confirmation-v1 \
  --manifest-sha256 1098fb60c1497828deae342a7dc68a7647ae49f4952ee95258417947c7db1c07 \
  --review ../artifacts/evidence/P1-03/qualification/qwen35-v15-human-reference-001 \
  --destination ../artifacts/evidence/P1-03/qualification/MP1-QWEN35-V15-CONFIRMATION-001
```

The bundle contains the Git archive, immutable packet, exact submitted review,
frozen plan, launcher and checksums. It excludes the editable answer sheet.
Existing destinations/archives are never replaced. Any partial preparation
remains for inspection. Do not use the earlier `prepare_confirmation_bundle.py`,
which intentionally retains the V13 protocol and historical count.

Use the resulting `project` directory for every verification, execution and
replay. Source its environment script, then set a dedicated Linux environment:

```bash
export UV_PROJECT_ENVIRONMENT="$AIA_MP1_TOOLS/v15-confirmation-venv"
uv run --locked python tools/v15_confirmation.py verify ..
```

The execute command rejects imports from a different source checkout. This keeps
the actual client code aligned with the committed package.

## 3. Start one owned Mac phase

Warn Chad before using the Mac and check its current availability. Verify the
bundle first in WSL. Copy and checksum-verify the packaged `run-on-mac.sh` to:
`/Users/chadjosewski/AIA/MP1-handoff/MP1-QWEN35-V15-CONFIRMATION-001/`.
Python and the evidence ledger remain in WSL; the Mac needs the launcher and the
already pinned weight files, not a Python environment.

Open an SSH session that forwards local loopback port 18081 to Mac loopback
8081, with `ExitOnForwardFailure=yes` and keepalives. Use the existing project
SSH identity and verified host key. In that foreground session, run:

```bash
bash /Users/chadjosewski/AIA/MP1-handoff/MP1-QWEN35-V15-CONFIRMATION-001/run-on-mac.sh candidate
```

The launcher refuses an occupied port, writes an exclusive phase invocation
marker and owns only its child server. Allow model loading; verify the health
endpoint through the tunnel before starting the WSL client. A health timeout
is not evidence that a live process stopped: inspect the existing SSH handle
and server logs without starting a replacement.

From the frozen bundle's `project` directory in **WSL**:

```bash
uv run --locked python tools/v15_confirmation.py execute .. --phase candidate
```

Runtime preflight verifies the model, command, template and exact token
reservations before the first start. Every request start is written before
dispatch and every result/error is retained. Inspect the exit status, ledger and
candidate report before proceeding.

Create `candidate/STOP` under the remote bundle root to stop the launched server.
Wait on the same SSH session, inspect its terminal status, retrieve
`candidate/runtime/` and verify the owned PID is absent and port 8081 is clear.
Do not stop unrelated processes. The launcher also has a four-hour maximum
lifetime and bounded cleanup.

Only after ten valid candidate judgments and successful cleanup, repeat the
same steps with `comparator` in the launcher, client `--phase` and STOP path.
The comparator uses its own pinned template and single weight checksum, the
same reasoning cap and the same shared ledger. Its preflight cannot bypass a
candidate failure boundary.

## 4. Audit and report

After both phase servers are confirmed stopped, copy their complete runtime
logs/status receipts into separate phase directories beside the local results.
Replay from the frozen project in **WSL**:

```bash
uv run --locked python tools/v15_confirmation.py verify ..
uv run --locked python tools/v15_confirmation.py report ..
```

Inspect every public justification against the reviewed answer and source
context, including matching decisions. Retain initial validity, retries,
unresolved cases, timing, false approvals/rejections and all regressions.
Archive the complete package and returns locally/NAS with checksum verification.

Selection must be justified by the matched candidate/comparator evidence and
its limitations; the report does not automatically qualify a judge. Keep the
[documented score discrepancy](AGREEMENT-DISCREPANCY-20261117.md) visible. This
small authored challenge screen cannot establish assessed improvement. A
supported selection must still be followed by the remaining original-baseline
assessment, with at least **16/20 matches in every dimension** and complete
fifty-item coverage, before a calibrated Phase B comparison.

## Preparation boundary

The new runner and package builder are implemented offline. Synthetic tests
exercise human-reference gating, pinned protocol, matched two-model inputs,
shared failure limits, package tampering, phase-specific weights/templates,
reasoning-cap mismatch, context overflow and changed-process rejection before
a request start. Test declarations and completions are synthetic and are not
added to project evidence. Real packaging and model execution remain gated on
Chad's authentic review. No new model measurements are claimed by this work.

November 17 verification: **483 tests passed in 102.14 seconds** in the locked
WSL analysis environment with the optional PDF renderer; Ruff and launcher
syntax checks passed. The real NAS answer-sheet snapshot was rejected as blank.
Attempting to package the real packet without its human reference failed before
creating a bundle or ZIP. No Mac connection or model request occurred. The
dated receipt is under external evidence
`qualification/v15-confirmation-preparation-20261117/`.
