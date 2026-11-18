"""Pure first-slice screening; heuristic checks never certify rubric quality."""

from __future__ import annotations

import re
import unicodedata
from typing import get_args

from .schemas import CATEGORIES, DOMAIN, GeneratedItem, QAItem, RepairCategory

_HAZARD = re.compile(
    r"\b(?:units?|crs|coordinates?|data loss|overwrite|instability|unstable|"
    r"convergence|precision|loads?|forces?|scale|collision|invalid|corrupt\w*|"
    r"failure|risk|loss|nonphysical|singular\w*|overflow|rotation)\b",
    re.IGNORECASE,
)
_PRECAUTION = re.compile(
    r"\b(?:check|verify|validate|confirm|back\s*up|backup|review|test|"
    r"avoid|ensure|preserve|inspect|compare|use|limit|disable|save)\b",
    re.IGNORECASE,
)
_GENERIC_TIPS = {
    "be careful",
    "use caution",
    "stay safe",
    "good luck",
    "practice makes perfect",
    "take your time",
    "follow the steps",
    "follow the instructions",
    "double check your work",
}


def _normalized(text: str) -> str:
    # Unicode compatibility normalization also catches full-width/presentation variants.
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(
        " " if unicodedata.category(char).startswith("P") else char for char in normalized
    )
    return " ".join(normalized.split())


def _tip_text(text: str) -> str:
    return re.sub(r"^\d+\s+", "", _normalized(text))


def _heuristic_checks(item: QAItem) -> dict[str, dict]:
    if DOMAIN in {"home-diy", "aec-course"}:
        return _repair_checks(item)
    safety = item.safety_info
    safety_pass = (
        len(safety) >= 40 and bool(_HAZARD.search(safety)) and bool(_PRECAUTION.search(safety))
    )
    steps = {_tip_text(step) for step in item.steps}
    tip_pass = all(
        len(tip) >= 20 and _tip_text(tip) not in steps and _tip_text(tip) not in _GENERIC_TIPS
        for tip in item.tips
    )
    pending = {
        "kind": "rubric_review",
        "status": "pending",
        "reason": "Requires human and calibrated-judge evaluation; not implemented in this slice.",
    }
    return {
        "D1": dict(pending),
        "D2": {
            "kind": "heuristic",
            "status": "passed" if safety_pass else "failed",
            "reason": "At least 40 characters plus engineering hazard and precaution terms; not a safety judgment.",
        },
        "D3": dict(pending),
        "D4": dict(pending),
        "D5": dict(pending),
        "D6": {
            "kind": "heuristic",
            "status": "passed" if tip_pass else "failed",
            "reason": "Each tip has at least 20 characters and is neither a generic phrase nor a repeated step; usefulness remains ungraded.",
        },
    }


def _repair_checks(item: QAItem) -> dict[str, dict]:
    problem = set(_normalized(item.equipment_problem).split()) - {
        "the",
        "and",
        "for",
        "with",
        "does",
        "when",
        "from",
        "that",
        "this",
        "not",
    }
    safety = _normalized(item.safety_info)
    tips = [_tip_text(t) for t in item.tips]
    steps = {_tip_text(s) for s in item.steps}
    text = _normalized(" ".join([item.question, item.answer, *item.steps, item.safety_info]))
    specialist = re.search(r"\b(gas line|breaker panel|refrigerant circuit)\b", text)
    checks = {
        "D1": (
            len(item.answer) >= 100 and len(steps) >= 3,
            "Answer length and three distinct steps",
        ),
        "D2": (
            len(safety) >= 80
            and bool(
                set(safety.split())
                & {
                    "avoid",
                    "wear",
                    "unplug",
                    "disconnect",
                    "close",
                    "turn",
                    "shut",
                    "isolate",
                    "switch",
                    "keep",
                    "verify",
                    "ensure",
                    "protect",
                    "allow",
                    "use",
                    "stop",
                }
            ),
            "Specific safety field length and a precaution verb",
        ),
        "D3": (
            all(
                not re.search(
                    r"\b(trade only|professional grade|refrigerant recovery machine)\b",
                    _normalized(tool),
                )
                for tool in item.tools_required
            ),
            "Screen for explicitly specialist tools",
        ),
        "D4": (
            not specialist
            or bool(re.search(r"\b(professional|plumber|electrician|technician)\b", text)),
            "Specialist work mentions professional help",
        ),
        "D5": (
            bool(problem & set(_normalized(item.question).split()))
            and bool(problem & set(_normalized(item.answer).split())),
            "Problem terms in question and answer",
        ),
        "D6": (
            all(len(t) >= 20 and t not in steps and t not in _GENERIC_TIPS for t in tips),
            "Tips have detail and differ from steps and generic advice",
        ),
    }
    return {
        d: {"kind": "heuristic", "status": "passed" if passed else "failed", "reason": reason}
        for d, (passed, reason) in checks.items()
    }


def evaluate_gate(records: list[GeneratedItem], *, expected_count: int) -> dict:
    """Screen one run without mutating records or assigning full rubric labels.

    ``status`` describes only implemented checks and exact planned category quotas.
    ``quality_status`` remains pending even when this bounded gate passes. Input
    records have already passed schema validation; initial-attempt schema validity
    must be computed from the attempt ledger, never from this retained collection.
    """
    if type(expected_count) is not int or expected_count <= 0 or expected_count % len(CATEGORIES):
        raise ValueError("expected_count must be a positive multiple of five")
    if any(not isinstance(record, GeneratedItem) for record in records):
        raise TypeError("gate input must contain validated GeneratedItem records")
    if len({record.run_id for record in records}) > 1:
        raise ValueError("gate input must belong to one run")
    for field in ("item_id", "trace_id", "attempt_id"):
        values = [getattr(record, field) for record in records]
        if len(set(values)) != len(values):
            raise ValueError(f"gate input contains duplicate {field}")

    before = dict.fromkeys(CATEGORIES, 0)
    after_dedup = dict.fromkeys(CATEGORIES, 0)
    retained = dict.fromkeys(CATEGORIES, 0)
    seen_questions: set[str] = set()
    results = []
    accepted_ids = []
    accepted_traces = []
    duplicate_count = 0
    heuristic_rejected = 0
    for record in records:
        before[record.category] += 1
        question = _normalized(record.item.question)
        duplicate = question in seen_questions
        seen_questions.add(question)
        checks = _heuristic_checks(record.item)
        reasons = [dimension for dimension, check in checks.items() if check["status"] == "failed"]
        if duplicate:
            duplicate_count += 1
            reasons.insert(0, "duplicate_question")
        else:
            after_dedup[record.category] += 1
            if reasons:
                heuristic_rejected += 1
        accepted = not reasons
        if accepted:
            accepted_ids.append(record.item_id)
            accepted_traces.append(record.trace_id)
            retained[record.category] += 1
        results.append(
            {
                "trace_id": record.trace_id,
                "item_id": record.item_id,
                "accepted": accepted,
                "schema_status": "passed",
                "duplicate": duplicate,
                "checks": checks,
                "reasons": reasons,
            }
        )

    quota = expected_count // len(CATEGORIES)
    distribution_pass = all(count == quota for count in retained.values())
    count_pass = len(accepted_ids) == expected_count
    return {
        "schema_version": "1",
        "status": "passed" if count_pass and distribution_pass else "failed",
        "status_scope": "implemented structural, deduplication and heuristic checks only",
        "quality_status": "pending",
        "course_acceptance": "not_evaluated",
        "expected_count": expected_count,
        **(
            {
                "benchmark": {
                    "dataset": "dipenbhuva/home-diy-repair-qa",
                    "revision": "074f64327b4d19fd83052f614ca9d25f89cfe6ee",
                    "counts": dict.fromkeys(get_args(RepairCategory), 1000),
                    **(
                        {
                            "comparison_basis": "uniform fraction across five subject categories",
                            "target_fraction_per_category": 0.2,
                        }
                        if DOMAIN == "aec-course"
                        else {}
                    ),
                },
                "drops_per_check": {
                    d: sum(d in row["reasons"] for row in results)
                    for d in ("D1", "D2", "D3", "D4", "D5", "D6")
                },
            }
            if DOMAIN in {"home-diy", "aec-course"}
            else {}
        ),
        "minimum_assessed_size_met": len(accepted_ids) >= 50,
        "schema_pass_rate": None,
        "schema_pass_rate_note": "Read initial-attempt validity from the generation attempt ledger, not retained items.",
        "counts": {
            "input": len(records),
            "after_dedup": len(records) - duplicate_count,
            "accepted": len(accepted_ids),
            "duplicates": duplicate_count,
            "heuristic_rejected": heuristic_rejected,
            "missing": max(0, expected_count - len(accepted_ids)),
            "excess": max(0, len(accepted_ids) - expected_count),
        },
        "distribution": {
            "before": before,
            "after_dedup": after_dedup,
            "counts": retained,
            "target_per_category": quota,
            "policy": "exact_uniform_quota",
            "passed": distribution_pass,
        },
        "accepted_item_ids": accepted_ids,
        "accepted_trace_ids": accepted_traces,
        "items": results,
    }
