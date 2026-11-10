# MP1 requirements and source decisions

This is the technical requirements record for P1-03, Mini Project 1. The [live execution checklist](https://github.com/cjosewski/aia-plan/issues/4) remains authoritative for progress. The [course brief](https://community.newline.co/ai-accelerator-cohort-2026/community?space=7764533d-9888-422e-a11c-83e00817859b) and explicit instructor decisions govern assignment acceptance.

## Source verification and early start

On November 9, 2026, the live brief's schema, six quality dimensions and success metrics were read through the signed-in course portal. The lower visualization and example-log sections were not independently reread; their checklist below comes from issue #4, also read that day. This document summarizes those sources rather than reproducing the course post.

Chad approved the first implementation slice on November 9 at 14:25 EST. He reported that Courses 1–4 are complete and that the instructor permits him to start MP1 now. He expects to finish Courses 5–8 within a week. This is an early-start decision, not evidence that Courses 5–8 or their exercises are complete. It does not resolve the benchmark adaptation or establish project acceptance.

The adopted 26-hour reference and November 10–14 window remain owned by `aia-plan/project.json`; they are not measured effort or a guaranteed completion forecast.

## First implementation slice

**November 9 continuation:** Chad stated, "The assignment has been accepted. The plan is approved. Go." Assignment acceptance is recorded as owner-reported, and the next implementation slice is authorized. Human labeling, local judge execution and calibration reporting are now implemented; real labels and model-quality evidence are still recorded only when observed. The historical kickoff scope below remains the boundary of that earlier approval. The [SDD](SDD-P1-03.md) specifies the complete project and distinguishes subsequent assessed collection/analysis work.

The approved slice covers a local repository, seven-field schema, generation through a configured local OpenAI-compatible model, bounded retries, attempt traces, independently runnable structural gating, offline tests and a five-item smoke run when a model is available. It ends with test evidence and an actual smoke result or a concrete endpoint blocker.

November 10: Chad approved the assessed-collection plan. Source packs, bounded
collection, cohort assessments and independent human-reference freezing are now
implemented. A production source pack, qualified stronger judge and live assessed
measurements remain pending. The five-item diagnostic and post-review amendments
are preserved separately; they do not certify assessed calibration.

At kickoff, human labeling, LLM judging, judge calibration, analysis charts and generator correction were subsequent work. The continuation implements the first three workflows; full analysis/charts and generator correction remain later work. The structural gate cannot establish six-dimensional quality or supply missing assessment evidence.

## Payload and categories

Every generated item's payload has exactly these fields. Run, model, category, provenance and trace metadata live in a separate envelope.

| Field | Type and constraint | Engineering meaning |
| --- | --- | --- |
| `question` | Nonblank string | A specific engineering-code question |
| `answer` | Nonblank string | Coherent guidance that addresses the question |
| `equipment_problem` | Nonblank string | The task or failure being addressed |
| `tools_required` | At least one nonblank string | Required libraries, APIs or tools |
| `steps` | At least three nonblank strings | Ordered, concrete actions |
| `safety_info` | Nonblank string | Specific correctness/data-loss hazard and precaution |
| `tips` | At least one nonblank string | Useful task-specific advice beyond the steps |

The portal's canonical field is `equipment_problem`; the copied issue calls it `problem`. Output must use `equipment_problem`. Any supported legacy input normalization must reject conflicting values and must not alter the emitted schema.

| Category ID | Topic |
| --- | --- |
| `gis_scripting` | GIS scripting and spatial-data workflows |
| `aec_automation` | AEC automation |
| `structural_analysis` | Structural-analysis code |
| `cad_apis` | CAD APIs |
| `simulation` | Nonmedical simulation |

The initial assessed batch target is 50 retained items, ten per category. Exact equal quotas avoid interpreting the source's ambiguous “20% within tolerance” wording. A balanced five-item smoke batch checks plumbing only.

## Six quality dimensions

Human reviewers and the eventual independent judge use the same versioned rubric in [config/rubric.json](../config/rubric.json). Each dimension is binary. An overall pass requires all six dimensions to pass for the same item.

| ID | Dimension | Pass anchor | Corrected pass rate |
| --- | --- | --- | ---: |
| D1 | Answer Completeness | Covers the tools, concrete actions, hazards and advice needed to finish the task | ≥85% |
| D2 | Safety Specificity | Identifies the actual hazard and a specific precaution; generic caution fails | ≥90% |
| D3 | Tool Realism → API realism | APIs and libraries exist and are available in the stated installation/version | ≥95% |
| D4 | Scope Appropriateness | Identifies when licensed-engineer review or sign-off is required | ≥95% |
| D5 | Context Clarity | Provides enough context and directly addresses `equipment_problem` | ≥90% |
| D6 | Tip Usefulness | Adds task-specific insight beyond repeated steps or generic encouragement | ≥85% |

D3 originally concerns ordinary homeowner tools; D4 concerns when repair work needs professional help. The engineering mappings above come from issue #4. Disclose them with the adaptation; do not present a local rubric as an instructor-approved amendment. Cheap checks can flag obvious defects but do not replace human or judge assessments.

## Full pipeline and evidence

| Stage | Required behavior and evidence |
| --- | --- |
| 1. Generate | Category-parameterized prompt, Pydantic/Instructor output, prompt variant, model, timestamp and raw response per attempt |
| 2. Gate | Schema validation, cheap dimension checks, deduplication, category counts, retention/rejection reasons and batch result |
| 3. Human labels | Resumable CLI; authentic human labels on at least 20 baseline and 20 corrected items, with trace IDs, timestamp and rubric version |
| 4. Judge | Independent prompt, lower temperature where supported, structured six-dimensional judgments and prompt version |
| 5. Analyze | Category/variant segment metrics, exact human/judge agreement counts, gate statistics and five charts |
| 6. Iterate | Phase A calibrates the judge on fixed items; Phase B corrects the worst segment × dimension and reruns generation/evaluation |

Each stage must be runnable independently against saved artifacts. Phase A must reach at least 80% human/judge agreement in every dimension before Phase B. Freeze the calibrated judge for the baseline/corrected comparison. Retain every prompt revision and an iteration entry with date, change, hypothesis, result, decision and next step.

Required charts are dimension pass rates before/after, a segment heatmap, agreement by dimension, category distribution and before/after paired bars. Required handoff material includes separate baseline/corrected JSONL, gate reports, labels, traces, prompt revisions, reproducible evaluation instructions, dependency lock, code identity, README, a 90–180 second demo and coaching-call approval.

## Measurement rules

| Metric | Requirement or local measurement rule |
| --- | --- |
| Assessed dataset size | At least 50 items per run, all five categories |
| Structural validity | At least 95%; report valid initial responses / initial generation slots separately from retries and retained-item validity |
| Baseline overall failure | At least 15%, established honestly |
| Corrected overall pass | At least 80% passing all six dimensions |
| Human/judge agreement | At least 80% on every dimension, with exact compared counts |
| Relative failure reduction | `(baseline_failure - corrected_failure) / baseline_failure`; target strictly greater than 0.80 until the source's equality ambiguity is resolved |

The portal states corrected failure at most 20% of baseline, while describing that as greater than 80% reduction. Issue #4 uses at least 0.80. The implementation's conservative target is strictly greater than 80%; an exact-80% result must disclose this unresolved boundary.

Retain failed first attempts, retries, filtered outputs and unresolved slots. Never compare an unfiltered baseline with a filtered corrected dataset. Missing judgments are unresolved, not passes. If baseline failure is zero, relative improvement is undefined. If a genuine baseline has less than 15% failure, preserve it and seek instructor disposition; do not introduce defects to satisfy a metric.

The initial-attempt denominator and separate retry/retention reporting are local audit controls. They make the ≥95% schema requirement inspectable without claiming that the portal specified every denominator detail.

## Source permissions and benchmark decision

[config/sources.json](../config/sources.json) identifies the current standalone authored prompt as local smoke input only. It is not a licensed external corpus, independent factual ground truth, or proof that generated API claims are correct. No third-party documentation is ingested by the kickoff source configuration.

Before adding external source material, record its URL, version/revision, retrieval date, license/terms and permitted use. Public accessibility is not permission to redistribute. Employer/client material, proprietary physiology and medical simulation are excluded.

The course benchmark `dipenbhuva/home-diy-repair-qa` supplies a uniform five-category distribution reference, not labels for generated items. Whether the engineering adaptation needs a replacement benchmark remains an instructor question. Starting MP1 early does not decide that question.

## Runtime and failure behavior

Use Python in WSL2 Ubuntu, Pydantic, Instructor and the explicitly configured local model endpoint. The full project also requires Matplotlib/Seaborn. Every assessed answer must be generated at runtime; deterministic test fixtures are marked synthetic and are never submitted as model evidence.

Bound transport timeouts and application attempts. Preserve malformed responses or explicit transport failures. Exhaustion must produce a controlled failed/incomplete result rather than an unhandled traceback or an infinite retry loop. Do not silently switch to a hosted provider, change Herd settings or overwrite a prior run.

Keep raw datasets, human labels, traces and charts outside Git under workspace `artifacts/evidence/P1-03/`. Log model and prompt identities without credentials or authorization headers. Reproducible code/configuration and reviewed summaries belong in the repository.
