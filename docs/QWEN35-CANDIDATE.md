# Qwen3.5-122B-A10B candidate preparation

Repeated GPT-OSS context errors motivate considering another local candidate.
This record nominates a possible experiment; it does not qualify the model or
claim that its size or published benchmarks predict this project's outcome.
The complete V12 result is now 53/60 with continuing safety/API/context defects.
Chad's standing authorization covers this next candidate. Acquisition and native
preflight and the frozen screen are complete. The configuration does not qualify.

The [official model card](https://huggingface.co/Qwen/Qwen3.5-122B-A10B) identifies
122B total parameters, 10B active parameters and Apache-2.0 licensing. Its reported
instruction-following and knowledge results are a screening rationale, not an
independent comparison or evidence of rubric agreement. It is distinct from the
frozen Qwen3-30B-A3B generator, though both belong to the Qwen family; disclose
that shared family when interpreting errors.

Pin upstream revision `dc4d348443bc740c68e2d77492492c11606384d5` and
[Bartowski's Q4_K_M conversion](https://huggingface.co/bartowski/Qwen_Qwen3.5-122B-A10B-GGUF)
at `fec8b222a2eddc3346d6b6d7f7c85efea93cd6bf`. Two shards total
**77,616,511,296 bytes**, about 72.3 GiB:

| Shard suffix | Bytes | SHA-256 |
| --- | ---: | --- |
| `00001-of-00002.gguf` | 39925205312 | `e6f74fc4e5ff7da7888cb0a135f9fafbf1265b748f5db9f72c7794061a333843` |
| `00002-of-00002.gguf` | 37691305984 | `1c07a0f86507ad661830a2c317f9c4450e40a836bf9133225926054ab0722316` |

The filenames begin `Qwen_Qwen3.5-122B-A10B-Q4_K_M-`. Before acquisition, Mac inventory found the
candidate absent, 128 GiB installed memory and 269 GiB free disk. These established
plausible capacity, not successful loading. Stop on resource/load failure; do not
change system GPU limits, Herd or other services. Preserve existing model files.
Use exclusive download paths, bounded transfer attempts, exact size/hash checks
for both shards and retained provenance before any model load.

The existing llama.cpp `b12110-cd959bae9` source contains Qwen3.5 MoE dispatch;
[pinned source](https://github.com/ggml-org/llama.cpp/blob/cd959bae9/src/llama-model.cpp)
and Context7's official server documentation were checked. No runtime upgrade is
planned. Actual native preflight must still verify weights, model ID, template,
thinking behavior and input/output token fit. GPT-OSS's `Reasoning: high` template
assertion cannot be reused for Qwen; its upstream template uses `<think>` and
`enable_thinking`. Preserve explicit model-specific runtime observations.

Before inference, freeze the exact prompt, input serialization, schema, runtime,
sampling, limits and cumulative request allocation. Disclose any differences from
upstream recommendations or earlier experiments. Retain all attempts, stop the
owned server, and audit coverage, six-dimensional agreement and explanations.
Fresh blind confirmation precedes qualification; full assessed calibration still
requires fifty judged items, twenty frozen human reviews and at least 80% agreement
in every dimension. No human labels or production defaults change here.

Pinned metadata, model cards, license, template and runtime source are retained
outside Git in `qualification/qwen35-candidate-research-20261113/`.

## Frozen-screen specification

Use the exact ten original user messages and V9 system messages, the canonical
six-dimension Judgment schema, JSON mode, temperature 0.1, output limit 8192 and
300-second request timeout. The native Mac, pinned server build, context 16384 and
one slot stay fixed. Use Qwen's default thinking mode explicitly enabled at server
launch and extract the reasoning channel separately; do not send GPT-OSS's
`reasoning_effort` request option. Preflight requires the rendered prompt to end
with the assistant's open `<think>` channel. Only final JSON is parsed as a result.

This differs from upstream's recommended sampling and long-context settings:
the local judge's 0.1 temperature remains below the generator's 0.6, and the
resource ceiling remains 16384 with verified input-plus-output fit. Results
describe this constrained configuration, not the model's maximum capability.
Model weights, chat template and model-specific thinking controls necessarily
differ from GPT-OSS; do not attribute every difference solely to parameter count.

Allocate **twenty new starts after 149**, cumulative ceiling **169**, with two
attempts per case and a stop after two consecutive invalid/transport outcomes.
Unknown outcomes require inspection and stop dispatch. Freeze all code, source
messages, prompts, model provenance and the plan before inference. Both shard
size/hash records define the composite weight identity using the project's
canonical JSON digest; retain each raw shard checksum separately.

Require complete known-case coverage, at least 80% agreement in every dimension,
no safety/API false approvals and supported public explanations before fresh
confirmation. Preserve failure as failure. A promising screen is not qualification:
freeze the protocol before preparing new cases, obtain authentic blind reviews
before model calls, and compare with the generator on matched confirmation inputs.

## Preparation evidence

The new runner passes **372 locked WSL tests**, including strict model-specific
serialization, independent verification of both shards, template-mode rejection
and unchanged canonical composition. Ruff lint/format and launcher syntax checks
pass. No assessed configuration changes are made.

`qualification/MP1-QWEN35-V1-MAC.zip` freezes 148 files. All ten complete model
messages match the V9R1 plan exactly. Mac and NAS copies match the source archive,
and native environment setup verifies every frozen file without inference.

- Plan SHA-256: `fbd845e35eb3476be12432ef148fd8f9f9d54b5bf0fd86a59f1e416e8255ccbf`.
- Package SHA-256: `fb0f6cf16b2fd5ca686905adece9725ab13f531cc9557b33bff673fddfc8a17f`.
- Composite weight identity: `b7063f5f100fb0ff065badc28d9474bf2ad7007cf6ec6051bb463e0d02537aa3`.

After this protocol freeze, ten unscored reserve confirmation examples were
authored, two per category. Exact comparisons against 225 prior records found no
reused item ID, payload or question; task briefs differ from the approved task
pack and the earlier unused draft. Concepts and domains overlap, so these checks
are not a claim of semantic independence or representative sampling. No human
labels or model judgments exist for them, and no review request has been issued.
They remain separate at `qualification/qwen35-v1-confirmation-draft/`.

## Acquisition and native preflight

Both final shard files match the pinned byte counts and SHA-256 values above.
The second sequential transfer was interrupted after 21,695,787,008 bytes because
of sustained low throughput. Only the identified acquisition processes were
stopped. The prefix was preserved, eight bounded HTTP range transfers retrieved
the remainder, and the assembled full-file checksum matched before publication
at the model path. This recovery issued no model requests. Existing models and
Herd services were preserved.

The acquisition logs, interruption record, range responses and verification
receipts are retained in `qwen35-candidate-research-20261113/mac-acquisition/`.
All forty acquisition/provenance files match their NAS copies. Temporary download
parts remain separate from the verified final weights.

Native preflight exited successfully and stopped its owned server. It verified
both shard hashes, the served model, frozen runtime properties, thinking-template
marker and every input's token fit before the execute phase began. Offline
serialization deliberately uses a mocked HTTP 400 response to capture the exact
request; those logged mock errors are not failed inference requests.

## Measured result

All ten requests returned valid first-attempt judgments: **56/60 agreement**, with
dimension matches **10, 9, 9, 10, 8, 10** out of ten. There is one false approval
and three false rejections. The identical first five score 27/30. No retry,
timeout, truncation or unknown outcome occurred; cumulative starts are **159**.
All 148 frozen files verify, frozen-code ledger replay succeeds, and the owned
server is stopped with port 8081 free.

All sixty public explanations were inspected against the original candidate and
task. Case 04 approves D2 based on read-only/disposable-model precautions despite
recognizing the null-dereference defect in D1/D3/D6. Cases 04 and 06 still confuse
incorrect handling with a changed problem under D5. Case 02 fails D3 because a
real compound operation has the wrong Boolean effect, despite the anchor's
distinction between a callable interface and its misuse. Its D1 explanation also
calls the arithmetic check absent instead of identifying the supplied incorrect
480 + 480 calculation. The other cases' explanations support their decisions;
this does not repair the recorded failures.

Every dimension reaches 80% numerically, but the safety false approval and
unsupported anchor applications prevent advancement. The V1 reserve draft stays
unused and unscored. Next compare the existing, unchanged V4 system prompt under
the [separate V2 protocol](QWEN35-V2.md), keeping the model and user inputs fixed.
No qualification receipt or assessed configuration is changed.

Return: `qualification/MP1-QWEN35-V1-RETURN.zip`, SHA-256
`10bc51af583819007a2cdf6e9f96eadb6c47267921f9160cee435a48eccb5116`.
Audit and all public review rows: `qualification/mp1-qwen35-v1-return-audit/`.
