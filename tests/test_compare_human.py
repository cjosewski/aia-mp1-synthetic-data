"""Exact before/after statistics over synthetic blind human labels (aec-rubric-v2)."""

import copy
import json
import re
from fractions import Fraction
from pathlib import Path

import pytest

from aia_mp1.compare_human import clopper_pearson, compute_comparison, fisher_exact_one_sided

RUBRIC = json.loads(
    (Path(__file__).resolve().parents[1] / "config/aec-course/rubric-v2.json").read_text()
)
DIMENSIONS = (
    "fidelity",
    "completeness",
    "api_correctness",
    "verification",
    "safety",
    "professional_boundary",
    "tips",
    "clarity",
)
CATEGORIES = ("gis_scripting", "aec_automation", "structural_analysis", "cad_apis", "simulation")
# A corrected item may fail one of these each while every per-dimension minimum still holds.
SPREAD = ("tips", "clarity", "completeness", "verification", "fidelity", "safety")
# Failures allowed among 20 corrected items by the frozen per-dimension minimums.
ALLOWED_FAILURES = {
    "fidelity": 2,
    "completeness": 3,
    "api_correctness": 1,
    "verification": 3,
    "safety": 2,
    "professional_boundary": 1,
    "tips": 3,
    "clarity": 3,
}
COURSE = {
    "baseline": {"retained_items": 50, "initial_attempt_schema_pass_rate": 0.95},
    "corrected": {"retained_items": 50, "initial_attempt_schema_pass_rate": 0.95},
}
FIRST = "synthetic-baseline-item-0001"


def arm(name, fails=None, *, n=20):
    """A synthetic arm of n items; fails maps a dimension to the indexes of items failing it."""
    ids = [f"synthetic-{name}-item-{i:04d}" for i in range(1, n + 1)]
    fails = fails or {}
    return {
        "assessment_id": f"synthetic-{name}",
        "selected_ids": ids,
        "labels": {
            item: {d: 0 if i in fails.get(d, ()) else 1 for d in DIMENSIONS}
            for i, item in enumerate(ids)
        },
        "categories": {item: CATEGORIES[i % 5] for i, item in enumerate(ids)},
    }


def baseline(failing, *, n=20):
    """Baseline whose first `failing` items fail API correctness."""
    return arm("baseline", {"api_correctness": range(failing)}, n=n)


def corrected(failing, *, n=20):
    """Corrected run whose first `failing` items each fail a different non-API dimension."""
    return arm("corrected", {d: [i] for i, d in enumerate(SPREAD[:failing])}, n=n)


def compare(base, corr, *, rubric=RUBRIC, course=COURSE):
    return compute_comparison(base, corr, rubric, course_checks=course)


def rubric_with(path, value):
    rubric = copy.deepcopy(RUBRIC)
    *parents, last = path
    target = rubric
    for key in parents:
        target = target[key]
    target[last] = value
    return rubric


def exact_values(value):
    if isinstance(value, dict):
        if set(value) == {"fraction", "float"}:
            yield value
        else:
            for item in value.values():
                yield from exact_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from exact_values(item)


def test_arm_figures_are_exact_counts_and_rates():
    base = arm("baseline", {"api_correctness": range(9), "tips": range(3)})
    result = compare(base, corrected(0))
    assert result["status"] == "complete"
    b = result["arms"]["baseline"]
    assert (b["assessment_id"], b["n"], b["failing_items"]) == ("synthetic-baseline", 20, 9)
    assert b["failure_rate"] == {"fraction": "9/20", "float": 0.45}
    assert b["overall_pass_rate"] == {"fraction": "11/20", "float": 0.55}
    assert list(b["dimensions"]) == list(DIMENSIONS)
    assert b["dimensions"]["api_correctness"] == {
        "pass_count": 11,
        "pass_rate": {"fraction": "11/20", "float": 0.55},
    }
    assert b["dimensions"]["tips"] == {
        "pass_count": 17,
        "pass_rate": {"fraction": "17/20", "float": 0.85},
    }
    assert b["dimensions"]["fidelity"]["pass_rate"] == {"fraction": "1/1", "float": 1.0}
    assert b["categories"] == {
        "aec_automation": {"n": 4, "failing_items": 2},
        "cad_apis": {"n": 4, "failing_items": 2},
        "gis_scripting": {"n": 4, "failing_items": 2},
        "simulation": {"n": 4, "failing_items": 1},
        "structural_analysis": {"n": 4, "failing_items": 2},
    }
    assert result["arms"]["corrected"]["failure_rate"] == {"fraction": "0/1", "float": 0.0}


@pytest.mark.parametrize(("baseline_failing", "corrected_failing"), [(10, 2), (15, 3), (20, 4)])
def test_reduction_of_exactly_four_fifths_misses_and_carries_the_disclosure(
    baseline_failing, corrected_failing
):
    result = compare(baseline(baseline_failing), corrected(corrected_failing))
    reduction = result["relative_failure_reduction"]
    assert reduction["status"] == "evaluated"
    assert reduction["value"] == {"fraction": "4/5", "float": 0.8}
    assert reduction["meets_target"] is False
    assert reduction["at_or_above_0_8"] is True
    assert (
        reduction["boundary_disclosure"]
        == RUBRIC["relative_failure_reduction"]["exact_boundary_rule"]
    )
    assert result["course_decision"]["result"] == "fail"
    assert result["course_decision"]["unmet"] == ["relative_failure_reduction_target"]


def test_reduction_above_four_fifths_with_every_check_met_passes():
    result = compare(baseline(11), corrected(2))
    reduction = result["relative_failure_reduction"]
    assert reduction["value"] == {"fraction": "9/11", "float": 9 / 11}
    assert reduction["target"] == {"operator": ">", "value": {"fraction": "4/5", "float": 0.8}}
    assert (reduction["meets_target"], reduction["at_or_above_0_8"]) == (True, True)
    assert reduction["boundary_disclosure"] is None
    decision = result["course_decision"]
    assert decision["result"] == "pass"
    assert decision["unmet"] == []
    assert decision["checks"] and all(decision["checks"].values())
    # Exactly 50 retained items and exactly 0.95 validity meet their minimums.
    checks = result["course_checks"]["corrected"]
    assert checks["retained_items"] == {"observed": 50, "minimum": 50, "met": True}
    assert checks["human_labels"] == {"observed": 20, "minimum": 20, "met": True}
    assert checks["initial_attempt_schema_pass_rate"] == {
        "observed": {"fraction": "19/20", "float": 0.95},
        "minimum": {"fraction": "19/20", "float": 0.95},
        "met": True,
    }


def test_inputs_are_left_unchanged():
    base, corr = baseline(11), corrected(2)
    rubric, course = copy.deepcopy(RUBRIC), copy.deepcopy(COURSE)
    before = copy.deepcopy((base, corr, rubric, course))
    compute_comparison(base, corr, rubric, course_checks=course)
    assert (base, corr, rubric, course) == before


def test_reduction_below_four_fifths_fails():
    result = compare(baseline(10), corrected(3))
    reduction = result["relative_failure_reduction"]
    assert reduction["value"] == {"fraction": "7/10", "float": 0.7}
    assert (reduction["meets_target"], reduction["at_or_above_0_8"]) == (False, False)
    assert reduction["boundary_disclosure"] is None
    assert result["course_decision"]["result"] == "fail"
    assert result["course_decision"]["unmet"] == ["relative_failure_reduction_target"]


def test_a_corrected_run_worse_than_baseline_gives_a_negative_exact_reduction():
    reduction = compare(baseline(4), corrected(6))["relative_failure_reduction"]
    assert reduction["value"] == {"fraction": "-1/2", "float": -0.5}
    assert reduction["meets_target"] is False


@pytest.mark.parametrize(
    ("baseline_failing", "status"),
    [(0, "undefined"), (1, "baseline_below_minimum"), (2, "baseline_below_minimum")],
)
def test_zero_or_below_minimum_baseline_failure_is_not_evaluable(baseline_failing, status):
    result = compare(baseline(baseline_failing), corrected(0))
    reduction = result["relative_failure_reduction"]
    assert reduction["status"] == status
    assert reduction["value"] is None
    assert (reduction["meets_target"], reduction["at_or_above_0_8"]) == (False, False)
    assert reduction["boundary_disclosure"] is None
    assert reduction["baseline_failure_minimum"] == {"fraction": "3/20", "float": 0.15}
    assert result["course_decision"]["result"] == "not_evaluable"
    assert result["course_decision"]["unmet"] == [
        "baseline_failure_minimum",
        "relative_failure_reduction_target",
    ]


def test_baseline_failure_of_exactly_the_minimum_is_evaluated():
    result = compare(baseline(3), corrected(0))
    reduction = result["relative_failure_reduction"]
    assert reduction["baseline_failure"] == {"fraction": "3/20", "float": 0.15}
    assert reduction["status"] == "evaluated"
    assert reduction["value"] == {"fraction": "1/1", "float": 1.0}
    assert result["course_decision"]["result"] == "pass"


def test_an_unevaluable_reduction_with_another_unmet_check_is_a_failure():
    course = copy.deepcopy(COURSE)
    course["corrected"]["retained_items"] = 49
    decision = compare(baseline(0), corrected(0), course=course)["course_decision"]
    assert decision["result"] == "fail"
    assert decision["unmet"] == [
        "corrected_retained_items",
        "baseline_failure_minimum",
        "relative_failure_reduction_target",
    ]


@pytest.mark.parametrize(("failing", "observed", "met"), [(4, "4/5", True), (5, "3/4", False)])
def test_corrected_overall_pass_rate_minimum_is_inclusive(failing, observed, met):
    result = compare(baseline(20), corrected(failing))
    row = result["corrected_minimums"]["overall_pass_rate"]
    assert row["observed"]["fraction"] == observed
    assert row["minimum"] == {"fraction": "4/5", "float": 0.8}
    assert row["met"] is met
    assert ("corrected_overall_pass_rate" in result["course_decision"]["unmet"]) is not met


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_per_dimension_minimums_are_inclusive_at_their_exact_boundaries(dimension):
    allowed = ALLOWED_FAILURES[dimension]
    for failing, met in ((allowed, True), (allowed + 1, False)):
        result = compare(baseline(20), arm("corrected", {dimension: range(failing)}))
        minimums = result["corrected_minimums"]
        assert minimums["dimensions"][dimension]["met"] is met, failing
        assert minimums["all_met"] is met
        unmet = result["course_decision"]["unmet"]
        assert (f"corrected_{dimension}_pass_rate" in unmet) is not met


@pytest.mark.parametrize(
    ("side", "field", "value", "check"),
    [
        ("baseline", "retained_items", 49, "baseline_retained_items"),
        ("corrected", "retained_items", 49, "corrected_retained_items"),
        (
            "baseline",
            "initial_attempt_schema_pass_rate",
            0.9499,
            "baseline_initial_attempt_schema_pass_rate",
        ),
        (
            "corrected",
            "initial_attempt_schema_pass_rate",
            0.94,
            "corrected_initial_attempt_schema_pass_rate",
        ),
    ],
)
def test_each_course_check_failure_blocks_a_pass(side, field, value, check):
    course = copy.deepcopy(COURSE)
    course[side][field] = value
    result = compare(baseline(11), corrected(2), course=course)
    assert result["relative_failure_reduction"]["meets_target"] is True
    assert result["course_decision"]["result"] == "fail"
    assert result["course_decision"]["unmet"] == [check]


def test_fewer_than_twenty_labeled_items_per_arm_blocks_a_pass():
    result = compare(baseline(11, n=19), corrected(2, n=19))
    assert result["relative_failure_reduction"]["meets_target"] is True
    assert result["course_checks"]["baseline"]["human_labels"] == {
        "observed": 19,
        "minimum": 20,
        "met": False,
    }
    assert result["course_decision"]["result"] == "fail"
    assert result["course_decision"]["unmet"] == ["baseline_human_labels", "corrected_human_labels"]


def test_unresolved_labels_give_incomplete_with_counts_and_no_figures():
    base = baseline(10)
    del base["labels"][FIRST]
    corr = corrected(0)
    del corr["labels"][corr["selected_ids"][5]]["tips"]
    result = compare(base, corr)
    assert result["status"] == "incomplete"
    assert set(result) == {
        "comparison_schema",
        "rubric_version",
        "status",
        "arms",
        "course_decision",
    }
    assert result["rubric_version"] == "aec-rubric-v2"
    assert result["course_decision"] == {"result": "incomplete"}
    assert result["arms"]["baseline"] == {
        "assessment_id": "synthetic-baseline",
        "selected_items": 20,
        "unresolved_items": 1,
        "unresolved_by_dimension": dict.fromkeys(DIMENSIONS, 1),
    }
    assert result["arms"]["corrected"] == {
        "assessment_id": "synthetic-corrected",
        "selected_items": 20,
        "unresolved_items": 1,
        "unresolved_by_dimension": {d: int(d == "tips") for d in DIMENSIONS},
    }


def test_one_unresolved_dimension_in_one_arm_withholds_every_figure():
    corr = corrected(0)
    del corr["labels"][corr["selected_ids"][0]]["api_correctness"]
    result = compare(baseline(10), corr)
    assert result["status"] == "incomplete"
    assert result["arms"]["baseline"]["unresolved_items"] == 0
    assert result["arms"]["corrected"]["unresolved_by_dimension"]["api_correctness"] == 1
    assert not set(result["arms"]["baseline"]) & {"failure_rate", "failing_items", "dimensions"}


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda a: a["labels"][FIRST].update(api_correctness=2), "0 or 1"),
        (lambda a: a["labels"][FIRST].update(api_correctness=-1), "0 or 1"),
        (lambda a: a["labels"][FIRST].update(api_correctness=True), "0 or 1"),
        (lambda a: a["labels"][FIRST].update(api_correctness=None), "0 or 1"),
        (lambda a: a["labels"][FIRST].update(api_correctness=1.0), "0 or 1"),
        (lambda a: a["labels"][FIRST].update(api_correctness="1"), "0 or 1"),
        (lambda a: a["labels"][FIRST].update(D3=1), "unknown dimension"),
        (lambda a: a["labels"][FIRST].update(tool_realism=0), "unknown dimension"),
        (lambda a: a["labels"].update({FIRST: [1] * 8}), "decisions"),
        (lambda a: a["labels"].update({"synthetic-other-item-0001": {}}), "unselected"),
        (lambda a: a["categories"].pop(FIRST), "categories"),
        (
            lambda a: a["categories"].update({"synthetic-other-item-0001": "simulation"}),
            "categories",
        ),
        (lambda a: a["selected_ids"].append(FIRST), "duplicate"),
        (lambda a: a.update(selected_ids=[], labels={}, categories={}), "selected_ids"),
        (lambda a: a.update(purpose="baseline"), "fields"),
        (lambda a: a.pop("categories"), "fields"),
        (lambda a: a.update(assessment_id=""), "assessment_id"),
    ],
)
def test_malformed_arms_are_refused(mutate, message):
    base = baseline(10)
    mutate(base)
    with pytest.raises(ValueError, match=message):
        compare(base, corrected(0))


def test_arms_must_be_different_assessments_with_different_items():
    with pytest.raises(ValueError, match="different assessments"):
        compare(baseline(10), {**corrected(0), "assessment_id": "synthetic-baseline"})
    with pytest.raises(ValueError, match="share items"):
        compare(baseline(10), {**baseline(10), "assessment_id": "synthetic-corrected"})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.pop("corrected"),
        lambda c: c.update(diagnostic={}),
        lambda c: c["baseline"].pop("retained_items"),
        lambda c: c["baseline"].update(planned_slots=200),
        lambda c: c["baseline"].update(retained_items=True),
        lambda c: c["baseline"].update(retained_items=-1),
        lambda c: c["baseline"].update(retained_items=50.0),
        lambda c: c["corrected"].update(initial_attempt_schema_pass_rate=1.01),
        lambda c: c["corrected"].update(initial_attempt_schema_pass_rate=-0.1),
        lambda c: c["corrected"].update(initial_attempt_schema_pass_rate="0.95"),
        lambda c: c["corrected"].update(initial_attempt_schema_pass_rate=None),
        lambda c: c["corrected"].update(initial_attempt_schema_pass_rate=True),
        lambda c: c["corrected"].update(initial_attempt_schema_pass_rate=float("nan")),
    ],
)
def test_malformed_course_checks_are_refused(mutate):
    course = copy.deepcopy(COURSE)
    mutate(course)
    with pytest.raises(ValueError, match="course_checks"):
        compare(baseline(11), corrected(2), course=course)


@pytest.mark.parametrize(
    ("path", "value", "unmet"),
    [
        (("overall_pass", "pass_rate_minimum"), 0.95, ["corrected_overall_pass_rate"]),
        (("per_dimension_pass_rate_minimum", "tips"), 1.0, ["corrected_tips_pass_rate"]),
        (
            ("dataset", "minimum_items_per_run"),
            51,
            ["baseline_retained_items", "corrected_retained_items"],
        ),
        (
            ("dataset", "minimum_human_labels_per_run"),
            21,
            ["baseline_human_labels", "corrected_human_labels"],
        ),
        (
            ("structural_validity_minimum",),
            0.96,
            [
                "baseline_initial_attempt_schema_pass_rate",
                "corrected_initial_attempt_schema_pass_rate",
            ],
        ),
        (
            ("baseline_overall_failure_minimum",),
            0.6,
            ["baseline_failure_minimum", "relative_failure_reduction_target"],
        ),
        (
            ("relative_failure_reduction", "conservative_target", "value"),
            0.85,
            ["relative_failure_reduction_target"],
        ),
    ],
)
def test_thresholds_are_read_from_the_rubric(path, value, unmet):
    # Baseline 11/20 and corrected 2/20 pass every check under the frozen rubric.
    result = compare(baseline(11), corrected(2), rubric=rubric_with(path, value))
    assert result["course_decision"]["unmet"] == unmet


def test_target_boundary_and_disclosure_text_come_from_the_rubric():
    rubric = rubric_with(("relative_failure_reduction", "conservative_target", "value"), 0.9)
    rubric["relative_failure_reduction"]["exact_boundary_rule"] = "Synthetic disclosure."
    result = compare(baseline(10), arm("corrected", {"tips": [0]}), rubric=rubric)
    reduction = result["relative_failure_reduction"]
    assert reduction["value"] == {"fraction": "9/10", "float": 0.9}
    assert reduction["meets_target"] is False
    assert reduction["boundary_disclosure"] == "Synthetic disclosure."


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("relative_failure_reduction", "conservative_target", "operator"), ">="),
        (("overall_pass", "rule"), "majority_of_dimensions_pass"),
        (("label_values",), [0, 1, 2]),
        (("per_dimension_pass_rate_minimum",), {"fidelity": 0.9}),
        (("structural_validity_minimum",), "0.95"),
        (("baseline_overall_failure_minimum",), True),
        (("dataset", "minimum_items_per_run"), 50.0),
    ],
)
def test_rubric_semantics_and_values_this_code_cannot_apply_are_refused(path, value):
    with pytest.raises(ValueError):
        compare(baseline(11), corrected(2), rubric=rubric_with(path, value))


def test_api_correctness_counts_reduction_intervals_and_fisher_p():
    result = compare(baseline(15), arm("corrected", {"api_correctness": range(8)}))
    api = result["api_correctness"]
    assert api["dimension"] == "api_correctness"
    assert (api["baseline"]["n"], api["baseline"]["failures"]) == (20, 15)
    assert (api["corrected"]["n"], api["corrected"]["failures"]) == (20, 8)
    assert api["baseline"]["failure_rate"] == {"fraction": "3/4", "float": 0.75}
    assert api["corrected"]["failure_rate"] == {"fraction": "2/5", "float": 0.4}
    assert api["relative_reduction"] == {
        "status": "evaluated",
        "value": {"fraction": "7/15", "float": 7 / 15},
    }
    interval = api["baseline"]["failure_rate_interval"]
    assert interval["method"] == "clopper_pearson"
    assert interval["confidence"] == {"fraction": "19/20", "float": 0.95}
    assert (round(interval["lower"], 4), round(interval["upper"], 4)) == (0.5090, 0.9134)
    fisher = api["fisher_exact"]
    assert fisher["alternative"] == "corrected_fails_less"
    assert fisher["significance"] == {"fraction": "1/20", "float": 0.05}
    assert fisher["p"]["float"] == pytest.approx(0.0268, abs=5e-5)
    assert Fraction(fisher["p"]["fraction"]) == fisher_exact_one_sided(15, 20, 8, 20)
    assert api["targeted_improvement"] is True

    api = compare(baseline(15), arm("corrected", {"api_correctness": range(9)}))["api_correctness"]
    assert api["fisher_exact"]["p"]["float"] == pytest.approx(0.0527, abs=5e-5)
    assert api["targeted_improvement"] is False


def test_api_reduction_is_undefined_without_baseline_api_failures():
    api = compare(arm("baseline", {"tips": range(10)}), corrected(0))["api_correctness"]
    assert api["baseline"]["failures"] == 0
    assert api["relative_reduction"] == {"status": "undefined", "value": None}
    assert api["fisher_exact"]["p"] == {"fraction": "1/1", "float": 1.0}
    assert api["targeted_improvement"] is False
    interval = api["baseline"]["failure_rate_interval"]
    assert interval["lower"] == 0.0
    assert round(interval["upper"], 4) == 0.1684


@pytest.mark.parametrize(
    ("b3", "largest_c3"),
    [(20, 15), (18, 12), (16, 10), (15, 8), (14, 7), (12, 5), (10, 4)],
)
def test_fisher_threshold_table_for_twenty_items_per_arm(b3, largest_c3):
    significant = [
        c3 for c3 in range(21) if fisher_exact_one_sided(b3, 20, c3, 20) < Fraction(1, 20)
    ]
    assert max(significant) == largest_c3
    for c3, improved in ((largest_c3, True), (largest_c3 + 1, False)):
        corr = arm("corrected", {"api_correctness": range(c3)})
        assert compare(baseline(b3), corr)["api_correctness"]["targeted_improvement"] is improved


def test_fisher_exact_reference_values():
    # Fisher's tea-tasting table [[3, 1], [1, 3]] has one-sided p = 17/70.
    assert fisher_exact_one_sided(3, 4, 1, 4) == Fraction(17, 70)
    assert float(fisher_exact_one_sided(15, 20, 8, 20)) == pytest.approx(0.0268, abs=5e-5)
    assert float(fisher_exact_one_sided(15, 20, 9, 20)) == pytest.approx(0.0527, abs=5e-5)
    assert fisher_exact_one_sided(0, 20, 0, 20) == 1


def test_targeted_improvement_needs_p_strictly_below_the_significance_level():
    # Three of three baseline items fail and none corrected: p is exactly 1/C(6, 3) = 1/20.
    assert fisher_exact_one_sided(3, 3, 0, 3) == Fraction(1, 20)
    api = compare(baseline(3, n=3), corrected(0, n=3))["api_correctness"]
    assert api["fisher_exact"]["p"] == {"fraction": "1/20", "float": 0.05}
    assert api["targeted_improvement"] is False


def test_unequal_arm_sizes_compare_api_failure_rates_not_counts():
    # 12 of 20 baseline and 12 of 40 corrected items fail: equal counts, half the rate.
    base = arm("baseline", {"api_correctness": range(12)})
    corr = arm("corrected", {"api_correctness": range(12)}, n=40)
    api = compare(base, corr)["api_correctness"]
    assert api["relative_reduction"]["value"] == {"fraction": "1/2", "float": 0.5}
    assert api["fisher_exact"]["p"]["float"] == pytest.approx(0.02553, abs=5e-6)
    assert api["targeted_improvement"] is True


def test_clopper_pearson_reference_values_and_edges():
    lower, upper = clopper_pearson(0, 20)
    assert lower == 0.0
    assert round(upper, 4) == 0.1684
    assert upper == pytest.approx(1 - 0.025 ** (1 / 20), abs=1e-12)
    lower, upper = clopper_pearson(15, 20)
    assert (round(lower, 4), round(upper, 4)) == (0.5090, 0.9134)
    lower, upper = clopper_pearson(20, 20)
    assert upper == 1.0
    assert lower == pytest.approx(0.025 ** (1 / 20), abs=1e-12)
    lower, upper = clopper_pearson(10, 20)
    assert lower == pytest.approx(1 - upper, abs=1e-12)


@pytest.mark.parametrize(
    "call",
    [
        lambda: clopper_pearson(21, 20),
        lambda: clopper_pearson(-1, 20),
        lambda: clopper_pearson(0, 0),
        lambda: clopper_pearson(True, 20),
        lambda: fisher_exact_one_sided(21, 20, 0, 20),
        lambda: fisher_exact_one_sided(1, 20, 1, 0),
        lambda: fisher_exact_one_sided(1.0, 20, 1, 20),
    ],
)
def test_statistics_refuse_impossible_counts(call):
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize(
    ("base", "corr", "status"),
    [
        (baseline(11), corrected(2), "complete"),
        (baseline(0), corrected(0), "complete"),
        (baseline(4), corrected(6), "complete"),
        (baseline(10), {**corrected(0), "labels": {}}, "incomplete"),
    ],
)
def test_output_is_json_with_n_over_d_fractions_beside_floats(base, corr, status):
    result = compare(base, corr)
    assert result["status"] == status
    assert json.loads(json.dumps(result, allow_nan=False)) == result
    exact = list(exact_values(result))
    assert len(exact) > 20 or status == "incomplete"
    for row in exact:
        assert re.fullmatch(r"-?\d+/[1-9]\d*", row["fraction"]), row
        assert float(Fraction(row["fraction"])) == row["float"]
