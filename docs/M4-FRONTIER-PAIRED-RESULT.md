# M4 source-free frontier comparison result

November 18, 2026. Chad approved GPT-6.2 Astra with a $25 ceiling. The
source-free fifty-item bundle was checked against the frozen assessment,
prompt, rubric and human-reference hash before dispatch. No local-only source
excerpt, human rating or reviewer note was sent to OpenAI. The historical V15
95/120 result used source context and remains a separate baseline.

## Hosted arm

The first JSON-mode request returned HTTP 400. Its one start and failure are
preserved separately at `qualification/m4-frontier-astra-20261118/`; the
provider returned no token usage. OpenAI's JSON mode requires the string
"JSON" in the prompt, which the frozen V15 prompt lacks. That is a likely
cause, not a captured server diagnostic. The hosted adapter then used the
model's supported strict JSON Schema response format without changing the
frozen message text. This corrected arm used a new result directory.

| Measure | GPT-6.2 Astra strict-schema arm |
| --- | ---: |
| Starts / valid completions | 50 / 50 |
| Automatic retries | 0 |
| Returned prompt + completion usage estimate | $1.98774 at listed Standard rates |
| Conservative preflight ceiling | $22.384; owner cap $25 |
| D1 agreement | 17/20 |
| D2 agreement | 17/20 |
| D3 agreement | 17/20 |
| D4 agreement | 18/20 |
| D5 agreement | 16/20 |
| D6 agreement | 17/20 |
| Total criterion matches | 102/120 (85%) |

These are agreement with Chad's **frozen human ratings**, not agreement between
models. D5 equals the 80% threshold, so a single different judgment would
change that dimension's verdict. The estimate uses returned token counts and
listed rates; it is not a provider invoice. The result directory is
`artifacts/evidence/P1-03/qualification/m4-frontier-astra-schema-20261118/`.

## Explanation audit

All 120 public justifications on the twenty human-reviewed items were read
against the candidate, task and human notes. The packet is saved as
`explanation-audit.md` beside the hosted result. The following material
discrepancies are retained rather than silently accepting the numeric gate:

- `b01-item-0031` D1 says the answer computes intersection and union areas
  with `.area`. The candidate mentions `.area` generally but never performs
  either requested area extraction. Its D1 fail decision matches the human,
  but that part of the justification overstates the procedure.
- `b03-item-0011` D1 gives credit for linking exported coordinates to the
  feature class's CRS. The candidate retrieves a spatial reference but gives
  no concrete way to preserve its identifier or WKT with exported records.
  This is one of the D1 false approvals.
- `b03-item-0041` D3 passes despite the candidate treating
  `arcpy.env.outputCoordinateSystem` as an alternative way to set buffer
  distance units. The property exists, but that is not what it does.
- `b02-item-0040` and `b02-item-0020` D4 pass despite replacing the exact
  mathematical systems in the task. Their failures remain visible in D1 and
  D5. The frozen D4 anchor is specifically about professional sign-off, so
  these two model decisions follow that anchor even though the frozen human
  ratings applied D4 more broadly. Neither side of the disagreement is erased.
- `b02-item-0010` D3 rejects the SciPy/NumPy versions named by the candidate.
  This disagreement with the frozen human rating is technically supported:
  [SciPy 1.16 requires NumPy >=1.25.2](https://docs.scipy.org/doc/scipy-1.16.1/dev/toolchain.html),
  whereas the candidate lists NumPy 1.23.5. The human rating is not rewritten.

These findings hold qualification pending the matched local result and a
conservative explanation-audit decision. The 80% threshold and human labels
are unchanged.

Chad's November 18 copy of the [course brief](COURSE-BRIEF-RECONCILIATION-20261118.md)
also requires a judge temperature lower than the generator's and Instructor
for structured judge output. Astra does not accept a temperature parameter,
and this isolated arm used OpenAI strict JSON Schema with Pydantic validation
rather than Instructor. Its numeric pass is therefore not, by itself, a
course-conforming assessed-judge qualification.

## Local control

The first local control used the same inputs with Qwen's historical 4,096-token
output cap. It stopped after two valid judgments when item 3 ended at the
length limit, leaving three starts and three recorded outcomes. That run is
preserved at `qualification/m4-local-pair-20261118/`. A new control with an
8,192-token output cap is in progress at
`qualification/m4-local-pair-b8192-20261118/`. It uses the same frozen
messages; the output-budget change is disclosed as a separate run.
