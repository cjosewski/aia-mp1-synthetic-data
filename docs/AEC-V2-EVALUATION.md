# AEC rubric v2 evaluation path — design

Build step 2 of the corrected-generator design, dated November 20, 2026. It
implements the frozen rubric `config/aec-course/rubric-v2.json` (sha256
`c366ecace6fd663405d8831019d7806b47f27b5ebd71a3d38eb15d2e323b078f`, decision
record `docs/AEC-RUBRIC-V2-INTERVIEW.md`). Everything runs offline. No model is
called.

## Constraints

- **New modules only.** These files are pinned by hash in frozen evidence
  records and must not change: `assessment.py`, `labels.py`,
  `human_reference.py`, `evaluation_schemas.py`, `evaluation_cli.py`,
  `assessed_review.py`, `analysis.py`, `analysis_export.py`, `calibration.py`,
  `schemas.py`, `sources.py`, `gate.py`, `generate.py`. Importing their
  functions is allowed.
- Old D1–D6 assessments keep loading with the old code. A v1 loader refuses a
  v2 directory, and a v2 loader refuses a v1 directory, each with a clear error.
- Evidence stays outside the repository. Nothing is overwritten. Writes take
  the directory's `.writer.lock`.
- Standard library plus the locked dependencies only. `pyproject.toml` and
  `uv.lock` are unchanged.
- Rubric rules that bind the code:
  - `label_rule`: binary only; automatic passes are recorded as 1.
  - `missing_label_rules`: an unresolved label is never a pass or a failure,
    and figures are incomplete until every selected item has all eight labels.
  - `review_inputs`: reviewers see the brief and the seven fields only, under
    an opaque ID.
  - `relative_failure_reduction`: exact fractions; exactly 0.8 misses, with a
    disclosure.
  - `baseline_overall_failure_minimum` 0.15.
  - `per_dimension_pass_rate_minimum` and `overall_pass.pass_rate_minimum` 0.8
    apply to the corrected run.
  - `dataset` minimums.

## Modules

### `rubric_v2.py`

- **Constants:**
  - `RUBRIC_V2_PATH` (repository-relative);
  - `RUBRIC_V2_SHA256`;
  - `RUBRIC_V2_VERSION = "aec-rubric-v2"`;
  - `DIMENSIONS_V2 = ("fidelity", "completeness", "api_correctness",
    "verification", "safety", "professional_boundary", "tips", "clarity")`.
- **`DecisionsV2`:** strict pydantic model with the eight fields, extra
  fields forbidden, each strictly 0 or 1.
- **`HumanLabelV2`:**
  - It has the same fields as the v1 `HumanLabel`, with `decisions:
    DecisionsV2`.
  - `review_stage` is required: `blind`, `post_review` or `unknown`.
  - Optional `packet_id` and `review_id` are excluded when None.
  - `notes` may span several lines.
- **`load_rubric_v2(text=None) -> dict`:**
  - It reads the repository file when no text is given.
  - It refuses any text whose sha256 differs from `RUBRIC_V2_SHA256`.
  - It then checks:
    - `status == "frozen"`;
    - the version;
    - the dimension IDs in order;
    - `label_values == [0, 1]`;
    - that the minimums keys equal the dimension set;
    - `overall_pass.rule == "all_eight_dimensions_pass"`;
    - the professional-boundary classification is `owner_confirmed`, with 50
      tasks.
- **`boundary_triggered(rubric, task_id) -> bool`:** reads the frozen
  classification and refuses an unknown task ID.

### `assessment_v2.py`

**`create_assessment_v2(root, cohort_id, assessment_id, *, exclude_reviewed_in=(), declare_no_prior_reviews=False, seed="mp1-v1")`**

The caller must choose explicitly: list the earlier assessments in
`exclude_reviewed_in`, or pass `declare_no_prior_reviews=True`. Neither or both
is refused. `eligibility.prior_reviews` records `listed` or `declared_none`,
and the loader re-derives it.

A declaration of no prior reviews is checked, not trusted:

- Creation scans every `root/assessments/*/human-labels.jsonl` with a plain
  JSON read of each envelope's `label.item_id` and `label.payload_sha256`,
  because assessments of any version may be present.
- Creation is refused if any label matches a member of this population by item
  ID or payload hash. The error names the assessment and says to list it with
  `--exclude-reviewed-in`.
- `eligibility.prior_review_scan` records each scanned ledger as
  `{assessment_id, ledger_sha256, ledger_lines}`. It is `null` when priors are
  listed.
- The loader re-checks every recorded ledger. A ledger may have grown since
  creation, but its recorded prefix must still hash the same and still hold no
  matching label.

1. Load the cohort with the existing `cohort.load_cohort`. The population is
   `summary.members`.
2. Require:
   - a purpose of `baseline` or `corrected`;
   - at least 50 members;
   - `initial_attempt_schema_pass_rate` of at least 0.95;
   - a domain of `engineering` or `aec-course`, not `home-diy`.
3. **Eligibility rule `exclude-human-labeled-v1`.**
   - For each prior assessment ID:
     - load it with its own loader (the v1 `assessment.load_assessment` and
       `labels.load_labels`, or the v2 equivalents);
     - record `{assessment_id, manifest_sha256, ledger_sha256, ledger_lines,
       labeled_item_ids}`.
   - Excluded means a population member with any label in those ledgers. The
     member's `payload_sha256` must match the label's, or creation is refused.
   - A member under another item ID whose payload hash equals a label's in
     those ledgers is excluded too: the reviewer has already seen that exact
     content. This matches the declared-none scan. These payload twins are
     listed in `eligibility.payload_twin_ids` (also in `excluded_ids`), and the
     loader re-derives them.
   - The eligible set is the population minus the excluded members, in
     population order.
4. **Selection:** the existing `assessment.select_items(eligible, 20, seed)`.
   Refuse unless the result has exactly 4 per category.
5. **Write the assessment.**
   - Create `root/assessments/<id>/` with the existing `assessment_directory`
     and `mkdir(exist_ok=False)`.
   - Write `data.jsonl` (all population members), `rubric.json` (the exact
     frozen text), an empty `human-labels.jsonl`, `labels-checkpoint.json` and
     `manifest.json`.
   - Manifest fields:
     - `schema_version "v2-1"`, `rubric_schema "aec-rubric-v2"`,
       `source_type "cohort"`. `v2-1` is the first released v2 schema; no
       earlier v2 manifest was released. A later format change bumps the
       version, with an explicit migration;
     - the purpose, cohort ID and sha256;
     - the generator identity fields (as v1) and `reference_pack_sha256`;
     - `population_ids` and `eligibility`;
     - `selected_ids` and `selection` (algorithm, seed, count 20,
       `applied_after_eligibility: true`);
     - the rubric version and sha256, `data_sha256` and structural validity;
     - `implementation_identity()` and `manifest_sha256`.

**`load_assessment_v2(root, assessment_id) -> (directory, manifest, records, rubric)`** re-verifies everything:

- the manifest hash and ID, and the v2 schema markers;
- the cohort sha256, and that the data equals the members;
- the rubric text hash, which must equal the manifest's and `RUBRIC_V2_SHA256`;
- each prior ledger's recorded prefix (`ledger_lines` lines must still hash to
  `ledger_sha256`; ledgers are append-only);
- the recomputed exclusions, eligibility and selection.

**`item_identity_v2`** has the v1 shape.

### `labels_v2.py`

Same ledger format as v1: envelopes `{label, previous_sha256, sha256}` and a
checkpoint `{assessment_sha256, ledger_sha256, count}`.

- **`load_labels_v2`** applies v1's chain, checkpoint, UTC, identity and
  explicit-supersede checks to `HumanLabelV2`.
- **`record_label_v2`** follows v1's stage rules. After the reference is
  frozen, a `blind` stage is refused and the default is `post_review`. Before
  the freeze, the default is `unknown`.
- **No labels on a bound arm before its import.** `record_label_v2`, the
  interactive session (before any prompt) and the CLI `label` command refuse
  an assessment whose `review-packet.json` marker exists while that packet has
  no finished import (`import.json`). Otherwise the packet becomes
  unimportable and no new packet can be made. The packet import itself is
  exempt.
- **One ledger line per label.** Every append serialises the envelope exactly as
  `append_record` writes it, and refuses it unless `splitlines()` gives one
  line. JSON keeps U+2028, U+2029 and U+0085 raw, and `read_records` would split
  there, so such a character in notes or a reviewer name is refused before
  anything is written: interactive, `--notes`, amendments and packet imports.
- **`label_status_v2`.**
- **`interactive_label_v2`:**
  - It shows "Item k of n", the task brief and the seven fields, never the
    item ID, run ID, category or reference context.
  - Items come in a seeded shuffled session order, sorted by `digest({"seed",
    "assessment_id", "item_id", "order": "interactive-session-v1"})` with the
    selection seed, so k carries nothing. The selection is a
    per-category round robin, and its positions would reveal the category.
    Resuming keeps the same order and numbering.
  - It shows each dimension's name, pass anchor and fail anchor.
  - Professional boundary on an untriggered brief is recorded as 1 and shown
    as an automatic pass under F3; the reviewer is not asked for it.
  - Notes can span several lines, ending with a line holding only `.`.
  - EOF or `q` stops the session without saving that item.

### `reference_v2.py`

`freeze_reference_v2(root, assessment_id, reviewer, *, declare_blind)` and
`load_reference_v2(directory, manifest, records, *, for_scoring=False)` mirror
the v1 `human_reference.py`:

- all 20 selected items labeled, every label `blind`, one reviewer, and no
  judge evidence;
- the frozen ledger prefix;
- a withdrawal notice refuses scoring.

The reference also records the set of `packet_id` values on its labels. For
each of those packets, freezing requires its finished import:

- `import.json`'s own hash checks out;
- its `label_ids` equal the reference's labels from that packet, review ID by
  review ID;
- the submitted sheet's hash matches;
- the preserved sheet, re-parsed with `parse_packet_answers`, binds every label
  by content. The labels that name the packet must be exactly the import's
  labels for this assessment, each found by its imported label ID. For each
  review ID, the label must match:
  - the mapping entry's assessment, item and payload hash (routing);
  - the sheet's eight decisions and its notes;
  - the declared reviewer;
  - the `blind` stage;
  - `packet_id` and `review_id`.
- the started marker's declarations, and the re-parsed sheet's declarations and
  reviewer, equal those in `import.json`; `import.json` covers every review ID
  and names this packet;
- both import records name the same `parser_version`, and it is one this code
  knows. A parser change gets a new version and keeps the old version's parser,
  so that earlier imports still verify. An unknown version is refused.

A started but unfinished import is refused. So is an `import.json` with no
`import-started.json` or no `submitted-answers.md` beside it, with a
ValueError naming the packet.

### `review_packet_v2.py`: one masked packet over two assessments

**`prepare_masked_packet(root, packet_id, assessment_ids, task_pack_path, output, *, seed="mp1-v1")`**

- **Inputs.** Exactly two v2 assessments, one `baseline` and one `corrected`,
  with the same rubric sha256. Each must have no labels, no reference and no
  judge evidence. The 40 items are their 20 + 20 selected records.
- **One packet per assessment.** Preparation writes an exclusive
  `review-packet.json` marker (packet ID, packet sha256, creation time) into
  each assessment under its writer lock. It refuses an assessment that already
  has one.
- **Brief.** It is `reference_context.task.brief`. It must equal the brief for
  that task ID in the pinned task pack, whose sha256 must equal
  `rubric.target_version.source.sha256`. This guarantees identical wording in
  both arms.
- **Shuffle.**
  - Sort the items by `digest({"seed", "packet_id", "assessment_id",
    "item_id"})`, then assign opaque IDs `R01`–`R40` in that order.
  - Write `root/packets/<packet_id>/sealed-mapping.json` with `{packet_id,
    seed, entries: [{review_id, assessment_id, assessment_sha256, item_id,
    payload_sha256}]}`.
  - Write `packet.json`, which commits to the mapping's sha256 and to every
    reviewer file's sha256.
- **Write order.**
  1. Do every fallible step that binds nothing: create the output folder's
     parent and stage all reviewer files in a hidden sibling directory. A
     failure here removes the staging directory and leaves both assessments
     free for a new packet.
  2. Bind: write both assessment markers, then the packet folder,
     `sealed-mapping.json` and `packet.json`.
  3. Rename the staged folder into place last.
  
  A crash therefore never leaves a complete-looking reviewer folder for an
  unimportable packet.
- **Global rules**, rendered from `rubric-v2.json` before the dimensions, in
  this order and each under a short heading. Strings are quoted verbatim;
  dict values become labelled lines in the rubric's key order.
  - `reader` and `evidence_standard`;
  - `target_version`: `rule`, `category_targets`, `helper_software` and
    `off_target_items`, not `briefs_stating_a_version` or `source`;
  - `task_brief`: `meaning` only;
  - `terms`, `fields_rule`, `anchor_reading` and `label_rule`;
  - `professional_boundary_triggers`: `rule` and `reporting` only, never the
    per-task list.
- **Reviewer folder** (`output`, outside the repository, new):
  - `REVIEW-PACKET.md`:
    - a neutral title;
    - the global rules listed above;
    - the rubric rendered (each dimension's name, measures, pass and fail
      anchors and rules, then the tie-breaks);
    - the reviewer documentation list;
    - then, per item, `## Item Rnn`, the fenced brief and the fenced seven
      fields.
  - `MY-ANSWERS.template.md` and `MY-ANSWERS.md`, `RUNBOOK.md`,
    `rubric-v2.json` and `manifest.json`.
  - These files never contain item IDs, run IDs, assessment IDs, task IDs,
    purpose, an item's category or reference context. Category IDs appear
    only as the labels of `category_targets`, which is the same for every
    item. `rubric-v2.json` is the deliberate exception: the complete frozen
    rubric. It contains task IDs, category IDs outside `category_targets`, the
    words baseline and corrected, the provenance field names `item_id`,
    `run_id`, `trace_id` and `reference_context`, and two evidence paths: the
    task pack and the rubric's review record. It contains no arm or item
    mapping.
  - Both arms render through one function.
- **Answer-sheet declarations:**
  - `Packet`, `Reviewer`, `Review date`;
  - `Assistance used (names/tools, or NONE)`;
  - `Judge-output exposure for these items before this review (NONE or
    describe)`;
  - `I personally reviewed all forty answers and adopt these
    ratings/comments` (Yes);
  - `I completed this review without seeing judge ratings, run identities or
    arm assignments for these items` (Yes).
- **Per item:** `## Item Rnn`, then the ratings line
  `fidelity=_ | completeness=_ | api_correctness=_ | verification=_ |
  safety=_ | professional_boundary=1 | tips=_ | clarity=_`, then `Comments:`
  with free text that may span several lines.
  - `professional_boundary` is pre-filled as 1 only for untriggered briefs.

**`parse_packet_answers(text, packet)`** validates the whole sheet before
anything is written. It refuses:

- a missing or extra section, or one out of order;
- any `_` left in a rating;
- a rating other than 0 or 1;
- an empty or `_` comment;
- a missing declaration;
- a "Yes" declaration that is not Yes;
- an exposure value other than NONE;
- `professional_boundary=0` on an untriggered brief;
- a Unicode line separator (U+2028, U+2029 or U+0085) anywhere;
- an HTML comment opening, `<!--`, anywhere, because a Markdown preview hides
  commented text. A bare `-->` hides nothing and is accepted, as in
  "ModelLine --> Curve";
- a line that starts with an HTML tag (`^[ \t]*<(?!(?i:https?)://)[A-Za-z/!]`),
  such as `<div hidden>` or `<h1 hidden>`. A Markdown autolink
  (`<https://...>` or `<http://...>`) may start a line.

The last three refusals name the item or the declarations where they occur.

**`import_packet_answers(root, packet_id, answers_path, reviewer)`**

1. Verify `packet.json`, the reviewer template's hash and the mapping
   commitment.
2. Require:
   - both assessments still have zero labels and no reference;
   - both assessments' markers name this packet;
   - the packet folder holds no import marker and no submitted sheet.
3. Rebuild the mapping and flags, and refuse any difference, the coverage
   check included:
   - every entry from `seed`, `packet_id` and both manifests' `selected_ids`,
     with prepare's sort key;
   - each professional-boundary flag with `boundary_triggered`, from the mapped
     record's task.
4. Parse the sheet.
5. Require the declared reviewer to equal `reviewer`.
6. Write in this order:
   - `submitted-answers.md`, the exact bytes;
   - `import-started.json`, with the sheet's sha256, the parsed declarations
     and `parser_version`;
   - the 40 `blind` labels, with `packet_id` and `review_id`;
   - `import.json`, with the sheet's sha256, the declarations, `parser_version`
     and the label ID for each review ID.
7. A leftover `import-started.json` or `submitted-answers.md` without
   `import.json` refuses every later import until someone inspects it.

### `compare_human.py`: pure computation, no I/O

**`compute_comparison(baseline, corrected, rubric, *, course_checks) -> dict`**

- Each arm is `{assessment_id, selected_ids, labels: {item_id: decisions},
  categories: {item_id: category}}`. `decisions` maps dimension IDs to 0 or 1.
  A missing key means unresolved.
- `course_checks` is `{"baseline": {"retained_items": int,
  "initial_attempt_schema_pass_rate": float}, "corrected": {...}}`.
- `rubric` is the dict that `load_rubric_v2` returns. Thresholds are read from
  it, never hard-coded. Exact values become Fractions from their decimal
  strings, for example `Fraction(str(0.85))`.
- **Missing labels.** If any selected item lacks any dimension, the result is
  `status: incomplete`, with unresolved counts and no figures.
- **Per arm:**
  - `n` and `failing_items` (any 0);
  - `F = Fraction(failing, n)`;
  - per-dimension pass counts and exact rates.
- **Relative failure reduction (RFR).**
  - At `F_b == 0` it is `undefined`.
  - At `F_b < Fraction(3, 20)` it is `baseline_below_minimum`, not evaluable.
  - Otherwise `RFR = (F_b - F_c) / F_b` as an exact Fraction:
    - `meets_target` means `RFR > Fraction(4, 5)`;
    - `at_or_above_0_8` is also reported;
    - when it equals 4/5 exactly, add the rubric's boundary disclosure text.
- **Corrected-run checks:**
  - the overall pass rate is at least 0.8;
  - each `per_dimension_pass_rate_minimum` value is met, as at least.
- **API correctness, the targeted dimension.**
  - B3 and C3 and their relative reduction (undefined when B3 = 0).
  - Clopper–Pearson 95% intervals per arm, from exact binomial sums with
    bisection.
  - One-sided Fisher exact p for "corrected fails less", from exact
    hypergeometric Fractions.
  - `targeted_improvement` means C3 < B3 and p < 0.05.
  - The design's thresholds must hold: B3 → largest C3 with p < 0.05 is
    20→15, 18→12, 16→10, 15→8, 14→7, 12→5 and 10→4.
- **Serialization.** Fractions are written as `"n/d"` strings with a float
  beside them.
- **Course decision.** It is `pass` only when every rubric success metric
  holds:
  - RFR > 0.8;
  - the baseline failure minimum;
  - the corrected overall pass rate;
  - all eight corrected per-dimension minimums (Q5 and `success_metric_scope`);
  - the supplied course checks: each arm has at least 50 retained items and
    at least 20 labels, and each arm's initial validity is at least 0.95.
  
  If the only unmet checks are the baseline-failure minimum and the RFR target
  (`F_b` = 0 or below 0.15), the result is `not_evaluable`, which goes to the
  instructor. Otherwise any unmet check gives `fail`. Each check is reported
  separately, and the pre-registration states this rule for the owner's
  approval.

### `comparison_v2.py`: the loader

**`compare_assessments(root, baseline_id, corrected_id, declared_differences, comparison_id) -> dict`**

- **Load and refuse.** It loads both v2 assessments and their references with
  `for_scoring=True`. A missing reference counts as unfrozen; unfrozen and
  withdrawn references are both refused.
- **It requires:**
  - the purposes baseline and corrected;
  - the same rubric sha256;
  - the same reviewer;
  - the same single `packet_id` on every label in both references (one review
    session);
  - that packet's finished import, verified as for freezing; a started but
    unfinished import is refused.
- **Declared differences.**
  - Compare the two cohorts' identities:
    - the `settings` fields, except the path-valued and `purpose` fields;
      list- and dict-valued settings are compared by digest;
    - the digests of `identity.prompt`, `identity.sources`, `identity.policy`
      and `identity.implementation`;
    - `gate_rules_sha256`.
  - Every field that differs must appear in `declared_differences` (`{field:
    reason}`). An undeclared difference, or a declared field that does not
    differ, is refused.
- **Output.**
  - It calls `compute_comparison` with the course checks taken from the cohort
    summaries.
  - It saves the result with `save_new`, under `analysis/.writer.lock`, to
    `root/analysis/<comparison_id>.json`.
  - The document records the review declarations from `import.json`.
  - It records professional-boundary exercise per arm and overall as
    `{exercised, triggered_items, reporting}`.
    - `triggered_items` counts the selected items whose task triggers the
      dimension (`boundary_triggered` on `reference_context.task.id`).
    - `reporting` is the rubric's text (owner F3).
    - With nothing triggered, the dimension is reported as not exercised; its
      check stays in the decision.

### `evaluation_v2_cli.py`

`python -m aia_mp1.evaluation_v2_cli <command>`. The commands are
`create-assessment`, `status`, `label`, `prepare-packet`, `import-answers`,
`freeze-reference` (which requires `--declare-blind`) and `compare`.
`create-assessment` requires `--exclude-reviewed-in ID` (repeatable) or
`--declare-no-prior-reviews`. An expected
failure prints `error: <message>` to stderr and exits with 2, without a
traceback.

## Tests (synthetic fixtures only)

Follow the existing fixture helpers for cohorts and assessments. Run `python
-m pytest -q` in the locked environment, without `AIA_MP1_DOMAIN` exported, and
`ruff check`.

- **Rubric.**
  - The frozen file loads.
  - A one-byte change is refused.
  - The schemas reject a missing, extra or non-binary dimension.
- **Assessment.**
  - The worked example: 50 members with 20 labeled in a prior v1 assessment
    leave 30 eligible, from which 20 are selected, 4 per category,
    deterministically.
  - Re-verification refuses:
    - tampered data, rubric or manifest;
    - a rewritten prior-ledger prefix;
    - a payload-hash mismatch;
    - an existing directory, or one inside the repository;
    - an unbalanced eligible set;
    - fewer than 50 members, or validity below 0.95.
  - Old D1–D6 assessments still load, and each loader refuses the other's
    directories.
- **Labels.**
  - Round trip, chain and checkpoint tampering, and supersede rules.
  - The post-freeze stage rule.
  - Multi-line notes are preserved.
  - Interactive: `.` ends the notes, EOF saves nothing, and professional
    boundary is automatic.
- **References.** The freeze preconditions, tampered prefixes, and withdrawal
  refusing scoring.
- **Packet.**
  - 40 items with IDs R01–R40, and the same seed gives the same order.
  - No item ID, run ID, assessment ID, purpose, category or `reference_context`
    appears in any reviewer file.
  - Rendering is identical for both arms.
  - The mapping commitment is enforced.
  - Every listed refusal of an incomplete or invalid sheet.
  - The import writes 20 + 20 blind labels, and a second import is refused.
  - An interrupted import blocks later imports.
- **Comparison.**
  - Fraction results.
  - Exactly 0.8 misses and carries the disclosure.
  - `F_b = 0` is undefined; `F_b < 0.15` is not evaluable.
  - Incomplete labels give `incomplete`.
  - The Fisher threshold table holds.
  - Clopper–Pearson reference values: x=0, n=20 gives an upper bound of about
    0.1684; x=15, n=20 gives about [0.5090, 0.9134].
  - The minimums are checked.
  - The loader refuses unfrozen and withdrawn references, a different
    reviewer or packet, and undeclared or spurious declared differences, and
    accepts the declared ones.
- **CLI.** Each command's happy path, plus failures exiting with 2 and an
  error message.
