# M4 source-ID development trial result

November 18, 2026. The first and only source-ID facts request completed with a
valid response. A separate technical audit rejected a materially wrong finding,
so the frozen one-rejection stop rule halted the trial before scoring. This is
development evidence, not assessed calibration. The M4 rating gap remains:
V15 has 14/20 D1 and 13/20 D6 matches; each dimension requires 16/20.

## Recorded outcome

| Measure | Result |
| --- | --- |
| Frozen allocation | Ten exposed cases, at most twenty starts |
| Actual starts / returned outcomes | 1 / 1 |
| First response | Structurally valid; `stop`; 11,769 prompt and 7,720 completion tokens |
| Check statuses | 19 supported, 3 contradicted, 4 insufficient across 26 checks |
| Fact audits accepted / rejected | 0 / 1 |
| Score starts / assessed comparisons | 0 / 0 |
| Journal halt | `semantic_audit_rejected` |
| Cumulative recovery starts | 392, including the earlier 391 |

The response correctly identified the ArcPy coordinate reference system
defects at K0008, K0009 and K0026, and left the four prepared unknown claims
insufficient. It nevertheless marked K0020 **supported** because its bound
documentation says that a Geometry object has a `type` property. K0020 asks a
different, candidate-specific question: the answer's cursor retrieves `OID@`
and `SHAPE@XY`, and it does not retrieve a geometry object through `SHAPE@` or
another step. Its advice to inspect `geometry.type` is therefore unusable as
written. A valid source ID proved only that the passage was allowed; it did not
prove that the candidate procedure met the property's prerequisite. This is
the decisive audit objection saved in the append-only journal.

The source-ID protocol removed the old exact-quote/offset failure, but this
first live result shows that passage identity alone does not solve source
applicability. The trial's advance gate required ten accepted fact/score pairs,
at least 8/10 agreement in each dimension and other safety conditions. None
of those conditions was measured or met. No human label or prior calibration
record changed. The dedicated Mac server on 8082 and Windows tunnel on 18082
were stopped after the rejection; the other Herd workload was untouched.

## Preserved evidence and next boundary

The source-ID journal, exact-wire preflight receipt, raw completion and
attributed rejection are outside Git at
`artifacts/evidence/P1-03/qualification/m4-source-id-development-20261118/`.
Its journal checkpoint is
`2ef4f47046b182dc44369da1a78d321b77a90723b940c2601eb54923e551c20d`;
`events.jsonl` SHA-256 is
`797f8c58c09562da6d4501b8b6a8c1fe3bfae3ea7bb0ab5ae30c8d9e3d501f67`.
The frozen [allocation](M4-SOURCE-ID-DEVELOPMENT-PLAN.md) and source-ID
implementation remain replayable. Do not continue this halted journal or
reinterpret its supported findings as audited facts.

The next design must test whether a cited passage establishes the **candidate's
actual prerequisite and result** for each check. It needs a new versioned,
bounded development allocation and its own technical audit before another
assessed run. A wording-only rerun of the same source-ID prompt would not
address this observed error. The original 80%-per-dimension acceptance rule
and all frozen human reviews remain in force.
