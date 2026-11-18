# M4 frontier judge comparison amendment

November 18, 2026. Chad proposed comparing the local judge with a frontier
model after the source-ID trial failed and the candidate-applicability
diagnostic caught its first ArcPy error. Chad then approved **GPT-6.2 Astra with
a $25 cap**. This is a separate, source-free hosted judge experiment; generation
and ordinary assessed collection remain local. It is not yet an executed
assessment. The original 80% agreement
requirement in each of D1–D6, the twenty frozen human reviews, all V13/V15
results and their reported errors remain unchanged.

## Decision to measure

Run an independently prompted frontier judge and a new local Qwen3.5 control
on the **same fifty frozen baseline answers** and compare each arm's six
ratings on the **same twenty human-reviewed answers**. Report each model's agreement with the
human ratings, false approvals, false rejections, all-six passes, invalid
responses, token usage and cost. Model-to-model agreement is descriptive;
it cannot substitute for the human reference. The frontier candidate qualifies
only with complete fifty-item coverage, at least 16/20 human agreement in
**each** dimension, an explanation audit with no material fabrication, and a
recorded stronger/distinct-model basis. A one- or two-item difference on twenty
reviews meets or misses the course threshold but is weak evidence of broader
generalization; report it as such.

All fifty baseline `reference_context.sources` entries are marked
`export_permission: local_only`. They cannot be sent to a hosted model. Build a
create-only paired input bundle containing only the authored task ID, brief and
category; the seven-field generated candidate; and the unchanged D1–D6 rubric.
Exclude source excerpts, source identifiers, URLs, versions, hashes and
permission records. A validator must verify that no local-only source content
enters the hosted wire. Give **both** arms this same source-free input and the
frozen [V15 prompt](../prompts/judge-v15-task-contract.md). The historical V15
95/120 result used source context and is retained as a reference, not presented
as a matched control. The new local and frontier results are the matched
comparison.

Neither arm receives human ratings or notes, prior judge decisions, comparison
targets or failed-case examples. Do not tune the prompt after seeing either
arm's outcomes. Use synthetic fixtures for schema and transport smoke tests
before the paired fifty-item allocation. Preserve every start and raw response
or explicit failure; an unknown outcome consumes its slot and stops pending
inspection. Never overwrite the historical local baseline or its calibration
report.

## Approved OpenAI implementation

The approved frontier candidate is
[`gpt-6.2-astra`](https://developers.openai.com/api/docs/models/gpt-6.2-astra),
which the provider describes as a frontier reasoning model with Chat
Completions and structured-output support. The existing Qwen V15 client sends
temperature 0.1. [OpenAI's current migration guide](https://developers.openai.com/api/docs/guides/latest-model)
says to omit `temperature` for this reasoning model and start with medium
reasoning effort. That unavoidable API difference must be frozen and reported;
there is no claim of numerically identical sampling settings. Use a separate
hosted adapter, API key source and result directory. A hosted endpoint is never
an automatic fallback for Herd.

Before dispatch, count the exact fifty prompts and set a hard input cap of
12,000 budgeted input tokens per item (with at most 10,000 UTF-8 message bytes),
maximum 8,192 output tokens, at most fifty starts and zero automatic retries.
At the [listed Standard rates](https://developers.openai.com/api/docs/pricing)
of $8 per million input tokens, $10 per million cache writes and $40 per
million output tokens, the conservative $10 input bound makes the fifty-call
maximum **$22.384** before any pricing change or provider-specific fee. Stop if the preflight cannot stay inside
the cap. Record actual usage and billed estimate from returned tokens; do not
represent a budget estimate as a measured cost.

Only the authored task brief, generated candidate and rubric in the sanitized
bundle are eligible to leave the local workspace. Do not send human labels,
reviewer comments, raw evidence archives, credentials, third-party source
excerpts or employer/client material. OpenAI's
[current data-controls documentation](https://developers.openai.com/api/docs/guides/your-data)
says API data is not used for training by default and lists up to thirty days
of abuse-monitoring retention for Chat Completions; the account's actual
settings must be checked before any hosted call. The hosted model cannot expose
weight checksums like the pinned local GGUF; retain exact model IDs, response
model/fingerprint if present, prompt and code hashes and request time.

## Execution boundary

The Windows and WSL process environments have no `OPENAI_API_KEY` configured.
Chad supplied the external `D:\_Repos\_AIA\.env` path; its `AIA_GPT` entry is
read as data by the isolated runner without logging the secret. Do not paste a
secret into chat or commit it.
The source-free paired input bundle is prepared outside Git at
`artifacts/evidence/P1-03/qualification/m4-frontier-pair-v2-20261118/`:
fifty messages, ten in each category, SHA-256
`872d3ffb543574d59c391231d5228cf784cf894514041a4edb6fec048a1f1bb0`
over its structured inputs. It has **zero** model starts. The first draft
bundle retained a private project URL from rubric metadata; it is marked
`do_not_send` and was never transmitted. The v2 builder strips that metadata
and local-only source records, preserving the six scoring anchors.

The separate hosted adapter and create-only ledger use fifty starts, zero SDK
retries, medium reasoning effort, JSON output validation and a conservative
input/cache-write rate in their preflight. The local control still needs a
matching source-free run. This approval is an explicit owner amendment to the
runbook's local-only judge procedure;
historical local evidence remains intact. If the provider does not meet the
six separate human-agreement gates, M4 stays open and no alternate threshold
is inferred.

## Operator commands

Run these in WSL2 Ubuntu with `AIA_MP1_TOOLS` set and
`source tools/environment.sh` completed. Keep each output path new. The
`--preflight` command performs the full input and human-reference integrity
check without contacting OpenAI:

```bash
ROOT=/mnt/d/_Repos/_AIA/artifacts/evidence/P1-03
BUNDLE="$ROOT/qualification/m4-frontier-pair-v2-20261118"
uv run --locked python tools/run_frontier_pair.py \
  --bundle "$BUNDLE" --artifact-root "$ROOT" --preflight
```

Set `OPENAI_API_KEY` in the dispatch process through a secure local environment,
or pass `--credential-file /mnt/d/_Repos/_AIA/.env` to read Chad's `AIA_GPT`
entry. The file path is external to Git. Do not put the key value in the command
line, runbook, repository or chat. Check the
account's data-controls and current Standard prices before starting. The
hosted arm writes each start before its request and stops after its first
invalid or unknown result; never rerun the command against the same output.

```bash
uv run --locked python tools/run_frontier_pair.py \
  --bundle "$BUNDLE" --artifact-root "$ROOT" \
  --credential-file /mnt/d/_Repos/_AIA/.env \
  --output "$ROOT/qualification/m4-frontier-astra-20261118"
```

For the local control, first verify that the owned loopback tunnel points to
the dedicated Mac Qwen3.5-122B-A10B-Q4_K_M server and does not conflict with
other Herd work. The exact served model ID comes from `/v1/models`. Warn Chad
before taking control of the Mac. Then run:

```bash
uv run --locked python tools/run_local_pair.py \
  --bundle "$BUNDLE" --artifact-root "$ROOT" \
  --endpoint http://127.0.0.1:PORT/v1 --model EXACT_SERVED_MODEL_ID \
  --output "$ROOT/qualification/m4-local-pair-20261118"
```

After both arms have fifty valid results, `tools/report_paired_judges.py`
creates a separate, local-only agreement report. Inspect all 120 public
justifications and complete the technical explanation audit before a
qualification claim. Neither the human reference nor this comparison report
is sent to OpenAI.
