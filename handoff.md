# P1-03 handoff to the Linux session

**November 19, 2026 · Paused during the first online-documentation comparison.** Start by transferring and verifying the checkout and evidence. The Linux host has not been provisioned or verified in this session. At the last process check the MP1 worker and workstation tunnel were stopped, and the dedicated model server on the Mac was down.

## What to move

Run the MP1 session, Python environment, tests, documentation reader and evaluation runner on **Linux**. Keep **Herd on Windows** and use the **Mac for local model inference**. The two verified Qwen model shards are already on the Mac.

| Material | Windows source | Linux destination |
| --- | --- | --- |
| Private implementation checkout | `D:\_Repos\_AIA\aia-mp1-synthetic-data` | A directory named `aia-mp1-synthetic-data` |
| Private evidence, including runs, reference sources and frozen human labels | `D:\_Repos\_AIA\artifacts\evidence\P1-03` | `../artifacts/evidence/P1-03` relative to the checkout |
| Unit 4 exercise review | `docs/UNIT-4-ALIGNMENT.md` in the checkout | Included with the repository. The current review covers 39 exercises in five notebooks. |

The private repository is `github.com/cjosewski/aia-mp1-synthetic-data`. The base is `main` at `2297ccf`. **A fresh clone alone misses the online-documentation experiment.** Copy the following working files byte-for-byte over that base. The experiment records hashes of its Python sources.

- `tools/aec_online_docs.py` and `tools/screen_aec_online_docs.py`
- `tests/test_aec_online_docs.py` and the modified `docs/AEC-COURSE-RUNBOOK.md`
- `tools/screen_aec_single_specialty.py`, an earlier, separate experiment
- This `handoff.md`

Transfer raw evidence privately, outside Git, and verify the copied files against their source checksums. Set up Linux's own authorized SSH connection to the Mac. Keep credentials out of the handoff. The Mac model path, shard hashes, build and launch settings are in the run's `deployment.json`. Its PID and verification timestamp describe the previous deployment.

## Where the experiment stopped

Chad wants the models to consult official documentation directly. The current test changes the **judge** first to measure the effect on the same ten development answers. The local Qwen judge selects up to three publisher pages per case. The workstation reader opens them, the judge receives the returned passages, and a second call scores D1–D6. It uses no document index or vector database. The generator has not been changed.

Let `RUN=../artifacts/evidence/P1-03/aec-course/api-development-qwen-online-docs-001` from the checkout. All item IDs below start with `baseline-001-b04-item-`.

| Case suffix | Saved state |
| --- | --- |
| `0006`, `0047`, `0018`, `0024` | Completed lookup, saved pages and returned six-dimensional judgment |
| `0045` | Completed lookup and saved pages. A judgment start exists with no return. Its outcome is unknown. |
| Remaining five | No lookup or judgment started |

There is a `.writer.lock` and no final `report.json`. Five lookups and four returned judgments are preserved. The interrupted judgment consumed its attempt. **Preserve run 001 intact.** Removing the lock alone cannot resume it because `capture()` also checks the unmatched start. After the migration is verified and work resumes, use a separately identified follow-up run and retain the link to run 001. The current runner hardcodes its run directory, so it needs an explicit new run ID before a clean rerun. Report which ten answers belong to each comparison.

Two early results explain why the full comparison matters. On the Revit Mark-update item, an Autodesk example helped the judge identify a filter method attached to the wrong object. On the ArcPy cursor item, Esri's page helped it reject an incorrect field-order tip, but the judge still approved a procedure that never created the requested `NAME` field. Four returns cannot establish a ten-case agreement rate.

## First checks on Linux

1. From the repository root, confirm `git rev-parse --short HEAD` returns `2297ccf` for the transferred base. Verify the working-file overlay, sibling evidence directory and the four source hashes recorded in `$RUN/protocol.json`.
2. Check the following SHA-256 values against the Linux copy. These identify the frozen protocol, human reference checkpoint and unmatched start.

   | Relative to `$RUN` | SHA-256 |
   | --- | --- |
   | `protocol.json` | `5c4e4f3bd49b072f62bf0e7d098d3190709bb7a983f8bd1eb75ff41e50a66c2a` |
   | `review-checkpoint.json` | `64f0296b39c266dbf18f51a7fc375d27dab9b7adb88c338da4e5333407e829d3` |
   | `documented/baseline-001-b04-item-0045/start.json` | `96d06e4aac8e30e2b750240e9a41e2fbaa22056f5bcb288d79d6d1806d901f9a` |

3. Record the move from the repository's WSL2 Ubuntu convention to native Ubuntu. Recreate the environment from `uv.lock` on Linux. From the checkout run the verification below. The last WSL run passed **840 tests**, including the documentation-reader tests.

   ```bash
   export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
   source tools/environment.sh
   env -u AIA_MP1_DOMAIN uv run --locked --extra analysis --with reportlab python -m pytest -q
   export AIA_MP1_DOMAIN=aec-course
   ```

4. Before a new inference run, confirm that Linux can open publisher pages and reach the Mac over SSH. When Chad resumes model work, verify the original Qwen model, llama.cpp build, 16,384-token context, one slot, 4,096 reasoning budget and temperature 0.1. Forward Linux loopback port 18082 to Mac loopback port 8082 so the local judge configuration continues to work. Use the [AEC runbook](docs/AEC-COURSE-RUNBOOK.md) for the experiment and offline replay.

## Success criteria

Keep all five AEC specialties. D3 uses Chad's version-specific API correctness rule, including any API or MCP operation the answer relies on. The ten-case source-aware control matched **3, 4, 8, 9, 8, 8** times on D1–D6. Compare the documentation-enabled judge against those same answers, count both corrections and regressions, and inspect whether the cited passages support the decisions. Development requires at least 8/10 on every dimension and sound explanations.

The assessed baseline is separate. Its 50 retained items and 20 blind human reviews yielded **12, 15, 12, 17, 13, 11** matches. The requirement is **16/20 on each dimension**. Only D4 qualified. Both original human review passes are complete. Generator correction, a fresh assessed cohort and the final comparison remain downstream of judge calibration. See the [iteration log](ITERATION_LOG.md) and [Unit 4 review](docs/UNIT-4-ALIGNMENT.md).

---

## Historical handoff notes

The entries below preserve earlier decisions and machine snapshots. Use the Linux checkpoint above for current status.

**November 19 specialty comparison.** Ten local Devstral judgments with version-specific checklists scored 4, 5, 4, 9, 7 and 6 matches. The separate D2 safety-field pass approved all ten items. Nine had valid quotes and only four matched the blind review. Offline replay verified the reports and the project ports were released. The full assessed baseline is still below threshold in five dimensions. See the [iteration log](ITERATION_LOG.md) for the evidence and the next Qwen development comparison.

**November 19 checkpoint.** The two Devstral 2 123B Q4_K_M shards are verified on the Mac external drive. Four matched ten-case prompt configurations completed locally. On v3 the D1–D6 counts were 3, 4, 3, 9, 7 and 7. Adding cross-category examples gave 3, 4, 4, 9, 7 and 6. The plain prompt with and without examples approved all 60 decisions. Offline replay verified all 40 judgments, and the Mac project server and tunnel are closed. The [Unit 4 exercise review](docs/UNIT-4-ALIGNMENT.md) covers all 30 exercises in the supplied folder and includes a specialty breakdown. The [iteration log](ITERATION_LOG.md) records the full comparison. The assessed 50-item baseline still qualifies only on D4.

**Current checkpoint, November 18 evening.** Chad completed 20 independent baseline ratings using version-specific API correctness for D3, then ten separate blind development reviews. The final initial judge, v3, scored all 50 retained answers. It matched 12, 15, 12, 17, 13 and 11 of the 20 assessed reviews on D1–D6. Only D4 reached 16/20. The disjoint ten-case Qwen control scored 3, 4, 8, 9, 8 and 8. GPT-OSS-120B scored 2, 3, 6, 9, 8 and 8 on the same ten answers. Its follow-up quoting individual candidate fields stopped at two completeness matches out of five. No new manual baseline or development review is due. See the [iteration log](ITERATION_LOG.md) and [AEC runbook](docs/AEC-COURSE-RUNBOOK.md) for subsequent model screens. The afternoon snapshot below records the earlier handoff.

**10:10 p.m. Eastern update.** Nemotron, GPT-OSS-20B and Llama-70B also fell short. Adding task-selected original source excerpts to GPT-OSS-20B yielded four API-correctness matches and two safety matches in five answers. The third safety disagreement ended that screen. The Mac and project tunnel are free. Ten source-free development requests and fifty baseline requests are prepared locally. The previous hosted authorization covered the separate engineering experiment. The assessed baseline still has only D4 above threshold, and the corrected AEC cohort awaits calibration.

**10:45 p.m. Eastern update.** Qwen completed the source-free local control in ten starts. Matches were 2, 4, 9, 9, 8 and 5 of ten. Offline replay verified all ten raw judgments and the Mac is free. The Astra transport and price preflight passed offline, with a $24.2304 reservation for all 60 proposed requests and zero paid calls. Astra omits temperature. A potential alternative is the local Devstral 2 123B coding model. The two pinned quantized shards total 74,897,653,312 bytes. An owner decision on the download or hosted comparison is pending.

**Owner:** Chad Josewski. **Snapshot:** November 18, 2026, around 3:02 p.m. Eastern.  
**Workspace:** `D:\_Repos\_AIA\aia-mp1-synthetic-data`. **Implementation revision:** `792e11e` on `main`. [Project tracker](https://github.com/cjosewski/aia-plan/issues/4)

## What Chad asked for

> That is not correct. The original plan was correct - applied to AEC data. The evaluation criteria and the method defined in the project description need to be followed exactly.

The project generates and evaluates Q&A across five AEC categories. The course requires a structured generation pipeline, a quality gate, human and independent model ratings, segment analysis, judge calibration, and then generator correction. Calibration requires at least 80% human/judge agreement in **each** of D1–D6. For the 20 reviewed items, that means at least 16 matches per dimension.

Chad clarified how he scored the original manual review:

> I scored D3 only on API correctness. Tool availability and affordability played no part in any score.

## Where the interpretations diverged

The approved engineering plan and its rubric are the starting point for understanding the AEC adaptation. The engineering rubric calls D3 **API Realism** and asks whether required APIs and libraries exist in the stated installation and version. The course brief calls D3 **Tool Realism** and uses homeowner availability, cost and specialty-tool restrictions. Both definitions exist in the checkout. [Implementation plan](docs/implementation-plan.md) · [Engineering rubric](config/rubric.json) · [Literal course rubric on AEC data](config/aec-course/rubric.json)

The previous session applied the literal homeowner wording to AEC tool lists, withdrew the first reference from course scoring, and prepared a D3-only review. The current SDD, runbook and GitHub update reflect that implementation choice. Chad then asked for a clean handoff because the session was confusing the issue. His clarification establishes how he **scored** the first review. It does not by itself settle which rubric governs submission. [SDD](docs/SDD-P1-03.md) · [Review runbook](docs/AEC-COURSE-RUNBOOK.md)

## Verified evidence at handoff

The evidence root is `D:\_Repos\_AIA\artifacts\evidence\P1-03\aec-course\assessments\`.

| Assessment or run | Verified state |
| --- | --- |
| `aec-course-baseline-review` | 50 AEC items, ten per category. Chad completed 20 blind reviews and personally confirmed independence. The original ratings and frozen reference are intact. A separate `human-reference-withdrawal.json` records the previous session's scoring decision. |
| `aec-course-baseline-d3-review` | Same cohort and same 20 selected items. The CLI reports **20 of 20 complete**, with no frozen reference at handoff. The launcher was designed to collect a new D3 decision and carry forward the other five ratings. |
| `aec-course-baseline-judge-v1` | Local Qwen3.5-122B-A10B on the Mac, using the literal course rubric. Its ledger showed 18 valid item judgments out of 50 and a running manifest at inspection. Check current status before starting any job. |

The separate Home DIY dataset is a historical experiment. The active subject is AEC. Preserve both human ledgers and all existing judge attempts. A score comparison needs matching human and judge criteria.

## November 18 follow-up

Chad confirmed that instructor approval covered the AEC topic in general. Use the course D3 Tool Realism and D4 Scope Appropriateness anchors for submission. AEC tasks may use MCP tools as well as direct API calls. Apply D3 to the required tools listed in each answer regardless of how they are accessed. Both review queues are complete. The replacement ledger contains 20 blind D3 reviews with the other five decisions carried forward. [Decision record](docs/COURSE-BRIEF-RECONCILIATION-20261118.md)

Chad subsequently confirmed that both D3 passes scored only version-specific API correctness, including whether the code compiles and behaves as claimed. The second 20-item reference is frozen, and its D3 scores match the first on every item. The reviews establish no course Tool Realism agreement. [Review disposition](docs/AEC-COURSE-RUNBOOK.md)

## First action requested at handoff (completed)

For the version-specific API correctness evaluation, use the [AEC runbook](docs/AEC-COURSE-RUNBOOK.md). The `aec-course/api-correctness-v1-inputs` packet pins both frozen reviews and the 50 label-free requests. The corresponding judge writes to `aec-course/api-correctness-judge-v1`. Read its manifest and report before allocating another run.

Read the approved plan, the two D3 definitions above, and the original project's customization decision. Explain in plain language how the course criterion maps to the AEC project and identify any point the documents leave open for Chad. Both human queues already contain 20 completed items. Resolve the rubric question before asking for further review, freezing the second reference, or changing the judge prompt. Recheck the running job from local evidence first. Give Chad notice before taking control of a machine, and give concurrent Herd work priority.
