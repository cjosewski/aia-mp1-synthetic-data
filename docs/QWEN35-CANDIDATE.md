# Qwen3.5-122B-A10B candidate preparation

Repeated GPT-OSS context errors motivate considering another local candidate.
This record nominates a possible experiment; it does not qualify the model or
claim that its size or published benchmarks predict this project's outcome.
The complete V12 result is now 53/60 with continuing safety/API/context defects.
Chad's standing authorization covers this next candidate; acquisition has begun.
Inference remains gated on verified files and a newly frozen executable package.

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

The filenames begin `Qwen_Qwen3.5-122B-A10B-Q4_K_M-`. Mac inventory finds the
candidate absent, 128 GiB installed memory and 269 GiB free disk. These establish
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
