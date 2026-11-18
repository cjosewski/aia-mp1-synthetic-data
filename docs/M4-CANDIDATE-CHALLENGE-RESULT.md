# M4 candidate-applicability diagnostic result

November 18, 2026. The [one-start diagnostic](M4-CANDIDATE-CHALLENGE-PLAN.md)
completed. The independent challenge reviewed all 19 tentative supports in the
first ArcPy source-ID response and correctly challenged K0020: the candidate
recommends `geometry.type` but only retrieves `OID@` and `SHAPE@XY` through its
cursor. The admitted source distinguishes `SHAPE@XY` coordinates from `SHAPE@`
Geometry objects. A separate assistant technical audit accepted the narrow
findings after inspecting the candidate and bound passages. This is **a
diagnostic success, not a judge rating or assessed calibration**.

| Measure | Recorded result |
| --- | ---: |
| Requests / returned outcomes | 1 / 1 |
| Candidate support findings reviewed | 19/19 |
| Tentative supports challenged / left unresolved | 1 / 0 |
| Challenged check | K0020 |
| Prompt / completion tokens | 9,212 / 7,773 |
| Finish reason | `stop` |
| Exact-wire token fit | 17,404 required of 65,536 context |
| Assessed ratings produced | 0 |

The challenge did not silently rewrite the earlier rejected source-ID response.
The original journal remains halted. Its source-ID format solved the old quote
offset failure but still let one unsupported candidate prerequisite through;
the challenge found that defect by asking whether the candidate actually
obtained the needed object. The result supports testing a distinct challenge
stage in a fresh development protocol. It does not show that a full ten-case
protocol, a D1/D6 score, or the original 80%-per-dimension threshold will pass.

The technical audit recorded a traceability limitation. The K0020 finding's
`candidate_passage_ids` lists the tip passage, while its explanation also cites
the answer passage. The auditor inspected the complete candidate, including
the cursor step. An integrated protocol should require explicit candidate
dependency IDs and should not count a source property alone as proof that the
candidate implemented its prerequisite.

The user subsequently shared an auto-generated course video transcript about
benchmarking prompt changes, supplying relevant context, structured outputs
and software-enforced boundaries. Those principles are useful design context
for this next protocol. The transcript's numerical examples and general claims
about effort controls are not measurements of this local Qwen/Herd setup. This
diagnostic measured one structural and semantic correction; a JSON schema by
itself did not establish factual correctness.

Raw evidence lives outside Git under workspace
`artifacts/evidence/P1-03/qualification/m4-candidate-challenge-20261118/`:
the create-only manifest, request, exact wire, model and process preflight,
durable start, raw response and attributed 19-finding audit. The audit record
SHA-256 is
`a5134dbb1ae3a0e515559d4fbc8dcaa29935c32e5b1eb8a0cf20316e7aba24cc`;
the raw-response record SHA-256 is
`f21dbfcb01ec2ca8cfc8e2193cc26cfe5f43d666a922d558a04714afa717d963`.
The dedicated Mac server and Windows SSH tunnel were stopped; no Herd service
or setting was changed. Cumulative recovery and diagnostic model starts are
393. V15 remains 95/120 with D1 14/20 and D6 13/20. M4 remains open.

**Next gate:** Build a new versioned protocol that retains raw verifier and
challenge outputs, requires a separate technical audit before using any
challenged finding, and tests the same ten exposed cases against V15 with
the declared per-dimension, false-approval and source-applicability gates.
Only then consider a distinct assessed extension on the twenty frozen reviews.
