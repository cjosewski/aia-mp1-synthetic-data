# V9 canonical judge development

Chad authorized continuing P1-03 to completion, with human work requested only
where necessary. This bounded experiment follows 99 retained development starts.
It does not reopen or repair any earlier run, or change frozen human ratings.

## Why change the experiment

V8/V8.1 demonstrated both formatting failures and semantic overclaims: an accepted
verifier treated incomplete source support as complete, and both scorers accepted
those findings. The supplied sources cannot resolve every claim. Merely fixing
citation IDs would not establish reliable technical judgment.

V9 retires that staged experiment for this screen and tests the original canonical
six-dimension contract with GPT-OSS-120B, explicit high reasoning effort and an
8192-token total completion allowance. The prompt retains independent rubric
anchors, checks API ownership and safeguard order, and avoids treating D5 as a
second correctness score. The complete original candidate/task/reference text is
unchanged. Authored summaries are identified as summaries; the model may use its
technical knowledge but cannot claim that an absent source supports a fact or
that code was executed. Public justifications receive a separate semantic audit.

This changes format, prompt and inference allowance together. It measures whether
the resulting candidate is promising; it cannot isolate a causal effect for any
one change. It also does not demonstrate source-complete factual verification.

## Frozen boundary

- Ten original, known development cases, two per category, in original order.
- GPT-OSS-120B MXFP4 with SHA-256
  `582bd40f6886200101f4c4ed9f25f3fe80cc14c86e9e2b37746cd8904a0c622d`.
- Same Mac and llama.cpp build, native model template, context 16384, one slot,
  temperature 0.1, explicit `reasoning_effort=high`, max output 8192 and 300-second
  request timeout. Native template rendering must confirm `Reasoning: high`.
- At most two attempts per case, twenty new starts, cumulative ceiling 119.
  Stop after two consecutive invalid/transport outcomes, unknown request outcome,
  changed identity, failed token fit, exhausted budget or all ten valid judgments.
- Exact Instructor wire requests are frozen by hashes, token-checked before any
  inference and checked again at dispatch. Every start is durable before sending;
  every raw completion/error is retained. No repair of returned JSON or ratings.
- Stop the separately owned model server on exit. Do not alter Herd.

Report all ten cases in coverage, initial validity separately from recovery,
per-dimension agreement, false approvals/rejections, and semantic defects. Compare
the first five with prior five-case screens using the same IDs; a ten-case score
must not be compared directly with a five-case percentage without that disclosure.

No automatic qualification receipt is produced. If the known-case evidence is
promising and the justifications withstand audit, freeze the protocol before
fresh blind human confirmation across all five categories. The assessed baseline
reference and its 80%-per-dimension calibration requirement remain unchanged.

## Native preflight and runtime revision

The first V9 package passed all ten native token checks. Execution then stopped
before inference because full runtime equality included llama.cpp's randomly
generated `media_marker`. A separately retained read-only diagnosis found that
this was the only differing field; rendered prompt hashes and token counts were
unchanged. Both server invocations stopped. No model requests were consumed.

The V9R1 package preserves the identical prompt, cases, rubric, reference, model,
settings and twenty-start allocation after 99. Its runtime comparison excludes
only that unused media marker for these text-only inputs. Both complete runtime
observations remain recorded. Changes to the template, settings, rendered prompt
hashes, token counts or any other runtime field still stop execution. A regression
test checks that the nonce exception cannot permit context or prompt drift.

## Measured development result

V9R1 produced ten valid first-attempt judgments in ten requests, with no retries,
timeouts or output-length failures. All 130 frozen package files and the full
returned ledger replay correctly. The server stopped and port 8081 was confirmed
free. Cumulative development starts are **109**; the earlier zero-request runtime
failure remains retained separately.

| Dimension | Matches / ten cases | False approvals | False rejections |
| --- | ---: | ---: | ---: |
| D1 | 10/10 | 0 | 0 |
| D2 | 10/10 | 0 | 0 |
| D3 | 10/10 | 0 | 0 |
| D4 | 10/10 | 0 | 0 |
| D5 | 6/10 | 0 | 4 |
| D6 | 10/10 | 0 | 0 |

Overall agreement is 56/60. On the same first five used in previous screens it is
27/30: D1/D2/D3/D4/D6 each 5/5 and D5 2/5. This equals GPT-OSS-20B V7's aggregate
27/30 while eliminating its false approval and introducing another false rejection;
it improves on GPT-OSS-120B V7's 23/30. These remain known-case development results.

The four D5 false rejections are cases 02, 04, 05 and 06: the judge penalizes wrong
procedure, unsafe implementation or a false conclusion as unclear context.
The Revit case 04 also has defective explanations despite matching failure ratings:
the judge claims the read-only command, active-document check, sheet collection and
empty-sheet handling are absent, although they appear in steps. Its D2 explanation
claims disposable/read-only precautions are absent, instead of identifying the
actual unguarded null dereference. Matching decisions alone do not qualify it.

V9R1 therefore does not advance to blind confirmation. A focused V10 prompt may
clarify the context/correctness boundary and require accurate candidate-specific
public explanations while holding all runtime settings and cases fixed.

Local evidence: `qualification/mp1-gptoss120b-v9r1-return-audit/`.
Returned archive SHA-256:
`a707c7ffdbc781a64808c03671c932dd83c52cf666496152185a4fc33419e8f7`.
