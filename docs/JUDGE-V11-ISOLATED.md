# V11 independent context scoring

V9R1 achieved 56/60 agreement on the ten known development cases, with all four
disagreements in D5. V10 clarified D5 but regressed to 53/60 and six false approvals.
This experiment tests whether two independent calls reduce interference between
context clarity and technical checks. It is covered by Chad's authorization to
continue P1-03 and use the Mac. It does not change the rubric or frozen reviews.

Each original case gets two new calls: D1/D2/D3/D4/D6, then D5. Both receive the
same complete original candidate and reference message. Neither sees human labels
or the other call's output. Each has a strict subset schema. Composition requires
both valid results from this experiment; a missing stage leaves the entire item
unresolved. Historical ratings are never substituted. Report twenty stage results
separately from ten composed judgments and sixty dimension comparisons.

The new prompts retain all original rubric anchors. The model, weight checksum,
Mac server build/template, context 16384, one slot, temperature 0.1, high reasoning,
8192 output allowance and 300-second timeout remain fixed. This tests the combined
protocol/prompt change; it cannot attribute any improvement solely to splitting.

Freeze the package before inference. Allocate at most **40 new starts after 119**,
cumulative ceiling **159**, normally twenty calls, at most two attempts per stage,
with a stop after two consecutive invalid/transport outcomes. Unknown outcomes,
changed identity or token overflow stop dispatch. Unused previous allocations do
not transfer. Preserve all raw outputs and stop the separately owned Mac server.

Audit agreement by dimension and every public explanation. Known-case performance
is development evidence only. A promising protocol must be frozen before new
confirmation cases and authentic blind human reviews are collected. No assessed
judge configuration or qualification receipt changes automatically. Production
support for the two-call protocol also requires ledger/receipt integration before
assessed use; this module is an isolated development runner.

## Frozen execution identity

The preparation passed **369 locked WSL tests**, Ruff lint/format and diff checks.
The package preserves 137 files, including all original candidate/reference user
messages and the unchanged frozen human reference. Both stage schemas are hashed.
Native Mac preflight passed all twenty input-plus-output token checks with the
pinned model/runtime. The original package is also hash-verified on the NAS.

- Plan SHA-256: `4c17897a75481029ea301d3c6bfcf92d160d42fabb72aca3eed1e01d24d92dc8`.
- Package: `qualification/MP1-GPTOSS120B-V11-MAC.zip`.
- Package SHA-256: `8dfa643f5b645884c489b81c06ead2d7b398b6281fa93dc251a65768f71f2403`.

The runtime excludes only the server's random, unused media marker when comparing
restarts; all other properties, rendered prompt hashes and token counts must match.
Full observations are retained. Preparation establishes no quality result.

## Measured result

All **20 stage calls** completed on their first attempt, yielding **10 composed
judgments** and **55/60** matching dimensions. D1/D2/D3/D4/D5/D6 match counts are
**10, 9, 10, 10, 6, 10 out of ten**. There is one safety false approval and four
context false rejections. The first five cases score 26/30. Splitting did not fix
context scoring and added a safety regression relative to V9R1.

Audit of all sixty public explanations finds:

- Case 02's D5 explanation says the 6 mm offset is ignored, although the candidate
  explicitly sets `App.Vector(6, 0, 0)`. Wrong Compound/union semantics are again
  treated as context failure.
- Case 04's D5 explanation says read-only mode, active-document handling, empty
  sheets and output format are absent, although all appear in the steps. Its D2
  approval cites read-only protection while overlooking the separate null hazard
  that its own D1 and D6 explanations identify.
- Cases 05 and 06 again treat a wrong conclusion/procedure as answering another
  problem. Their frozen D5 ratings remain passes; no label is changed to improve
  agreement. Case 09 correctly identifies the substituted ODE and initial value.
- The core call correctly identifies the API ownership/interface defects in
  cases 04 and 06. Other matching explanations generally identify relevant facts,
  but these improvements do not erase the listed contradictions.

The advancement condition is not met. No fresh review request, qualification
receipt or assessed configuration change follows. Twenty starts bring the total
to **139**. There were no retries, timeouts, truncations or unknown outcomes; all
finish reasons are `stop`. The owned server stopped and port 8081 was verified free.
Frozen-code replay verifies all 137 package files and composes only complete pairs.

Full return: `qualification/MP1-GPTOSS120B-V11-RETURN.zip`, SHA-256
`696e76aacbdae00adbe7d91700c0a3d4beb41e9c875143c57b934bc5791aa8bb`.
Replay and per-item public review: `qualification/mp1-gptoss120b-v11-return-audit/`.
Next is the [formatting-only V12 test](JUDGE-V12-PRESENTATION.md), using the exact
V9 prompt and semantically identical original user inputs. Two-call production
integration is deferred because this protocol did not improve the evidence.
