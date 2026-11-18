# M4 candidate-applicability diagnostic

November 18, 2026. This is a **single-start development diagnostic**, prepared
after the [source-ID trial](M4-SOURCE-ID-TRIAL-RESULT.md) stopped on a candidate
prerequisite error. It does not amend that rejected response, score a case,
replace the V15 baseline, or qualify a judge. The original human reviews and
80%-in-every-dimension acceptance rule remain frozen.

## Question and fixed input

Can an independent challenge of the source-ID verifier's *tentatively supported*
facts identify a candidate-side prerequisite failure? The fixed test is the
first ArcPy case, `baseline-001-b02-item-0011`, from the corrected ten-case
packet. Its saved source-ID response has 19 tentative supports among 26 checks.
The decisive probe is K0020: the candidate advises `geometry.type` while its
cursor requests only `OID@` and `SHAPE@XY`. The bound source documents the
Geometry property but does not show that the answer retrieves a Geometry.

The challenge input is built from the retained raw response, frozen task,
candidate passages, bound primary excerpts and check questions. It excludes
human ratings, reviewer comments, V15 decisions and the prior technical-audit
reason. The earlier rejected response is a diagnostic input only. Application
code verifies its ordered check coverage and bound source IDs, then verifies
challenge lineage, one response per tentative support, candidate passage IDs
and allowed source IDs. A structurally valid challenge still requires separate
technical audit; a plausible explanation is not accepted automatically.

## Allocation and stop rule

- One Qwen3.5-122B-A10B-Q4_K_M request, no retry. Temperature 0.1, maximum
  8,192 completion tokens, 1,200-second timeout. The same pinned model shards
  and Mac server settings are used on an exclusively owned loopback port 8082,
  reached through an exclusively owned Windows SSH tunnel on 18082. Herd
  services and settings are outside this work.
- Verify the process, all model shards and executable hashes, server identity,
  exact Instructor wire and token fit before persisting the start. Retain raw
  completion or explicit failure. An unknown outcome consumes the one slot.
- Stop this diagnostic after the single response. The probe succeeds only if
  K0020 is challenged for the correct candidate-specific reason, all 19
  findings are structurally valid, and a separate technical audit finds no
  material counterexample among retained supports or challenged findings.
  If the model misses K0020, produces malformed output, or the audit rejects
  another decisive finding, this protocol does not advance.
- Even a successful probe would only justify designing a fresh, bounded
  ten-case development comparison with independent fact, challenge and score
  audits. The assessed extension still must reach 16/20 in each D1–D6.

The diagnostic implementation is in `recovery_candidate_challenge.py`,
`recovery_candidate_wire.py` and `tools/recovery_candidate_probe.py`. Its
create-only manifest, request, exact wire, preflight, start, raw response and
audit record belong outside Git under workspace
`artifacts/evidence/P1-03/qualification/m4-candidate-challenge-20261118/`.
No assistant-produced challenge verdict is a human label.
