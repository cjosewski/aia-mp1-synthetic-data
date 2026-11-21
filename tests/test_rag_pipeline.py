"""The assessed request path: literal goldens, the slot mapping, and the real-baseline checks.

The two goldens are literals on purpose: the gates (G1, G4, G6) rebuild their expectations with
the same code the generator uses, so a change that moves both sides together would pass them.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from rag_fixtures import base_pack

from aia_mp1 import retrieval as r
from aia_mp1.sources import context_for, validate_pack

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import check_rag_pack as check  # noqa: E402

GOLDEN_USER_CONTENT = '{"request": "Generate one new, distinct gis_scripting task for slot 1. Variant: assessed-rag-bm25-v1. Attempt: 1. Return the seven-field JSON object. Do not claim that the result has been verified.", "untrusted_reference_context": {"pack_sha256": "343a8d79ead91a7547bf95a7205a9a61aae096f89fd31bcf80aeec945b1cd138", "task": {"id": "gis_scripting-01", "brief": "Read OID@ and SHAPE@XY with a SearchCursor on scratch table 1. List routes with arcpy.ListFeatureClasses first.", "category": "gis_scripting", "source_refs": ["gis-static"]}, "sources": [{"id": "gis-static", "url": "https://example.invalid/static", "version": "synthetic-1", "retrieved_at": "2026-11-10T00:00:00+00:00", "license": "synthetic", "license_evidence": "synthetic", "attribution": "Synthetic fixture", "installation": "Synthetic installation note.", "text": "Synthetic static reference summary for gis_scripting; not upstream text.", "content_sha256": "47a7f2c5c27b11a4b35d89e0d69074ea1f4e8b4b0c7ca2100b4a46520dab68c2", "allowed_uses": ["assessed_generation", "human_review", "judge_context", "local_evidence"], "export_permission": "local_only"}]}}'

SLOT_TABLE = (
    (0, "gis_scripting", "gis_scripting-01"),
    (1, "aec_automation", "aec_automation-01"),
    (2, "structural_analysis", "structural_analysis-01"),
    (3, "cad_apis", "cad_apis-01"),
    (4, "simulation", "simulation-01"),
    (5, "gis_scripting", "gis_scripting-02"),
    (6, "aec_automation", "aec_automation-02"),
    (7, "structural_analysis", "structural_analysis-02"),
    (8, "cad_apis", "cad_apis-02"),
    (9, "simulation", "simulation-02"),
    (10, "gis_scripting", "gis_scripting-03"),
    (11, "aec_automation", "aec_automation-03"),
    (12, "structural_analysis", "structural_analysis-03"),
    (13, "cad_apis", "cad_apis-03"),
    (14, "simulation", "simulation-03"),
    (15, "gis_scripting", "gis_scripting-04"),
    (16, "aec_automation", "aec_automation-04"),
    (17, "structural_analysis", "structural_analysis-04"),
    (18, "cad_apis", "cad_apis-04"),
    (19, "simulation", "simulation-04"),
    (20, "gis_scripting", "gis_scripting-05"),
    (21, "aec_automation", "aec_automation-05"),
    (22, "structural_analysis", "structural_analysis-05"),
    (23, "cad_apis", "cad_apis-05"),
    (24, "simulation", "simulation-05"),
    (25, "gis_scripting", "gis_scripting-06"),
    (26, "aec_automation", "aec_automation-06"),
    (27, "structural_analysis", "structural_analysis-06"),
    (28, "cad_apis", "cad_apis-06"),
    (29, "simulation", "simulation-06"),
    (30, "gis_scripting", "gis_scripting-07"),
    (31, "aec_automation", "aec_automation-07"),
    (32, "structural_analysis", "structural_analysis-07"),
    (33, "cad_apis", "cad_apis-07"),
    (34, "simulation", "simulation-07"),
    (35, "gis_scripting", "gis_scripting-08"),
    (36, "aec_automation", "aec_automation-08"),
    (37, "structural_analysis", "structural_analysis-08"),
    (38, "cad_apis", "cad_apis-08"),
    (39, "simulation", "simulation-08"),
    (40, "gis_scripting", "gis_scripting-09"),
    (41, "aec_automation", "aec_automation-09"),
    (42, "structural_analysis", "structural_analysis-09"),
    (43, "cad_apis", "cad_apis-09"),
    (44, "simulation", "simulation-09"),
    (45, "gis_scripting", "gis_scripting-10"),
    (46, "aec_automation", "aec_automation-10"),
    (47, "structural_analysis", "structural_analysis-10"),
    (48, "cad_apis", "cad_apis-10"),
    (49, "simulation", "simulation-10"),
)


def request_text(category: str, slot: int, attempt: int) -> str:
    return (
        f"Generate one new, distinct {category} task for slot {slot + 1}. "
        f"Variant: {r.PROMPT_VARIANT}. Attempt: {attempt}. "
        "Return the seven-field JSON object. Do not claim that the result has been verified."
    )


def test_the_assessed_user_content_for_one_synthetic_slot_is_this_literal_text():
    pack = validate_pack(base_pack())
    context = context_for(pack, "gis_scripting", 0)
    content = json.dumps(
        {"request": request_text("gis_scripting", 0, 1), "untrusted_reference_context": context},
        ensure_ascii=False,
    )
    assert content == GOLDEN_USER_CONTENT


def test_the_slot_to_category_and_task_mapping_over_fifty_slots_is_this_literal_table():
    pack = validate_pack(base_pack())
    found = tuple(
        (
            slot,
            r.CATEGORIES[slot % 5],
            context_for(pack, r.CATEGORIES[slot % 5], slot // 5)["task"]["id"],
        )
        for slot in range(50)
    )
    assert found == SLOT_TABLE


# ---------------------------------------------------------------- the real frozen baseline
# These read the preserved baseline ledgers, so they run only when asked for explicitly.

REAL = os.environ.get("AIA_MP1_RAG_REAL_BASELINE") == "1" and check.bc.DEFAULT_EVIDENCE.is_dir()
real_only = pytest.mark.skipif(
    not REAL, reason="set AIA_MP1_RAG_REAL_BASELINE=1 with the real evidence present"
)


@real_only
def test_the_real_baseline_slot_0_attempt_1_input_equals_the_recomputed_user_content():
    from aia_mp1.tracing import read_records

    evidence = check.bc.DEFAULT_EVIDENCE
    run = evidence / "aec-course" / "baseline-001-b01"
    pack = validate_pack(json.loads((evidence / "references/engineering-v1.json").read_text()))
    starts = [
        e
        for e in read_records(run / "events.jsonl")
        if e.get("event") == "attempt_started" and e["slot"] == 0 and e["attempt_number"] == 1
    ]
    assert len(starts) == 1
    event = starts[0]
    category = r.CATEGORIES[0]
    recomputed = json.dumps(
        {
            "request": event["request"],
            "untrusted_reference_context": context_for(pack, category, 0),
        },
        ensure_ascii=False,
    )
    # Digests only: nothing recorded in the baseline is printed.
    assert (
        hashlib.sha256(recomputed.encode()).hexdigest()
        == hashlib.sha256(event["input"][-1]["content"].encode()).hexdigest()
    )


@real_only
def test_the_aec_course_baseline_loads_in_an_aec_course_process_with_all_contexts_recomputed():
    baseline = check.Baseline(check.bc.DEFAULT_EVIDENCE / "aec-course")
    outcome = check.run_in_domain(
        "baseline",
        {
            "cohort_root": str(baseline.cohort_root),
            "cohort_id": baseline.cohort_id,
            "cohort_sha256": baseline.cohort_sha256,
            "rule_identity": baseline.rule_identity,
        },
    )
    assert [row["status"] for row in outcome["checks"]] == ["pass"] * len(outcome["checks"])
    assert any(row["id"] == "G8.3" for row in outcome["checks"])
