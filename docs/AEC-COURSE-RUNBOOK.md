# P1-03 — Blind baseline review of AEC data

Chad completed both baseline reviews on November 18. The active evaluation uses his version-specific API correctness rule for D3. The first two sections below document those completed reviews. For the current experiment, use [the AEC evaluation procedure](#aec-evaluation-using-the-reviewers-d3-definition) and [the independent development review](#independent-development-review).

Review 20 AEC questions and answers, four from each original category: GIS scripting, AEC automation, structural-analysis code, CAD APIs and simulation. Use the six course dimensions displayed for every item. The full scoring anchors and thresholds are in [the assessed rubric](../config/aec-course/rubric.json).

1. On the Windows project workstation, double-click `Review-AEC-Baseline.cmd` in the NAS AEC-baseline-review-001 handoff folder. It opens the Python CLI in Ubuntu.
2. Read the task, generated fields and supplied references. Evaluate the written response. You do not need to execute its code.
3. Enter 1 for pass or 0 for fail on each displayed dimension. D3 asks whether every listed tool meets the course's homeowner availability and affordability rule. The existence of an API alone does not satisfy D3. D4 asks whether the work fits the stated user's capability and calls for professional help where needed. Use the homeowner/DIY anchor printed in the CLI. Record a concrete reason when an AEC item fails a literal course requirement.
4. Add notes after the sixth decision. The CLI saves each finished item. Enter q to quit, then reopen the launcher to resume. If you recognize an item whose judge scores you have seen, disclose that before declaring a blind review.
5. When all twenty are saved, tell Codex whether you finished before seeing judge ratings for these items.

## D3 correction for the November 18 baseline

Chad confirmed that his 20 original D3 ratings assessed API correctness. The frozen review is retained for audit. Calibration requires human and judge decisions on the same criterion.

1. Open `\\192.168.0.55\aia\Handoff\P1-03\AEC-baseline-review-001` on the Windows project workstation and double-click `Review-AEC-D3.cmd`.
2. Confirm the opening statement if it applies. The CLI retrieves the same 20 items and carries forward your D1, D2, D4, D5 and D6 ratings with their original label IDs.
3. For each tool list, enter **1** if every tool is something a typical homeowner already owns or could buy at a general hardware store for under $50, and none is a professional, specialty or trade-only tool. Otherwise enter **0**. An optional note can identify the deciding tool. Skip an uncertain item with **s** or save your place and exit with **q**.
4. When the remaining count reaches zero, tell Codex. Keep the judge results closed until the replacement human reference is frozen.

## Open the original six-dimension review manually

From Windows Terminal, enter `wsl -d Ubuntu`. In Ubuntu:

```bash
cd /mnt/d/_Repos/_AIA/aia-mp1-synthetic-data
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
export AIA_MP1_DOMAIN=aec-course
export AEC_ROOT=../artifacts/evidence/P1-03/aec-course
uv run --locked python -m aia_mp1 label --artifact-root "$AEC_ROOT" --assessment-id aec-course-baseline-review --reviewer "Chad Josewski" --review-stage blind
```

## November 18 review disposition

Chad confirmed that he completed both reviews independently and scored D3 on version-specific API correctness in both passes. The 20 replacement scores match the original 20. Course D3 agreement remains unmeasured.

The frozen replacement reference in `aec-course-baseline-d3-review/human-reference.json` has SHA-256 `45e2dc3d149660ec322f00264f6b3fc2a5184a01d4adb01cfc72c195a2d027d4`. Preserve both references, their ledgers and the judge attempts under their original assessment IDs. The D3 launcher above describes the completed November 18 review. Keep judge decisions out of any subsequent blind review. The replacement judge stopped after 25 valid judgments on 50 items. One additional request had an unknown outcome. No calibration report was produced.

## Evidence and next steps

### AEC evaluation using the reviewer's D3 definition

Both blind reviews use version-specific API correctness for D3. The AEC evaluation uses those recorded decisions, the original five other anchors and the original per-dimension agreement threshold. The packet identifies both frozen reviews by hash. Judge requests contain the rubric, prompt, item and local reference context. Human ratings and reviewer notes stay outside the requests.

D3 applies to an MCP tool when a candidate relies on one. A text check found zero explicit mentions of “MCP” or “Model Context Protocol” across the 50 authored task briefs and 200 generated baseline answers, including the 50 retained answers and ten development cases. Connector-specific MCP behavior therefore has no direct measurement in this baseline.

In the WSL environment above, `uv run --locked python tools/prepare_aec_api_evaluation.py` prepares or verifies the 50 fixed requests under `$AEC_ROOT/api-correctness-v1-inputs`. The [D3 scoring anchor](../config/aec-course/api-correctness-d3.json) and [judge prompt](../prompts/aec-api-correctness-judge-v1.md) define the versioned comparison.

With the selected local model served through the project tunnel, `uv run --locked python tools/run_aec_api_evaluation.py` runs the batch once. To resume an interrupted batch, use `--resume` after checking the endpoint and the existing ledger. The ledger counts a request as soon as it starts. The run stores its manifest, attempts and final report under `$AEC_ROOT/api-correctness-judge-v1`. Use the report's six agreement counts and full coverage to evaluate the AEC calibration gate.

For a revised judge, pass the same `--revision v2` or `--revision v3` to both commands. Each revision has its own input packet and output directory. Check that the rubric, selected IDs, cohort, reference hashes and all 50 item messages match the first packet before inference. Record the hypothesis and compare all six agreement counts on the same 20 reviews. The initial allocation covers three judge versions, with two attempts per item per version.

The course replay verifies the original generation ledgers against their frozen AEC cohort hashes, reruns schema, six heuristic checks and deduplication, excludes all 50 items from the previously judged cohort and retains the first ten eligible items per category. The original 200 first attempts stay in the denominator. Review selection is stratified and deterministic. A fresh evidence root can reproduce this with `AIA_MP1_DOMAIN=aec-course uv run --locked python tools/prepare_aec_course_baseline.py`. The benchmark supplies its uniform distribution (20% per category) for comparison across the five AEC categories.

After the human reference is frozen, a distinct locally served judge uses Instructor/Pydantic and a lower temperature than the generator to score the same dimensions for every retained item. Calibration uses these fixed items and requires ≥80% agreement separately on D1–D6. Only then use the weakest measured segment and dimension to revise the generator and run the corrected cohort. Report all thresholds, traces, iteration history, charts and the measured before/after failure reduction. Prior engineering ratings used different anchors and cannot establish agreement on this rubric.

### Independent development review

The new review contains ten surplus baseline answers, two per AEC category. They cover ten different tasks. Each passed the generation gate and was left out when the category reached its quota. Selection excludes questions and payloads in the assessed AEC baseline and the earlier engineering baseline and corrected cohorts. The tasks come from the same source pack, so the screen measures performance on different answers to familiar kinds of tasks.

On the Windows project workstation, open `Review-AEC-Development.cmd` in `../artifacts/evidence/P1-03/aec-course/assessments/aec-api-development-001/`. Enter six independent ratings per item using the displayed anchors. The CLI saves each completed item. Enter `q` to exit and open the launcher again to resume. Keep model results closed until all ten are complete. The original twenty baseline reviews are already frozen.

The operator can reproduce the diagnostic selection and protocol in WSL with the environment above.

```bash
uv run --locked python tools/run_aec_development.py prepare
```

The development comparison allows one local request per case at each of three stages. The `reference` stage sees the task and its versioned sources. An independent technical audit reviews the resulting checklists for missing obligations and unsupported requirements. The `control` stage uses the v3 prompt. The `comparison` stage receives the checked reference and must account for each obligation and every tip. Both scoring stages require the ten new blind labels to be complete. Each stage preserves its start and return. An unknown or invalid return consumes the slot.

The candidate must resolve all ten items, match at least eight human ratings in each dimension, equal or improve the control on D1 and D6, and pass an explanation audit. Development results do not count toward the assessed 16/20. The assessed gate still requires scores for all 50 and the same frozen 20 human reviews.

**November 18 development update.** Chad completed all ten blind reviews. The first model-generated checklist failed its source-binding check and added an unnecessary ArcPy output-location requirement. That reference stage stopped after one saved return. The control continues to use the original v3 prompt on the ten development answers.

The replacement comparison uses technical notes written from the ten task briefs before the first reference request. Each case gets one structured scoring attempt with the same prompt and response schema as the planned checklist comparison. The application verifies coverage of each note and candidate tip, along with all candidate and rubric citations. In the WSL environment above, `uv run --locked python tools/run_aec_task_notes.py prepare` verifies the ten frozen requests. Use `score` with the project endpoint available. The assessed cohort receives no requests from either development command. Results and technical-audit receipts stay in `$AEC_ROOT/api-development-task-notes-001/`.

That first task-note scoring arm stopped on its first return. The ratings used prose where the format required short citation IDs, and the coverage explanation treated optional examples as mandatory. The subsequent screen used `tools/run_aec_scoped_review.py` to send required checks and optional scope notes in separate fields. Seven judgments passed validation. Its eighth return omitted part of the tip accounting. The receipt is in `$AEC_ROOT/api-development-scoped-001/closeout.json`.

The complete GPT-OSS-120B control is in `$AEC_ROOT/api-development-gptoss120b-001/report.json`. A follow-up required one candidate quotation per individual rubric decision. It stopped after five completeness decisions when 8/10 became impossible. The chronology and agreement counts are in the [iteration log](../ITERATION_LOG.md).

For another installed local model, verify its GGUF parts on the project Mac and record the SHA-256 of each part, served model path, server build, context size and number of slots in the model's `deployment.json`. The operator command is `uv run --locked python tools/compare_aec_installed_judge.py MODEL score`. The command reuses the ten fixed development inputs and stops once a dimension has three disagreements. It records each original request and completion under `$AEC_ROOT/api-development-MODEL-001/`. The assessed cohort, frozen ratings and all prior measurements retain their individual denominators.

The three additional installed-model comparisons and the source-assisted GPT-OSS-20B screen have ended. The latter retrieved original source excerpts using each task brief. To reproduce the source cards and requests offline, run `uv run --locked python tools/screen_aec_sources.py prepare`. The results and reasons for stopping are in the [iteration log](../ITERATION_LOG.md).

To verify the locally prepared source-free comparison packets, run `uv run --locked python tools/prepare_aec_source_free.py`. This command prepares ten development and fifty baseline inputs. Human ratings and source excerpts remain in the local evidence store. A new hosted run requires authorization for that experiment.

`uv run --locked python tools/preflight_aec_astra.py` exercises those 60 requests through the locked Instructor, Pydantic and OpenAI SDK with an in-memory transport. It verifies the exact message contents, endpoint, output limit and one request per item. The receipt in `$AEC_ROOT/api-source-free-astra-preflight-001/preflight.json` records the request hashes and the dated spending assumptions.

At November 18 Standard rates, reserving 12,000 input and 4,096 output tokens per start puts the ten-item screen at $4.0384 and the combined 60 starts at $24.2304. This includes the most expensive short-context cache write. The price calculation assumes the standard US API endpoint and tier. Recheck the applicable rates before any authorized dispatch. Astra supports the structured comparison through Instructor. Its API omits temperature, so that comparison would leave the course's lower-temperature judge requirement open. [Standard pricing](https://developers.openai.com/api/docs/pricing) · [GPT-6.2 parameter guide](https://developers.openai.com/api/docs/guides/latest-model)

The source-free local control uses the same ten application messages, Qwen's original Instructor JSON mode and temperature 0.1. Its independent start and return records are in `$AEC_ROOT/api-development-qwen-source-free-001/`. In the locked WSL environment, `uv run --locked python tools/run_aec_source_free_control.py replay` rebuilds the input and validates the raw completions, frozen labels and agreement report offline. Qwen's JSON-mode schema instructions differ from the hosted adapter's JSON Schema response format.

The Devstral comparison uses the original source-aware v3 requests, temperature 0.1 and one attempt per case. The two GGUF shards reside under `/Volumes/DataDrive/MP1/Devstral-2-123B-Q4_K_M` on the Mac. The local `api-development-devstral-001/deployment.json` records the verified file hashes and server build. Run `uv run --locked python tools/screen_aec_devstral.py replay` to reproduce the ten judgments and their agreement with the blind reviews.

The paired example comparison follows Unit 4, Module 1, Notebook 1, Exercises 4 and 9. It adds two completed AEC reviews to the system prompt. For each target, both examples come from other categories. One illustrates a joint completeness and safety pass and the other a joint failure. Selection is deterministic and uses the ten development reviews only. Run `uv run --locked python tools/screen_aec_examples.py prepare` to rebuild the requests. Each script accepts `score` for the verified local service and `replay` for checking recorded completions offline. The twenty assessed human reviews stay reserved for the later baseline comparison.

The [Unit 4 exercise review](UNIT-4-ALIGNMENT.md) explains the layer-alone and cumulative comparisons. Use `uv run --locked python tools/measure_aec_prompt_layers.py prepare plain` and `prepare examples` to verify the companion arms. Each retains the full rubric and only the opening v3 instruction. The latter includes the same demonstration pairs. Use `score` in place of `prepare` for local inference. After all four runs, `uv run --locked python tools/measure_aec_prompt_layers.py scoreboard` replays the returns and records which decisions each layer corrected or broke, plus median time per call.

The specialty comparison adds one checklist selected by the task's versioned source ID. Run `uv run --locked python tools/screen_aec_specialty.py replay` to verify the ten matched judgments, changes by dimension and two-case specialty counts. The D2 follow-up shows only the candidate's safety field alongside the task and reference. Run `uv run --locked python tools/screen_aec_safety_field.py replay` to check evidence quotations, valid decisions and changes relative to the original v3 judge. Both commands support `prepare` for offline input verification and `score` for the verified local endpoint. The D2 result covers one dimension.
