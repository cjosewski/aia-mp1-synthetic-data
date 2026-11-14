# Fresh confirmation transport

This operator procedure follows the [human review](QWEN35-CONFIRMATION-RUNBOOK.md).
The software is implemented and tested offline. A real confirmation plan, package,
native preflight and model calls remain pending the authentic frozen reference.
No production model or prompt default changes.

Verification: 409 locked WSL tests pass, including 21 transport/bundle tests using
synthetic inputs, declarations and completions only. Ruff lint/format and Bash
syntax checks pass. The actual packet cannot produce a package without its
missing human reference; that negative check created no output directory.

## Contract

`aia_mp1.confirmation_transport` runs Qwen3.5-122B-A10B first, then Qwen3-30B-A3B,
on the same ten original confirmation IDs and exactly the same message bodies.
Only the requested model changes. Each phase uses JSON-mode Instructor,
temperature 0.1, 8192 output tokens and a 300-second timeout. Native thinking is
enabled by the embedded model templates; no `reasoning_effort` field is sent.
Both phases require the recorded native Mac, build b12110-cd959bae9, context 16384
and one slot. This fixed order is not a randomized performance experiment.

The distributed packet manifest is pinned. The loader verifies the review's
exact submitted bytes and parsed decisions, reconstructs all model messages from
the immutable packet, and compares the resulting plan with the saved plan. Human
ratings/comments never enter model messages. The protocol retains the original
V13 system prompt, rubric, sources and cases without tuning on confirmation scores.

A single append-only ledger covers both phases. It allows at most forty new
starts after the verified prior total of 190, and at most two attempts per
case/model. Every start is flushed before dispatch. A shared stop after two
consecutive invalid/transport outcomes applies across the model boundary; starting
the comparator cannot reset a failed candidate run. A start without a result is
an unknown outcome and prevents new dispatch. Replay checks order, phase, exact
wire, raw completion, parsed judgment and lineage hashes. Completed phases cannot
be rerun in the same ledger. Never create a replacement ledger to bypass a stop.

Native preflight verifies both candidate shard hashes, the comparator's single
weight hash, served identity, build, context, slot count, thinking-channel opening
and every exact request's token fit. Every execution repeats preflight and checks
it against the first observation. The server's random unused media marker is the
only ignored runtime field. Runtime drift or overflow prevents dispatch.

Reports preserve selected denominators, unresolved cases, initial-attempt validity,
retry recovery, total starts, timing, exact agreement and false approvals/rejections
for each dimension/model. Reports do not qualify a model automatically. Inspect
every public explanation and retain all disagreements before a selection decision.

## Prepare after the human review is complete

Use WSL Ubuntu from the repository. Source `tools/environment.sh`. First preserve
and verify the submitted file with `aia_mp1.confirmation_review`, as described in
the human-review runbook. Resolve incomplete or ambiguous declarations with Chad;
the assistant cannot enter missing ratings or claim an exposed review was blind.

Commit the reviewed transport implementation before packaging. The builder rejects
tracked changes and uses the committed Git archive, not an arbitrary worktree.
Choose a new destination and real frozen review directory; the following names
are examples, not claims that those artifacts already exist:

```bash
uv run --locked python tools/prepare_confirmation_bundle.py \
  --packet ../artifacts/evidence/P1-03/qualification/qwen35-v4-blind-confirmation-v1 \
  --manifest-sha256 77b264b030e129cc839663ab68c92d04a72ab67c9804187020ed880f9bc702a6 \
  --review ../artifacts/evidence/P1-03/qualification/qwen35-v4-human-reference-001 \
  --destination ../artifacts/evidence/P1-03/qualification/MP1-QWEN35-CONFIRMATION-MAC
```

The builder freezes committed code, immutable input files, the exact submitted
review, plan and launcher. It writes a manifest and ZIP without replacing an
existing destination or archive. Partial failures remain available for inspection.
Review the output hashes, then copy and hash-verify the ZIP on the NAS and Mac.
Keep raw reviews and outputs outside Git and within the approved local audience.
Unpack in a new Mac folder under `~/AIA/MP1-handoff`.

## Execute on the authorized Mac

Announce before starting the owned server. Use SSH or a Mac Terminal and change
to the newly unpacked bundle root. Do not invoke the repository's launcher in
place: its packaged copy expects `project`, `packet`, `review` and `plan.json`.

Run one command at a time and inspect each result before proceeding:

```bash
bash run-on-mac.sh candidate preflight
bash run-on-mac.sh candidate execute
bash run-on-mac.sh comparator preflight
bash run-on-mac.sh comparator execute
```

Each command validates the package, human reference and permitted next phase
before starting a service. An occupied port 8081 stops the operation. Only the
launcher-owned child process is stopped on exit; services belonging to Herd or
other tasks are preserved. The launcher records startup, server logs, PID, exit
status and actual cleanup outcome. It has a bounded startup wait and bounded
termination grace period. Each phase/mode has an exclusive invocation marker;
inspect failed/partial invocations instead of deleting markers or rerunning them.

After both phases finish and both owned servers are confirmed stopped, create a
return ZIP of the entire bundle, copy it locally, verify its SHA-256, and replay
the frozen code against the returned packet, reference and ledger. Within the
returned `project` directory, the read-only reporting command is:

```bash
uv run --locked python -m aia_mp1.confirmation_transport report \
  --plan ../plan.json --packet ../packet --review ../review \
  --directory ../results/ledger
```

The returned bundle verifier checks immutable files before the report is trusted.
Archive the full return, raw completions, failed attempts, public-explanation audit
and report locally/NAS. Record the actual cumulative start count; unused budget is
not measured activity. Do not combine favorable ratings from different screens.

## Remaining qualification gates

The ten authored challenge cases are not a representative sample or an assessed
cohort. Shared model family, domain overlap and fixed execution order remain
disclosed. Evaluate the matched evidence rather than claiming superiority from
parameter count or development-set performance. Any selection basis must explain
regressions, ties and unsupported justifications. A qualified distinct judge still
needs full fifty-item baseline judging and at least 80% agreement in every
dimension against the frozen twenty authentic baseline reviews before Phase B.
