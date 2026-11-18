# M4 Revit 2025 contract follow-up

November 17, 2026 (November 18 UTC evidence directory). Eleven preparation holds
are resolved by newly retained Revit 2025 documentation. The ten-case packet now
contains **358 checks, 336 prepared questions, 22 holds, one empty binding and
43 reasoning notes**. These are source-preparation counts, not verified findings
or improved agreement. No model calls, accepting audits or human labels were added.

## Sources and scope

The [ADN-DevTech reference repository](https://github.com/ADN-DevTech/revit-api-chms/tree/e5347c6f0c2258b99e303548f3d12ea1e3a1ad15)
identifies its content as Revit SDK help files. Its
[MIT license](https://github.com/ADN-DevTech/revit-api-chms/blob/e5347c6f0c2258b99e303548f3d12ea1e3a1ad15/LICENSE)
explicitly includes associated documentation. The retained pages identify Revit
2025 and, where an assembly is listed, RevitAPI 25.0.0.0. This permission does not
extend to proprietary assemblies or unrelated SDK packages.

The snapshot retains original HTML, Git blob identities, SHA-256 hashes, license,
README, extraction script and per-page extraction receipts. Excerpts use exact
byte ranges from the extracted text. The first text extraction omitted dynamic
language placeholders; it is retained as research only. The admitted R2 extractor
renders the C#/neutral placeholders, including the `null` return in GetElement.
All twelve pages are replayed against the original HTML. No application or prompt
code changed.

| Case suffix | Preparation holds resolved | New evidence |
| --- | --- | --- |
| b02-item-0007 | K0004, K0019 | Parameter collection and built-in parameter retrieval contracts |
| b02-item-0007 | K0007, K0014, K0024 | AsValueString, AsString and type-specific reporting documentation |
| b02-item-0007 | K0012, K0021 | Exact Parameter.HasValue owner and assigned-value semantics |
| b02-item-0007 | K0030 | GetElement(ElementId) return type and null-result contract |
| b02-item-0047 | K0021, K0022 | Current transaction state versus Commit outcome, including Pending and RolledBack |
| b02-item-0047 | K0025 | Complete documented Transaction property list versus TransactionAttribute.Mode |

K0023 in b02-item-0007 remains held. The AsDouble page specifies the required
storage type but does not establish the candidate's named InvalidCastException.
Absence of an exception listing does not prove that an exception cannot occur.
Likewise, documentation examples are not exhaustive demonstrations of runtime
behavior. The verifier and subsequent semantic audit must retain those limits.

## Verification and remaining work

All ten revised packets and their preceding structural reports replay. All
candidate/task text, rubric, check questions, subjects, dimensions, reasoning
notes, existing excerpts and runtime records remain unchanged. Source additions
update input fingerprints with explicit predecessor lineage. **1,217 entries
across seven previous evidence seals verify unchanged.** No real verifier
Observations, fact audits, scores or scoring audits were generated.

| Category | Remaining preparation holds |
| --- | ---: |
| GIS | 11 |
| AEC | 1 |
| Structural | 4 |
| CAD | 1 |
| Simulation | 5 |
| **Total** | **22** |

The current evidence packet is outside Git at
`artifacts/evidence/P1-03/qualification/m4-recovery-revit-contracts-20261118/packet-revit/`.
Revised Revit verifier views are 76,593 and 52,582 UTF-8 bytes. Those sizes are
not token counts or evidence of context fit. Exact token/runtime preflight and
bounded staged transport remain pending after the remaining source questions.

The Mac was not used and Herd was unchanged. Cumulative starts remain 388;
execution is disabled, the twenty-start development proposal is unallocated and
unstarted, and the three assessed allocations remain consumed. M4 still fails
the original 80%-in-every-dimension criterion; M5 remains preserved.
