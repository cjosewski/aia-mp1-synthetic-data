# V12 input-presentation test

V11's completed audit finds 55/60 agreement, one safety false approval, four D5
false rejections and explanations that describe supplied details as missing.
It does not support advancement. The next narrow test will
change input presentation while returning to the frozen V9 canonical six-dimension
prompt. This protocol is not yet a quality result.

The original user messages contain a compact JSON object with the entire candidate
and reference context. Serialize that identical object with two-space indentation
and unescaped Unicode. Preserve every key, value, array order and string verbatim;
verify parsed equality against the original message before packaging. Do not
summarize, truncate, reorder, add facts or include ratings. This tests whether
visible field boundaries reduce omissions; it cannot guarantee better judgment.

Use V9's exact system message and the canonical Judgment schema. Keep GPT-OSS-120B,
the pinned Mac build/weights/template, context 16384, one slot, temperature 0.1,
high reasoning, 8192 output allowance and 300-second timeout fixed. Differences
from V9R1 must be limited to the user-message serialization and the new experiment
identity/accounting. No old output is reused or repaired.

Only activate a newly frozen package after the V11 ledger is closed and audited.
Record the actual cumulative starts then; allocate twenty new starts, two per
case, stopping after two consecutive failures. Unknown outcomes or changed
runtime/input identities stop dispatch. Preserve the complete return, exact
agreements and semantic review even if presentation makes no difference.

The V11 replay has now verified **139 cumulative starts**. This allocation is
therefore twenty new starts, cumulative ceiling **159**. Chad's authorization to
continue P1-03 and use the Mac covers this next test. No unused allocation carries
forward, and the V11 package/ledger remains unchanged.

Advancement still requires complete coverage, at least 80% in every dimension,
no safety/API false approvals and supported explanations on the known screen.
Fresh blind confirmation and complete assessed calibration remain later gates.
This test does not relax any rubric or course threshold.

## Measured result

All ten first attempts were valid. Agreement is **53/60**, with D1–D6 matches
**10, 9, 8, 10, 6, 10 out of ten**: two false approvals and five false rejections.
The first five score 25/30. The input-only change did not improve V9R1's 56/60.

All sixty public explanations were inspected. Case 02 falsely claims there are
no steps for box creation, placement or input preservation, although those steps
are present. It also treats the incorrect use of a real Compound API as an
unreal API. Case 04 approves read-only precautions while missing the null hazard.
Case 06 approves the invalid attribute access on the dictionary returned by
`arcpy.da.Describe`, while its D6 explanation recognizes the interface error.
D5 still falsely rejects cases 02, 04, 05 and 06. Case 09 correctly identifies the
substituted ODE and initial condition. No frozen ratings are amended.

Preparation passed **370 locked WSL tests**. All 138 frozen files and the returned
ledger replay correctly. Parsed equality confirms every original user-input
value is preserved; the V9 system messages are exact matches. No retries,
timeouts, truncations or unknown outcomes occurred. The owned server stopped and
port 8081 was verified free. Cumulative development starts are **149**.

- Plan SHA-256: `29afd18d4ad060fef1671a32df6b57f2d7810746ba5ae1d2d7ea081c9af15d77`.
- Package SHA-256: `349e5cf39ae13826865a26ffacee95b406f6daa3806cadc43edcd262c52532f8`.
- Full return: `qualification/MP1-GPTOSS120B-V12-RETURN.zip`, SHA-256
  `bdb1b0edc9ebfc684748f9cdf3960df4fff366e943e8643b7fdf33139cea6bec`.
- Replay/public review: `qualification/mp1-gptoss120b-v12-return-audit/`.

Do not qualify this protocol. Preserve the failed presentation experiment and
prepare the distinct [Qwen3.5 candidate](QWEN35-CANDIDATE.md) under its own pinned
identity, verified acquisition and bounded request allocation. No new human
review or assessed judging is started from V12.
