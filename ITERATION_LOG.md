# Iteration log

Record one entry for each generator or judge prompt change. Link measured results to immutable run artifacts; an unmeasured hypothesis is not a successful experiment.

| Date | Change | Hypothesis | Result | Decision | Next step |
| --- | --- | --- | --- | --- | --- |
| 2026-11-13 | Audit returned Mac `judge-v2` development run; no prompt or label change | Check whether the measured configuration reduces known false approvals | Twenty valid first attempts. Llama 50/60 agreement, nine false approvals; Qwen 51/60, three false approvals and six false rejections. Both D2 7/10. Means 38.1/9.6 seconds per item. Platform/runtime also changed, so improvement is not attributable solely to the prompt | Qualification remains pending; preserve the measured protocol and all regressions | Prepare a distinct candidate comparison on the same Mac before any new bounded run; fresh blind confirmation still required |
| 2026-11-13 | Move the unstarted v2 development run to the Mac at Chad's direction; preserve GGUF pins through standalone llama.cpp/Metal | Evaluate the candidate while Linux handles Herd updates | Native Mac execution unmeasured; platform/runtime now differ from Fedora v1 | Same forty-request allocation, separate Mac artifacts; no claim that a cross-platform difference isolates prompt effects | Run the Mac handoff and retain runtime properties/logs for both models |
| 2026-11-13 | Add `judge-v2.md`; retain v1, generator, rubric and all frozen references | Requiring task-specific evidence, contradiction checks and accurate tips will reduce false approvals without blanket failures | Unmeasured. Audited v1 Fedora comparison: Llama 42/60 agreement, Qwen 48/60; twenty valid first attempts. Llama falsely approved fourteen human-failing criteria | Keep Llama qualification pending; v2 is development-only until measured and independently confirmed | Run one bounded v2 development comparison, then review reasoning and fresh blind confirmation; see [checkpoint](docs/JUDGE-QUALIFICATION-RESULTS.md) |
| 2026-11-09 | Add `judge-v1.md` with independent rubric instructions, strict D1–D6 decisions and short justifications; generator prompt unchanged | A separately prompted judge can produce auditable decisions for comparison with authentic human reviews | 166 offline tests pass. Live readiness probe at 2026-11-10 03:56:28 UTC timed out from WSL before any judge call; no model-quality or agreement result | Preserve the unmeasured prompt and diagnostic queue; owner reports assignment acceptance and approves this implementation slice | Collect real human labels; run the bounded diagnostic judge when the configured endpoint is reachable |
| 2026-11-09 | Initialize `generator-v1.md`, the canonical seven-field contract and engineering rubric record | Explicit task context, real API requirements, concrete precautions and distinct tips will provide a useful first generation baseline | Not yet measured; no model or quality outcome claimed | Use this revision for the approved first-slice local smoke test | Run offline checks, then an available local model; retain raw attempts and gate results |

The November 9 early-start approval does not change the benchmark-adaptation question or replace human labeling, judge calibration, measured correction and coaching review. The first five-item smoke run is separate from the assessed baseline.

Implementation checkpoint, November 9: 114 offline tests, Ruff lint/format and CLI help checks passed in WSL2 Python 3.12.16. No generator prompt correction is supported by that result. The default local endpoint refused both health and model-list requests, so the model smoke run remains pending. Verification and probe receipts are in workspace `artifacts/evidence/P1-03/kickoff-20261109/`. Next step: use an available local Herd model with the documented configuration and run five items before assessed data collection.

Readiness follow-up, November 9 at 17:03 EST: Windows health and authenticated model-list requests both passed (HTTP 200; Qwen3-30B-A3B-Q4_K_M). WSL2 localhost refused connections and its Windows host gateway timed out. No generation ran and no prompt/settings changes were made. The smoke blocker is now specifically WSL-to-Windows connectivity; receipts are in workspace `artifacts/evidence/P1-03/herd-ready-20261109/`.

Live smoke, November 9 at 17:27 EST: owner-approved WSL restart applied mirrored networking; authenticated loopback access passed and anonymous model access was rejected. `smoke-herd-20261109T222724Z` used unchanged `generator-v1.md`, Qwen3-30B-A3B-Q4_K_M, temperature 0.6, 4096 tokens and a 120-second timeout. All five first attempts were schema-valid (5/5), with no retries or duplicates. The independent gate retained 3/5 and rejected two on D2; its batch result is failed. This is smoke evidence, not an assessed baseline or human quality judgment. Preserve the original run and review the D2 results before a later prompt experiment. Raw evidence: workspace `artifacts/evidence/P1-03/smoke-herd-20261109T222724Z/`.

November 10 implementation checkpoint: Chad approved the assessed-collection plan.
Added `generator-assessed-v1.md` to use explicit task/reference context. Hypothesis:
versioned context will make API and installation claims auditable. No live assessed
generation has measured that hypothesis. The original generator prompt and diagnostic
artifacts are preserved. Five independent diagnostic labels and judge responses were
completed; agreement-001 recorded 60% D1–D4 and 100% D5–D6. Owner-approved amendments
produce a separate 100% post-review report. New assessed reports freeze blind labels
before judging and keep later adjudication separate. Next: finish source clearance
and model qualification, collect a real baseline, then obtain 20 blind human reviews.

Verification for this implementation: 185 offline tests passed, Ruff check/format
passed and all new CLI help paths passed. The diagnostic label/judge status commands
still report five completed items. Receipt: workspace
`artifacts/evidence/P1-03/assessed-implementation-20261110T163211Z/`.
