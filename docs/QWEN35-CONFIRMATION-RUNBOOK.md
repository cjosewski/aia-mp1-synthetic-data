# Ten-item blind confirmation review

Your next task is to read ten technical answers and give your own D1–D6 ratings.
This checks a promising judge configuration on fresh examples. It is separate from
your frozen twenty-item baseline and earlier ten-item review. No model scores or
suggested human answers are included. You do not need to run code, Herd or the
engineering applications.

## On the Mac

1. In Finder, choose **Go → Go to Folder** and paste:
   `~/AIA/MP1-handoff/qwen35-v4-blind-confirmation-v1`.
2. Open `RUNBOOK.md`, then `REVIEW-PACKET.md`. The packet contains the rubric,
   ten reference tasks, candidate answers and source notes.
3. Open `MY-ANSWERS.md` in a text editor. Fill in your name, date and assistance
   used. Enter **Yes** for the personal-adoption and blind-review declarations
   only if they are true. If either is not true, describe the circumstances.
4. For C01, read the task and all seven answer fields. Replace each underscore
   after D1–D6 with your own **0** (fail) or **1** (pass). Add a brief comment
   identifying the decisive facts. Leave uncertain ratings blank and explain;
   an unresolved rating is not a pass.
5. Repeat for C02–C10. Keep the packet ID, item IDs and heading/rating format.
   Save after each item. There is no target pass rate and no need to repair the
   candidate answers.
6. Save `MY-ANSWERS.md` and tell Codex it is saved. Give the path if you used a
   different copy. Codex will preserve the exact submission and check that it is
   complete; it will not supply missing human judgments.

The same packet is on the NAS at
`\\192.168.0.55\aia\MP1-handoff\qwen35-v4-blind-confirmation-v1` and on Windows at
`D:\_Repos\_AIA\artifacts\evidence\P1-03\qualification\qwen35-v4-blind-confirmation-v1`.
Edit only one copy. You may revise that copy before submission. After freezing,
request a separate amendment so the original record remains intact.

Use authoritative sources when needed and disclose assistance. Do not ask either
comparison model to score these examples before completing the blind review.
Disclose accidental exposure to model judgments. These are assistant-authored
challenge examples, not measured generator outputs or a representative sample.

## Operator continuation

The distributed manifest SHA-256 is
`77b264b030e129cc839663ab68c92d04a72ab67c9804187020ed880f9bc702a6`.
The local `aia_mp1.confirmation_review` module checks this identity, all immutable
files, source permissions, category balance and exact reconstruction of model
messages. It requires ten explicit binary reviews, comments, reviewer/date,
assistance attribution and affirmative adoption/blind declarations. It preserves
the submitted bytes in a new external directory and checks parsed decisions
against them on reload. Software records declarations; it does not authenticate
human authorship or independently prove absence of exposure. The complete locked
WSL suite passes 388 tests, including thirteen synthetic confirmation-intake tests.
The actual unfilled packet is correctly rejected without creating a reference.

Run the following **in WSL Ubuntu from the repository**, after sourcing
`tools/environment.sh`. This is a read-only completeness check, not a command the
human reviewer needs to run:

```bash
uv run --locked python -m aia_mp1.confirmation_review \
  --packet ../artifacts/evidence/P1-03/qualification/qwen35-v4-blind-confirmation-v1 \
  --manifest-sha256 77b264b030e129cc839663ab68c92d04a72ab67c9804187020ed880f9bc702a6 \
  --answers /path/to/the/actually/submitted/MY-ANSWERS.md
```

Only after inspecting the actual submitted file and exposure declarations, repeat
with `--freeze-to` naming a new directory outside Git. Incomplete submissions
create no reference. Existing freeze directories are never overwritten; partial
writes require inspection. Preserve the submitted copy and its SHA-256 locally
and on the NAS. Do not freeze a template or copy assistant suggestions into it.

The separate [confirmation transport](CONFIRMATION-TRANSPORT.md) now implements
the two-model runner and portable bundle preparation. It requires the frozen
authentic review before it can prepare a real plan or package. After review freeze,
freeze that executable package before any model request. The known-case runner
remains separate; never rename the new case IDs to make it accept them. Run the candidate
Qwen3.5-122B-A10B and generator Qwen3-30B-A3B on identical messages with V13,
temperature 0.1, 8192 output tokens, 300-second timeout, native thinking, build
b12110-cd959bae9, context 16384 and one slot. Verify each model/template/token fit.
The packet allocates at most forty new starts after 190, at most two per
case/model; stop on two consecutive failures or an unknown outcome. Preserve
all attempts and stop only the owned server. Do not load both models concurrently.

Report exact per-dimension agreement, false approvals/rejections, initial validity,
recovery, coverage, public explanations and timing for both models. Preserve
regressions and ties. Model size, vendor benchmarks and earlier prompt-selected
screens do not establish superiority. A defensible selection requires the matched
evidence and its limitations; no automatic qualification receipt is issued.
Assessed Phase A still requires complete fifty-item judging and at least 80%
agreement in every dimension against the frozen twenty-item reference. Phase B
and the later twenty corrected reviews remain separate.
