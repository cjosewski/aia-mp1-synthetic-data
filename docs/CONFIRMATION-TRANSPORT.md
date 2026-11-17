# Fresh confirmation transport

**Historical V13 procedure:** the new V15 packet uses the separate
[V15 confirmation operator procedure](V15-CONFIRMATION-TRANSPORT.md), WSL client,
4096 reasoning cap and prior count 318. Do not apply the historical commands or
recovery amendment below to the V15 review.

This operator procedure follows the [human review](QWEN35-CONFIRMATION-RUNBOOK.md).
The software is implemented and tested offline. Chad's resubmitted ten-item
review was frozen on November 16 UTC (November 15 local), before model calls.
All ratings and added pass reasons are preserved; the earlier submission remains
separate. The frozen reference is `qualification/qwen35-v4-human-reference-001`
under the external evidence root. Plan/package preparation and native preflight
can now proceed.
No production model or prompt default changes.

Verification: 413 locked WSL tests pass, including 21 transport/bundle tests using
synthetic inputs, declarations and completions only. Intake tests cover exact-byte
preservation, added rationale, missing comments and rewritten parsed notes. The
earlier missing-reference negative check created no output directory.

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

### Recorded external interruption amendment — November 15, 2026

The first live run completed C01–C06, then recorded two connection failures for
C07. Chad confirmed that another session killed the Mac server, requested a hold,
and later stated that the Mac was free. The interrupted return is preserved as
`MP1-QWEN35-CONFIRMATION-INTERRUPTED.zip` (SHA-256
`efe646cc41b5a872b592aa809f8d827b2f58a9a020c6650dd381353e46ab31a4`).

This is an explicit recovery amendment to the original two-attempt protocol,
not an unchanged-protocol result. The `recover` command records the attributed
incident and availability statements and binds every original start/result byte
hash. It permits exactly one third attempt for the interrupted case. The original
eight starts still count toward the same forty-start limit, and neither the six
successful judgments nor the frozen review/messages/settings are replaced.
There is no new ledger or new human review. Unknown outcomes, malformed responses,
earlier failed cases and an exhausted total budget do not qualify for this recovery.
Only one amendment is supported. Subsequent consecutive failures still stop the run.

Recovery code and its launcher are frozen separately beside the original bundle;
the original code, markers and logs remain intact. The recovery launcher verifies
both code packages, uses distinct invocation/log names, and repeats native
preflight before dispatch. Reports include the amendment and retain the failed
first attempt in initial-validity accounting. The original partial result remains
separately reproducible with its original frozen code.

Native preflight verifies both candidate shard hashes, the comparator's single
weight hash, served identity, build, context, slot count, thinking-channel opening
and every exact request's token fit. Every execution repeats preflight and checks
it against the first observation. The server's random unused media marker is the
only ignored runtime field. Runtime drift or overflow prevents dispatch.

The initial comparator preflight stopped before inference because it incorrectly
required Qwen3.5's prefilled `<think>` opening from both models. Inspection of the
pinned Qwen3 weights' template shows that its enabled/default branch ends at the
assistant prefix; disabling thinking adds an empty thinking block. This agrees
with the [upstream template](https://huggingface.co/Qwen/Qwen3-30B-A3B/blob/main/tokenizer_config.json)
and [Qwen3 mode documentation](https://github.com/QwenLM/Qwen3#switching-thinkingnon-thinking-modes).
The corrected validator accepts only the exact observed comparator template hash
`5da44855ab7e0641774d5ed0ff0b4f89671d01df7d316e54d06557a962211cb4`
and its enabled native prefix. It rejects the disabled branch or changed template.
No template, server argument, message, sampling setting or model weight changes.
The failed preflight and separate zero-generation inspection are retained; the
comparator uses separately frozen corrected code and new invocation markers.

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
