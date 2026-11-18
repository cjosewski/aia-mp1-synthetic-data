# M5 corrected collection — ready for human review

**Historical engineering cohort.** Chad selected the original course criteria
on November 18. The current review is the [new DIY baseline](DIY-COURSE-RUNBOOK.md).

**November 17 update:** [80% in every dimension is restored](ACCEPTANCE-RESTORED-80.md).
M4 is reopened. The collection and review packet below remain preserved, but
corrected judging now awaits a judge meeting the original calibration criterion.
The dated November 16 70%-overall decision and planned V13 judging are historical.

November 16, 2026. **Collection is complete and the Mac is free.** The corrected
cohort contains fifty items, ten per category. Its twenty-item blind review packet
is available at `\\192.168.0.55\aia\Handoff\P1-03\M5-corrected-review-001`.

Open `RUNBOOK.md`, read `REVIEW-PACKET.pdf`, and edit only `MY-ANSWERS.md` in that
folder. Complete the reviewer declarations, six ratings per item and comments.
Save and provide the file path. No terminal commands or model server are needed.

## Measured collection result

| Measure | Result |
| --- | ---: |
| Collection / generator variant | `corrected-001` / `assessed-api-contract-v2` |
| Completed batches / maximum | 5 / 5 |
| Initial generation slots | 250 |
| Initial schema-valid responses | 250/250 (100%) |
| Total model requests | 250 |
| Retries / failed attempts / unknown outcomes | 0 / 0 / 0 |
| Retained cohort | 50, ten per category |
| Not retained | 200 |
| Frozen human selection | 20, four per category |
| Human reviews / corrected judge results | 0 / 0 — pending |
| Recorded completion tokens | 211,579 |

The unchanged collector ran complete fifty-slot batches and stopped when all five
quotas were filled. Exclusion reasons include 156 D2 heuristic rejections, ten
cross-batch duplicate flags and forty quota-excess decisions. These reason counts
overlap and must not be added as disjoint groups. D2 here is the existing lexical
screen, not a human safety rating. Every attempt and rejected/surplus result remains
saved. No output was edited to improve a score or fill a quota.

## Controls and limitations

The [M5 plan](M5-CORRECTION-PLAN.md) targeted AEC automation × D3 API realism,
the worst baseline judge segment at 4/10 failures. The generator v2 prompt adds
owner/member/type consistency checks, guarded access and task-given preservation.
The source pack, quotas, gate policy, model weights and configured sampling remain
fixed. Generation ran from archived commit `0e9a93b` in locked WSL.

The Mac inference preflight matched the baseline GGUF SHA-256, build
`b12110-cd959bae9`, chat-template hash, four slots, 16384 tokens per slot and all
recorded sampling defaults. The host/backend changed from Windows/Herd to native
Mac/Metal; retain this limitation when interpreting any later improvement. Herd
services were not changed. No generator thinking-budget change was introduced.
One local setup helper failed before any collection/model request because it read
an absent optional config field; its correction and both preflights are retained.

The owned server PID 1755 is absent, port 8081 is clear and the launcher exited 0.
No corrected judge run has started. The frozen Qwen3.5/V13 judge will be used only
after Chad's independent reviews are complete and frozen. Acceptance remains
[70% overall agreement](ACCEPTANCE-AMENDMENT-70.md); other quality/improvement
targets are unchanged. This collection does not yet demonstrate quality improvement.

## Review and audit evidence

Paths below are relative to workspace `artifacts/evidence/P1-03/`:

- Collection: `collections/corrected-001/`; attempts/data: `corrected-001-b01/` through `corrected-001-b05/`.
- Cohort: `cohorts/corrected-cohort-001/`; assessment: `assessments/corrected-review-001/`.
- Blind packet: `reviews/corrected-review-001/`; runtime, verification and PDF checks: `qualification/m5-generator-20261116/`.
- Cohort identity: `27c46ce3b5af4ab67446630c746251b250432e9abafe1ff25c4ba9f20f513b1b`.
- Assessment identity: `d5699a410dcb945ae3bdfc7d6ca373beeb1c3cf50ffea7522e547ced739969b0`.
- Packet manifest SHA-256: `76130f6bb29d16e06abcd560eb57356c19d3cbbe21b2fc6523095661bc921c28`.
- PDF SHA-256: `0c19060159a0bc47bc6481886a618ac2eca89bf5a4b4a9cea7475e9d7b102f73`.
- M5 audit seal (72 immutable files): `204052de5d93e440f63f2b57556e5ced6dd1248ec2c9e4dd5ca5fa49612f03f9`.

The review contains the exact frozen twenty items, all seven payload fields,
reference tasks, source context and rubric. The PDF has 41 pages; text extraction
verified all 445 payload/reference text parts, and pages 1, 2 and 41 were visually
inspected. All nine packet files were verified after NAS copy. The working answer
sheet is editable; a separately hashed blank template is retained.
The 72-file evidence record is hash-verified on the NAS under
`Handoff/P1-03/operator/m5-record-20261116`. Mutable answer sheets and append-only
human ledgers are excluded from the immutable seal so authentic reviews can follow.

All 99 entries in prior baseline, V14 and acceptance-amendment seals remain
unchanged. **456 WSL tests pass**, including export selection, blank answers,
existing-review protection, complete submission validation and PDF content checks.
Ruff lint/format checks pass. M5 now awaits authentic human reviews, corrected
judging and comparison; M6 demonstration and coaching/submission remain pending.
