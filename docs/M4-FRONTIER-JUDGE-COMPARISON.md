# M4 frontier judge comparison proposal

November 18, 2026. Chad proposed comparing the local judge with a frontier
model after the source-ID trial failed and the candidate-applicability
diagnostic caught its first ArcPy error. **This proposal is not an executed
assessment or a change to the local-only default.** The original 80% agreement
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

## Conditional OpenAI implementation

If Chad selects OpenAI, the proposed frontier candidate is
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
10,000 tokens per item, maximum 8,192 output tokens, at most fifty starts and
zero automatic retries. At the [listed Standard rates](https://developers.openai.com/api/docs/pricing)
of $8 per million input tokens and $40 per million output tokens, those caps
bound the fifty-call token charge at about **$20.40** before any pricing change
or provider-specific fee. Stop if the measured preflight cannot stay inside
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

The current workspace has no frontier API credential configured. Provider
selection and a credential supplied through the user's secure environment are
needed before live inference. Do not paste a secret into chat or commit it.
The source-free paired input bundle is prepared outside Git at
`artifacts/evidence/P1-03/qualification/m4-frontier-pair-v2-20261118/`:
fifty messages, ten in each category, SHA-256
`872d3ffb543574d59c391231d5228cf784cf894514041a4edb6fec048a1f1bb0`
over its structured inputs. It has **zero** model starts. The first draft
bundle retained a private project URL from rubric metadata; it is marked
`do_not_send` and was never transmitted. The v2 builder strips that metadata
and local-only source records, preserving the six scoring anchors.

Prepare the separate adapter, offline validator and create-only ledger before
inference. A chosen provider and endpoint would be recorded as
an explicit owner amendment to the runbook's local-only judge procedure;
historical local evidence remains intact. If the provider does not meet the
six separate human-agreement gates, M4 stays open and no alternate threshold
is inferred.
