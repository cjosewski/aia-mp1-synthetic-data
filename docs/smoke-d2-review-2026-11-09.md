# First live smoke: D2 rejection review

Reviewed November 9, 2026. This is an assistant diagnostic review, not a human label, calibrated judge result or assignment acceptance.

Run: `smoke-herd-20261109T222724Z`. Evidence remains under workspace `artifacts/evidence/P1-03/smoke-herd-20261109T222724Z/`. All five initial responses passed the schema; the original gate retained three. No run files, prompts or gate rules were changed during this review.

## Reproduced cause

A read-only Python diagnostic in WSL2 extracted the two regular expressions from `src/aia_mp1/gate.py`, applied them to each saved `safety_info`, and asserted agreement with all five stored D2 decisions. It exited 0. All five texts exceed the 40-character minimum.

| Item suffix | Category | Characters | Hazard matches | Precaution matches | Stored D2 screen |
| --- | --- | ---: | --- | --- | --- |
| 0001 | GIS scripting | 118 | data loss | backup, validate | Passed |
| 0002 | AEC automation | 122 | None | Verify, use | Failed |
| 0003 | Structural analysis | 140 | failure | None | Failed |
| 0004 | CAD APIs | 167 | coordinate | review | Passed |
| 0005 | Simulation | 147 | instability, convergence | Validate, use | Passed |

### AEC automation: vocabulary coverage

Item 0002 identifies incorrect material data leading to cost estimation errors and asks for verification with a licensed structural engineer. The hazard expression recognizes neither that task-specific phrase nor `errors`, so it fails despite recognized precaution words.

This is a lexical coverage limitation, not evidence that the model omitted all hazard language. Its precaution also remains broad: it does not specify a concrete quantity/unit reconciliation or reference comparison in the safety field. A reviewer must decide whether it meets the actual specificity anchor. Adding a general word such as `error` solely to retain this item would not establish that.

### Structural analysis: inflection coverage

Item 0003 identifies structural failure and requires results to be reviewed by a licensed engineer. The precaution expression recognizes the whole word `review`, but not `reviewed`. This is a clear mismatch between the expressed review action and the lexical screen. It does not prove the answer meets every rubric requirement.

### Passing items do not establish quality

The existing expressions can also recognize words without establishing the intended meaning. For example, `use` matches both the AEC and simulation texts but is not itself evidence of a concrete precaution. These checks cannot determine whether a hazard and precaution are meaningfully connected.

Other generated content needs later rubric review. The GIS item repeats a CRS-check step in a tip; the AEC tip repeats the material-extraction API named in its steps; and the simulation text describes Dirichlet boundaries while also prescribing insulated side boundaries. These are review questions, not recorded D1-D6 labels. API existence, supported versions and engineering correctness were not independently verified in this diagnostic.

## Disposition and next work

The original gate remains failed at 3/5 retention. Do not treat these two flags as a measured 40% safety failure rate, and do not tune the generator to the gate's vocabulary.

For the next implementation plan, make heuristic diagnostics expose the individual length, hazard and precaution results; consider explicit inflection handling supported by synthetic positive and negative cases. Any revised screen must retain its heuristic designation, preserve generic-warning rejection and produce separately versioned replay evidence rather than overwriting this run. Broader semantic safety decisions belong in authentic human labeling and calibrated judging.

The approved kickoff has produced its offline verification and actual smoke result. The next substantive slice is the human-labeling and judge workflow, followed by calibration, analysis and correction. That slice needs a concrete implementation plan under the workspace's plan-before-multi-file-change rule. The engineering benchmark disposition and full assignment acceptance remain pending.

## Evidence fingerprints

SHA-256 values read during the WSL diagnostic:

| File | SHA-256 |
| --- | --- |
| `src/aia_mp1/gate.py` | `802454e6535da5c37f9ff2ff070f1de1f1d995a6e0366cf4e91b46ffe0608ff0` |
| `data.jsonl` | `0982cd72b1da200be4a16321e771ec6a9ae64dc9598de8737ca4b6602f4af13e` |
| `gate-items.jsonl` | `3eb8a47a6eb0e77cad832a60a916a0032c23511b2282c785d1e8e8fa4742cfa3` |
| `gate-report.json` | `b8d5b35d99b44806f85044fe6c4cacdbfe057f82371ed07eca2f3ca7c2dd07ea` |

No GitHub tracking changes or new model generation were performed in this review.
