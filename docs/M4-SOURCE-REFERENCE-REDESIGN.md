# M4 source-reference redesign

November 18, 2026. The three bounded recovery trials stopped before scoring.
The final verifier recognized the ArcPy CRS defects, but 17 of 24 citations
failed exact-quote/character-offset validation. Earlier [V7 passage-ID
development](JUDGE-PASSAGE-PROTOCOL.md) accepted all five first responses while
showing that valid IDs alone do not establish correct decisions. This redesign
uses both findings: make evidence references simple to reproduce and keep
technical judgment under separate audit.

## Implemented offline prototype

`recovery_source_refs.py` adds `recovery-source-refs-v1`. For every frozen check,
the verifier returns a status, explanation and zero or more exact
`(passage_id, version)` pairs from that check's application-supplied binding.
Application code verifies plan identity, ordered complete check coverage,
duplicate/foreign references and the original source bundle. A supported or
contradicted finding needs at least one bound reference. An insufficient finding
remains unresolved. IDs resolve to the full immutable source passage; the model
does not invent quotes or count character offsets. The technical auditor must
still inspect whether each cited passage actually supports the claim, including
API owner, version and task fulfillment.

`recovery_source_scoring.py` adds a separate offline score input and response
shape. The scorer returns effects for every required check and candidate passage
IDs for each resolved dimension. It cannot convert an insufficient fact into
support or a defect, reverse an audited contradiction, pass with a decisive
defect, or omit required materiality review. Fact and score audits remain
attributed and separate. The output is development-only and never a human
label or assessed calibration receipt.

The prototype leaves the earlier exact-offset implementation and its
hash-pinned journals unchanged. It has **no live dispatch, durable versioned
journal, preflight runner or assessed projection yet**. The next integration
must bind the ID protocol to a new immutable journal and retain raw completions,
single-start transport semantics, source/packet fingerprints, Mac/tunnel
ownership and exact-wire token checks. It must not reinterpret earlier trial
outputs as valid ID responses.

The first corrected-packet case replayed offline with 26 checks and no model
call. Its frozen request is under workspace
`artifacts/evidence/P1-03/qualification/m4-source-refs-offline-20261118/`;
request SHA-256 is
`6b1e311ccb689369cb03368f1b840a194e76463ecf9d7ddd1fe2b558aada4769`.
The locked WSL suite passed **764 tests**, with one existing optional
`reportlab` import skip; the new 15 focused source-ID tests passed.

## Measurement gate

After integration, freeze prompts and settings before model use. Run a bounded
ten-case exposed development comparison with independent technical audits and
the existing stop rules. Advance only with complete audited coverage, at least
8/10 agreement in every D1–D6, no dimension regression against V15 on the same
cases, no increase in false approvals, zero D2/D3 false approvals and no
unsupported decisive finding. A separate assessed run on the original frozen
twenty human labels must still reach at least 16/20 in every dimension. No
source-ID validity count by itself closes the rating gap.
