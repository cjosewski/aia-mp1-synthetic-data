# M4 bounded development trial results

November 18, 2026. The restored readiness criterion remains at least 80%
agreement **separately** in D1–D6 against the original twenty frozen human
reviews. No new qualifying rating was produced. The latest assessed baseline
remains V15 at 95/120 (79.2%): D1 14/20, D2 17/20, D3 16/20, D4 18/20,
D5 17/20, D6 13/20. The rating gap remains D1 +2 and D6 +3 matches, without
regression elsewhere.

Three independent, bounded development journals were run on the same first
ArcPy case. Each retained one model facts response and a separate attributed
technical-audit rejection. No score request or human label was created.

| Trial | Change | Decisive audit finding |
| --- | --- | --- |
| Uncertainty packet | Explicitly preserve source-unsupported facts as insufficient | K0009 and K0026 treated a task requirement as proof that the candidate preserved CRS metadata. |
| Task-fulfillment prompt | Require inspection of the complete answer | The same K0009/K0026 fulfillment error persisted. |
| Task-check packet | Clarify K0008/K0009/K0026 questions, preserving parent coverage and sources | The CRS defect was identified, but 17 of 24 source citations failed exact-substring validation. |

The third packet retained ten cases, 358 child checks, sixteen prepared
insufficient claims and zero structural holds or source gaps. Its SHA-256 is
`f405cee4dea56404401b56136ae259808e66a308d9982e516103a6227f251b3d`.
The rejected response and per-citation failure details are under workspace
`artifacts/evidence/P1-03/qualification/m4-task-check-development-20261118/`.
The first two immutable journals are in sibling directories named
`m4-uncertainty-development-20261118` and
`m4-task-fulfillment-development-20261118`. All three have one start, one
finish and one rejected audit; each schedule is halted. Total newly recorded
model starts: **3**. Cumulative starts: **391**.

The dedicated Mac server on port 8082 and Windows tunnel on port 18082 were
stopped after the third rejection. Other Herd services and settings were not
changed. The ArcGIS Pro 3.7 `arcpy` license remains uninitialized in its
separate runtime probe; it was not used as positive API evidence.

## Decision

The exact-offset citation output is an unsuitable model contract for this
judge: the model can identify the relevant claim yet cannot reliably reproduce
character offsets and exact quotes. A future trial needs a new, explicitly
versioned evidence-reference interface with application-generated exact spans
or another source-grounded mechanism. It must retain raw model output and
require independent technical audits; no silent citation repair or rating
postprocessing is authorized. These three stopped trials cannot advance to an
assessed extension or close the 80%-per-dimension gap.
