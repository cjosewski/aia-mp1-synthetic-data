# Recovery draft context sizing — November 18, 2026

The previous 16,384-token runtime cannot accommodate the prepared recovery
inputs as currently serialized. Five compact inputs exceed that entire context
before the system instructions, response schema, chat template or output reserve.
This is a diagnostic input-size measurement, not a successful wire preflight.

The standalone Mac `llama-tokenize` executable reported version 0.9.0, build
12110, commit `cd959bae9`. Its pinned
[implementation](https://github.com/ggml-org/llama.cpp/blob/cd959bae9/tools/tokenize/tokenize.cpp)
loads vocabulary only. It tokenized the local Qwen3.5-122B-A10B Q4_K_M model's
ten draft inputs with `--offline --no-escape --ids --show-count`. No server was
started and no inference requests were made. Model weights were not rehashed;
this observation cannot substitute for frozen runtime/model verification.

| Baseline item suffix | Pretty JSON tokens | Compact JSON tokens |
| --- | ---: | ---: |
| b01-item-0013 | 48,012 | 42,272 |
| b01-item-0050 | 23,442 | 18,733 |
| b02-item-0007 | 26,321 | 21,218 |
| b02-item-0008 | 49,041 | 43,519 |
| b02-item-0011 | 13,554 | 10,572 |
| b02-item-0014 | 23,318 | 18,379 |
| b02-item-0019 | 17,680 | 13,577 |
| b02-item-0040 | 20,287 | 15,654 |
| b02-item-0047 | 17,134 | 13,476 |
| b03-item-0011 | 15,563 | 11,969 |

Compact serialization preserves every parsed JSON value, including source and
candidate text. It removes JSON formatting whitespace only. Each input hash was
matched against the remote copy; every retained token array length matched its
reported count. All twenty tokenizer processes returned zero. Both surrounding
shell sessions returned one afterward because PowerShell piping introduced a
trailing carriage return. That orchestration error is retained in the receipt;
the completed tokenizer cases were not repeated.

Evidence is outside Git at
`artifacts/evidence/P1-03/qualification/m4-token-sizing-20261118/`, including both
input forms, raw stdout/stderr, individual exit codes, executable hash, pinned
tokenizer source, validation scripts and `sizing-summary.json`. The draft inputs
come from the separately sealed `m4-structural-source-research-20261118/packet-units`.

Before inference, choose and freeze a context that fits the **actual complete
wire request**, or revise the representation to eliminate repeated evidence
without dropping claims, source content or applicability limits. A larger
context must be tested on the separately owned evaluation server; it must not
change Herd's shared services. Recheck the scorer with its actual accepted
observations as well. No context choice, new allocation, calibration readiness
or model-quality improvement is established by this sizing exercise.

## Subsequent 65,536-token capacity check

A separately owned native Mac server successfully loaded the same local model
path with one slot, 65,536 context tokens and a 4,096-token reasoning budget on
loopback port 8082. Herd/shared services were unchanged. The WSL client used an
owned SSH tunnel and called only health, model/properties, template rendering
and tokenization endpoints; it made no inference requests.

All ten **draft fact-stage requests** fit after locked Instructor serialization,
the actual server chat template, a recorded draft system prompt, and an
8,192-token output allowance:

| Baseline item suffix | Rendered prompt tokens | Prompt + output allowance |
| --- | ---: | ---: |
| b01-item-0013 | 43,059 | 51,251 |
| b01-item-0050 | 19,520 | 27,712 |
| b02-item-0007 | 22,005 | 30,197 |
| b02-item-0008 | 44,306 | 52,498 |
| b02-item-0011 | 11,359 | 19,551 |
| b02-item-0014 | 19,166 | 27,358 |
| b02-item-0019 | 14,364 | 22,556 |
| b02-item-0040 | 16,441 | 24,633 |
| b02-item-0047 | 14,263 | 22,455 |
| b03-item-0011 | 12,756 | 20,948 |

The maximum leaves 13,038 tokens of context headroom for these exact draft
requests. This does not establish that the output allowance is sufficient for
complete model answers, that long-context inference meets the timeout, or that
the later scorer input fits. Source holds and final prompt/runtime freeze remain
open. Model weights were not rehashed in this capacity experiment.

The retained server log contains unused-tensor warnings, including the additional
`blk.48`/`nextn` tensors. Startup nonetheless reached healthy status; no claim
about inference correctness follows. Mock HTTP 400 messages printed during
Instructor serialization were intentional offline interception, not live model
failures. They did not consume model-start allocations.

Evidence: `qualification/m4-context64k-preflight-20261118/`, including the launcher,
WSL sizing script, exact wire receipts, ten fit receipts, runtime properties,
draft prompt, server log and shutdown receipt. The owned server exited zero with
`owned_server_stopped: true`; port 8082 had no listener afterward. Its SSH tunnel
was also stopped. The Mac is released. Future inference must independently
revalidate runtime identity and fit after the remaining evidence changes.
