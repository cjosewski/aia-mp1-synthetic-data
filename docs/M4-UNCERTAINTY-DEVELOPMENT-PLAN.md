# M4 bounded development trial after explicit uncertainty handling

November 18, 2026. **Prepared; no starts allocated or measured yet.** Chad
instructed Codex to proceed until the rating gap is closed. The original
80%-agreement-in-each-D1–D6 criterion and all twenty frozen human reviews remain
unchanged. This plan is a development gate, not a fourth assessed allocation.

## Fixed trial

- Ten previously exposed baseline cases, exactly two per category, from the
  version 2 packet at workspace
  `artifacts/evidence/P1-03/qualification/m4-uncertainty-packet-20261118/packet-v2`.
  Packet SHA-256:
  `b2a4ac0e5a02fd2b8277dd53270a88e035a89d21c92600c9bf793aa5864ce080`.
  It has 358 checks, 16 explicitly insufficient claims and zero holds.
- Qwen3.5-122B-A10B-Q4_K_M, exact two frozen shards. New owned Mac server on
  loopback port 8082, context 65,536, one slot, reasoning on with DeepSeek
  formatting and budget 4096. The client uses a dedicated Windows loopback
  tunnel on 18082. No Herd settings or other ports are changed.
- Fixed facts and score prompts saved verbatim in the external experiment
  manifest. Temperature 0.1, 16,384 output-token allowance, 1,200-second
  client timeout, at most one new request per released stage. Actual exact-wire
  token fit is checked immediately before each request. An oversized request
  stops without a model call. No hidden retry, automatic technical audit,
  human-label creation or score postprocessing.
- Maximum **20 model starts**: one fact observation and, only after an accepted
  fact audit, one score per case. A returned malformed response consumes its
  slot. An unknown transport outcome consumes its slot and stops the trial.
  Two consecutive structural failures or one technical-audit rejection stop it.
- Every explicitly insufficient claim must remain insufficient. An auditor
  checks fact citations and source applicability before scoring, then separately
  reviews materiality per routed dimension. Unknowns cannot become passes or
  defects through the model's assertion alone. Unresolved dimensions count as
  nonmatches and cannot qualify.

## Advance/stop decision

Only ten complete, technically audited case pairs can support advancement.
Require at least **8/10 agreement in every D1–D6**, more total matches than
the same cases under V15, no dimension regression, no increase in false
approvals, zero D2/D3 false approvals, and no unsupported decisive finding.
The outcome is development evidence. The exposed cases cannot certify assessed
calibration. If the gate fails, retain the result and stop this trial; a new
bounded design is required before more starts. If it advances, record a
separate assessed extension and run on the original frozen 20 human reviews;
readiness still requires >=16/20 **in each dimension** with complete coverage.
No successful development score can substitute for that assessed result.

ArcGIS Pro 3.7 currently fails `import arcpy` because the product license is
uninitialized. The separate ArcPy experiment is retained as a failure and is
not reused as positive evidence. The version 2 packet represents those claims
as insufficient, with their reasons and source bindings; it does not infer a
3.6 API result from an unavailable 3.7 runtime.
