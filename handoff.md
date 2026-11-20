# P1-03 handoff to the Linux session

## Current handoff — November 20, 2026 (rubric v2 frozen; retrieval-grounded build next)

**The conformance trial ran and failed the development gate.** See the
[result](docs/AEC-CONFORMANCE-DOCS-RESULTS.md).

- **Validity:** 8 of 10 judgments validated. The native-schema contract
  eliminated the wire trial's response errors. Both failures were lookups that
  broke the unchanged lookup schema.
- **Agreement:** **0, 3, 7, 8, 6 and 4 of ten**, worse than the control's 3, 4,
  8, 9, 8 and 8.
- **D1 (answer completeness, not API correctness):** the judge passed all
  seven answers the reviewers failed. The offline audit shows it rates D1 on
  whether stages are present. In three of the seven, it did not let its own
  "contradicted" step evidence affect the rating. The online method had the
  same pattern, so this is not caused by the conformance contract.
- **Usage:** 18 of 20 starts and 23 of 30 pages.
- **Runtime:** the server and tunnel are stopped, and offline replay is
  identical.

**Owner decisions, November 20:**

- **Switch the judge model or method** instead of iterating this Qwen prompt
  pipeline. Five consecutive revisions failed the development gate, and the
  conformance contract fixed format, not quality. A judge redesign is being
  researched. No model start occurs until the owner approves a design.
- **Constrain the lookup stage later, as a separate change,** so its effect can
  be attributed. It addresses only the two failed cases, not agreement.
- **D1 boundary:** "API errors only count against D1 when they break a step." The result doc records how this applies to the
  frozen D1 anchor. No threshold or rubric text changes.
- The owner committed the five Unit 4 answer notebooks in `f86813a` ("Notebook
  sync") for review of accuracy techniques. That review is in progress.

**Later on November 20, superseding the hosted plan above:**

- **Direction.** The owner judged the adapted project a RAG use case and chose
  to build a local, retrieval-grounded corrected generator now.
- **Hosted judge.** The hosted-judge qualification (both arms, $60, 5 days) was
  approved and is now **on hold, not started**. Nothing was amended or spent.
- **Instructor approval (owner-reported, 12:07 EST, scope confirmed).** The
  instructor approved:
  - the AEC rubric redesign;
  - the retrieval-grounded generator;
  - completion without a calibrated judge (blind human reviews measure
    before/after; the judge is descriptive);
  - a hosted judge.

  M4 no longer gates completion. The hosted qualification attempt is
  unnecessary as a gate.
- **Rubric v2 is frozen.** `config/aec-course/rubric-v2.json` has sha256
  `c366ecac…b078f` and pins the decision record
  `docs/AEC-RUBRIC-V2-INTERVIEW.md` (`249aec51…32a7`).
  - Eight binary dimensions; overall pass requires all eight.
  - Professional boundary is not exercised: none of the 50 briefs trigger it.
  - See ITERATION_LOG "Rubric v2 frozen". The original rubric is preserved.
  - Never edit either file. A change is a new, dated version.
  - Baseline answers must be reviewed blind under v2 before any before/after
    comparison.
- **Target.** Aim for a >80% relative overall-failure reduction. On a miss,
  the owner contacts the instructor.
  - The corrected generator therefore pairs retrieval (knowledge failures) with
    generation guidance aligned to the new rubric (other dimensions).
  - Freeze the rubric first and pre-register the generator. Never revise either
    after seeing review results.
- **Corrected generator.** The design and owner decisions are recorded in
  ITERATION_LOG "Corrected-generator decisions". The owner's source-use
  decisions (tier 1 and tier 2) are made.
- **Next.**
  1. Build the 8-dimension evaluation code in new modules; the D1–D6 records
     must still load. Check that the labeling tool and judge schema accept the
     v2 keys and pin its hash.
  2. Build the BM25 retrieval pack and its build gates.
  3. Get an independent review, then pre-register
     `aec-course/preregistration/corrected-rag-001.json` before any corrected
     generation.

**Workspace incident, November 20 at 10:31.** The owner's pull of `f86813a`
auto-stashed all uncommitted work into `stash@{0}` and never re-applied it.
The 32 project files were restored byte-identical at about 10:44, and the full
suite passed. The stash is kept as a backup: it also holds about 323 staged
`.omc` session-state files, which must never be committed. Before any pull,
commit or stash deliberately.

Do not rerun or rescore the conformance or wire runs. Invalid and unknown starts
remain consumed.

Runner and contract code: `tools/aec_conformance_docs.py`,
`tools/screen_aec_conformance_docs.py`. 88 synthetic tests pass, and the full
suite gives 1,118 passed and 1 skipped. Run the suite without `AIA_MP1_DOMAIN`
exported. The procedure that ran, in order: `prepare`; Mac weight verification;
owned launcher; direct tunnel; `runtime/verify-deployment.mjs` writing the
receipt; `preflight --preflight-receipt <run>/deployment.json`; `score`; a STOP
file and tunnel exit; `replay`.

### Workspace, runtime and retained evidence

Repository: `/home/chadjosewski/_Repos/aia-mp1-synthetic-data` on native Fedora 44.
The scoped Fedora migration is authorized; preserve historical WSL guards.
From the repository root:

```bash
git status --short --branch
export AIA_MP1_TOOLS="$HOME/.local/share/aia-mp1-tools"
source tools/environment.sh
export AIA_MP1_DOMAIN=aec-course
```

Use the locked environment and `uv.lock`; Python is 3.12.16. The last full suite
passed **1,118 tests, 1 skipped** after the conformance implementation. The
implementation uses its own subset validator; it adds no dependency (the design
proof's system jsonschema 4.23.0 is not used). No runtime is currently owned
by this task: the dedicated server/tunnel were stopped and ports 8082/18082 closed
at the last verified execution cleanup.

Direct Mac access is `ssh hammerhead-mp1` as `chadjosewski`, using Fedora's
dedicated key. Mac identity is `Hammerhead-Shark.local` / `192.168.0.216`.
The prior direct tunnel forwarded Fedora `127.0.0.1:18082` to Mac
`127.0.0.1:8082`; do not assume it is running. Connectivity used temporary
`mp1-direct-wifi-test` on 5 GHz after 6 GHz routing failed; recheck connectivity
if NetworkManager restarted. Do not change Herd services/settings. The frozen
native build is `b12110-cd959bae9`; fresh runtime verification and exact
schema-bearing `/apply-template` plus `/tokenize` checks precede model dispatch.

Private evidence root: `../artifacts/evidence/P1-03/aec-course/`.
Design/proof/source manifests: `../artifacts/evidence/.conformance-design-20261120/`.
Conformance execution receipts: `../artifacts/evidence/.conformance-docs-execution-20261120/`
(the preflight result, execution start, score and replay outputs, the completion
receipt and the private D1 audit table). The earlier wire receipts remain in
`../artifacts/evidence/.wire-docs-execution-20261120/`.

| Frozen identity | SHA-256 / scope |
| --- | --- |
| Conformance protocol | `98ead1c0e6cfa43c1348b846528dc46f17fc8756f957b18454b2f4f0214b30da` |
| Conformance deployment | `9ec0dafd745f84ad241c136cb5d44f485c6249a54d1687170f1e635f2314df78` |
| Conformance report | `2ac50fb50761d27a3934834e21015d0e754f4d616ca31596a15e7109e2d1f586` |
| Conformance execution completion | `1f935197ffbcc520242ea4361432b05a220fd074f2889202785f0dd5eb49d590` |
| Wire protocol (stopped parent) | `c1456135128ed96240325f84e000880430ddba8efc527bd9bdd62f85958efc08` |
| Wire execution completion | `40ccfbdc394b9a258c6b0afdd3902bb65914b2dcf1f5f7ec0a059aad4e10aaba` |
| Logical-schema proof results | `b5194e90dd9332ae64e7bdb7e805d0971f5d72908e291d6b46eecad26f2d042d` |
| Preserved ancestors | 3 compact / 48 grounded / 132 completed-online files; 21 wire source pins |
| Original transfer | 16,634 files / 468,620,606 bytes rehashed unchanged at execution verification |

The wire replay checkpoint had 44 files; the later completion receipt makes the
current stopped parent 45. Preserve the older 44-file replay claim. The original
online001 unknown outcome/lock remains intact; never unlock or retry it.

### Remaining MP1 work and planning estimate

M4 remains open. Current assessed D1–D6 agreement is **12, 15, 12, 17, 13, 11 /20**;
only D4 reaches 16/20. The completed online development method remains
**2, 3, 9, 9, 8, 8 /10**, versus control **3, 4, 8, 9, 8, 8 /10**.
Development needs complete ten-case coverage, at least 8/10 in every dimension
and the existing independent explanation audit. A passing development run does
not replace the assessed criterion of at least 16/20 in every dimension.

After judge calibration, current AEC Phase B still needs corrected collection,
authentic human reviews, paired evaluation/analysis, five charts, final evidence,
demo and coaching approval. Historical engineering-rubric corrected001 is not a
completed current-AEC correction. Courses 5–8 remain separately pending unless
Chad supplies an updated completion record.

**The earlier 3–5 working-day estimate no longer holds.** It was conditional on
the conformance revision calibrating, and it did not. No completion date can be
estimated until a judge method passes the development gate. The original
estimate read: **3–5 working days if the next judge revision calibrates**, with human review and approval available. Confidence is low: this
is not a measured completion forecast or a promised 100% date. Further judge
iterations or review delays extend it. The conformance trial is complete and failed. The
owner has chosen a new judge model or method; the next checkpoint is approving
a judge design.

Historical migration/preparation checkpoints are archived outside Git in
`../artifacts/evidence/.conformance-design-20261120/handoff-historical-checkpoints.md`.
Use the current [AEC runbook](docs/AEC-COURSE-RUNBOOK.md),
[conformance design](docs/AEC-CONFORMANCE-DESIGN.md),
[conformance result](docs/AEC-CONFORMANCE-DOCS-RESULTS.md),
[wire result](docs/AEC-WIRE-DOCS-RESULTS.md),
[wire preflight](docs/AEC-WIRE-DOCS-PREFLIGHT.md) and
[iteration log](ITERATION_LOG.md) for their reviewed records. Historical commands
and unresolved questions in the archive are not current instructions.
