# Fixed V7 model comparison

**Completed:** five first-attempt Llama judgments matched 23/30 ratings, with six
false approvals and one false rejection, versus GPT-OSS's 27/30. Neither model
qualifies. The [checkpoint](JUDGE-QUALIFICATION-RESULTS.md) records the audit and
next step. The protocol below is retained as the predeclared procedure.

Chad authorized the next controlled model comparison with “Go” after the V7
format result. This development screen compares Llama 3.3 70B Q4_K_M with the
archived GPT-OSS 20B MXFP4 V7 judgments. Llama is Chad's previously selected judge
candidate, is distinct from the Qwen generator, and its exact weights are already
available on the same Mac. These are reasons to test it, not evidence of stronger
judgment. No model download or Herd change is needed.

## Fixed conditions

Use qualification-v1-01 through -05, one per category, in the same order. Copy
V7's complete model messages, passage catalog, response schema and validation code
byte for byte. Keep the rubric, references and human labels frozen. Expected
labels and reviewer comments stay outside requests. The GPT-OSS run remains
archived; do not rerun it or select different cases after seeing Llama's answers.

Use the same Mac and llama.cpp build b12110-cd959bae9, loopback port 8081, context
16,384, one slot, temperature 0.1, output limit 4,096 and timeout 300 seconds.
Use each model's native embedded template. Model architecture, quantization and
template necessarily differ; this compares deployed configurations, not parameter
count alone. Verify Llama's served identity, weights and native runtime properties
against its archived Mac V2 receipt before any completion request.

Llama weight SHA-256:
`32df3baccb556f9840059b2528b2dee4d3d516b24afdfb9d0c56ff5f63e3a664`.
The 42,520,398,816-byte file and upstream provenance are recorded in
[source readiness](SOURCE-READINESS.md). Local inventory on November 13 confirmed
this file exists; the runner must compute its checksum before inference.

## Budget and stop conditions

Experiment `llama70b-v7-mac-comparison-001` gets at most ten new starts after 82
documented starts (ceiling 92), at most two per case. Stop after five accepted
judgments or two consecutive unsuccessful attempts. Unknown outcomes consume
their attempts and require inspection. Preserve every start, raw output, failure
and canonical projection. No mid-run changes, automatic extension, prompt revision
or second model run follows this allocation.

Run locked WSL project and portable-runner tests, lint, shell syntax and frozen
input/contract checks before packaging. Use authorized SSH and a dedicated server;
stop only the server started by this run. Archive the entire working directory
and independent audit on the NAS, preserving the Mac copy and earlier experiments.

## Analysis and decision

Compare coverage, initial schema validity, accepted passage references, retries,
per-dimension agreement, false approvals/rejections and request durations.
Recompute the saved GPT-OSS counts on exactly these five cases. Inspect all thirty
Llama decisions and resolved passages, including matching decisions, for API-owner
accuracy, use of all supplied fields, dimension boundaries and supporting reasons.

A candidate is promising for a larger development screen only with complete
coverage, at least 4/5 matches in every dimension, no safety/API false approvals,
and explanations that substantiate the ratings. This small known-case check cannot
qualify an assessed judge even if all conditions hold. Report regressions and
unsupported matching rationales; do not rank by pooled agreement alone.

Fresh blind confirmation and assessed calibration remain separate. The original
20-item assessed human reference is unchanged. No new human review is needed for
this comparison, and no stronger-judge qualification receipt is issued by it.
