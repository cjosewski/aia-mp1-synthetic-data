# GPT-OSS-120B fixed V7 screen

**Completed:** the verified model loaded on the Mac and accepted five first
attempts, but matched only 23/30 ratings, with five false approvals and two false
rejections. It remains unqualified. The [checkpoint](JUDGE-QUALIFICATION-RESULTS.md)
owns the audit and next proposed intervention. The protocol below is retained
as the predeclared procedure; no automatic extension follows.

Chad's “Go” after the Llama comparison authorizes preparation of the next local
candidate. GPT-OSS-120B MXFP4 is selected for a bounded development screen, not
as a qualified assessed judge. The frozen human reviews remain unchanged.

## Selection basis and provenance

GPT-OSS-20B gave the best agreement of the two fixed-V7 candidates (27/30 versus
Llama's 23/30), but still falsely approved an API defect and rejected two clear
contexts. Testing the larger member of that reasoning family keeps the working
output protocol while asking whether capacity improves evidence use. A common
model family may retain the same errors; neither size nor published benchmarks
proves superiority as this engineering judge. Both GPT-OSS models are distinct
from the Qwen3-30B-A3B generator.

The [upstream model card](https://huggingface.co/openai/gpt-oss-120b/tree/b5c939de8f754692c1647ca79fbf85e8c1e70f8a)
describes a 117B-parameter reasoning model with 5.1B active parameters, native
Harmony formatting and an 80 GB GPU deployment target. The
[maintainer GGUF](https://huggingface.co/ggml-org/gpt-oss-120b-GGUF/blob/f59990363fbbb67f01bce03e5e7bf0929e3e320b/gpt-oss-120b-MXFP4.gguf)
is pinned independently; its card identifies `openai/gpt-oss-120b` as the base
model. The upstream snapshot is a documentation pin, not an attestation of the
converter's exact source-weight revision. Apache-2.0 and the
[gpt-oss usage policy](https://openai.com/policies/gpt-oss-usage-policy/) apply.

| Property | Pin |
| --- | --- |
| Upstream model | `openai/gpt-oss-120b` |
| GGUF repository revision | `f59990363fbbb67f01bce03e5e7bf0929e3e320b` |
| File | `gpt-oss-120b-MXFP4.gguf` |
| Bytes | 63,387,346,208 |
| SHA-256 | `582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d` |

The Mac and NAS inventory contained only the earlier candidates. Acquisition
therefore downloads this exact public file to a new `.part` path, checks its size
and SHA-256, and only then renames it to the final local model path. Partial or
existing files are preserved for inspection. No hosted inference or automatic
model substitution is permitted. Source metadata and model-card snapshots live
outside Git in `qualification/gptoss120b-selection-20261113/`.

## Capacity and runtime

The observed Mac is an M4 Max with 137,438,953,472 bytes of RAM (128 GiB).
Before acquisition its Data volume had 344,030,820 KiB available (about 352 GB).
These exceed the pinned file size and published deployment estimate, so a local
load is reasonable to attempt. Total RAM is not a guarantee of available Metal
memory or successful operation. Loading and effective server properties must pass
before any completion request. No system GPU-memory limit or Herd service changes
are part of this screen.

Retain the installed llama.cpp `b12110-cd959bae9`, native embedded chat template,
loopback port 8081, one slot and context 16,384. Keep temperature 0.1, max output
4,096 and timeout 300 seconds. The
[llama.cpp maintainer guide](https://github.com/ggml-org/llama.cpp/discussions/15396)
documents GPT-OSS GGUF support and memory guidance; the actual local build and
load result remain authoritative for this experiment. No upgrade is automatic.
Record the new native template and require unchanged default generation settings
against GPT-OSS-20B; the new model's template need not be byte-identical.

## Fixed experiment and stop rule

Experiment `gptoss120b-v7-mac-comparison-001` uses qualification-v1-01 through -05,
in the existing order, one per category. Messages, passage catalog, schema and
validation code must be byte-identical to GPT-OSS-20B V7. Preserve the rubric,
references, human labels and every earlier result. Compare archived GPT-OSS-20B
and Llama V7 outputs without rerunning them.

Allocate at most ten new completion starts after 87 documented starts (ceiling
97), at most two per case. Stop after five accepted judgments or two consecutive
unsuccessful attempts. Unknown outcomes consume their attempts and require
inspection. Health and checksum checks make no completion requests. A load failure
stops before inference. Do not revise settings, retry a completed run, or extend
the experiment automatically.

Before packaging, run locked WSL project and portable-runner tests, lint, formatting,
shell syntax, frozen-contract hashes and archived comparison accounting. After
execution, audit all thirty decisions, exact resolved passages, attempt lineage,
coverage, false approvals/rejections and latency. Archive the complete working
folder and audit on the NAS; preserve the Mac copy and stop only the owned server.

Development advancement requires complete coverage, at least 4/5 matches in each
dimension, no safety/API false approvals and supported explanations. Even a perfect
five-case result is not qualification: these are known development cases, with
AI-assisted human-adopted reference ratings and one stochastic run. Broader
development, fresh blind confirmation and assessed calibration remain separate.
No new human review is needed for this screen.
