"""Versioned acceptance decisions, separate from immutable scoring rubrics."""

from .tracing import digest

COURSE_POLICY = "course-per-dimension-80-v1"
OWNER_POLICY = "owner-overall-70-20261116"
POLICIES = (OWNER_POLICY, COURSE_POLICY)


def acceptance_result(summary: dict, policy_id: str) -> dict:
    if policy_id not in POLICIES:
        raise ValueError(f"unknown acceptance policy: {policy_id}")
    dimensions = summary["dimensions"]
    matching = sum(row["matching"] for row in dimensions.values())
    compared = sum(row["compared"] for row in dimensions.values())
    missing = sum(row["missing"] for row in dimensions.values())
    course_met = compared > 0 and all(row["threshold_met"] for row in dimensions.values())
    owner = policy_id == OWNER_POLICY
    policy = {
        "id": policy_id,
        "aggregation": "overall_criterion_agreement" if owner else "each_dimension",
        "minimum": 0.7 if owner else 0.8,
        "authority": "Chad Josewski, November 16, 2026" if owner else "original course criterion",
        "decision_record": "docs/ACCEPTANCE-AMENDMENT-70.md" if owner else "docs/requirements.md",
    }
    return {
        "policy": policy,
        "policy_sha256": digest(policy),
        "matching": matching,
        "compared": compared,
        "missing": missing,
        "agreement": matching / compared if compared else None,
        "threshold_met": compared > 0 and matching * 10 >= compared * 7 if owner else course_met,
        "original_per_dimension_80_met": course_met,
    }
