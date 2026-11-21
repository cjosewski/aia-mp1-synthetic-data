"""Exact before/after statistics over two arms' frozen blind human labels (aec-rubric-v2).

Pure computation: no file or network I/O. Every rubric threshold is read from the rubric dict
and converted to an exact Fraction through its decimal string, so 0.8 is exactly 4/5.
"""

from fractions import Fraction
from math import comb

COMPARISON_SCHEMA = "aec-v2-human-comparison-1"
TARGETED_DIMENSION = "api_correctness"
# Design values from docs/AEC-V2-EVALUATION.md; the rubric defines no significance level.
SIGNIFICANCE = Fraction(1, 20)
CONFIDENCE = Fraction(19, 20)
BISECTION_STEPS = 60
ARM_FIELDS = {"assessment_id", "selected_ids", "labels", "categories"}
COURSE_FIELDS = {"retained_items", "initial_attempt_schema_pass_rate"}
# The checks a baseline too low to evaluate a relative reduction leaves unmet.
NOT_EVALUABLE = {"baseline_failure_minimum", "relative_failure_reduction_target"}


def compute_comparison(
    baseline: dict, corrected: dict, rubric: dict, *, course_checks: dict
) -> dict:
    """Course decision for an independent baseline/corrected pair of blind human reviews.

    Each arm is {assessment_id, selected_ids, labels: {item_id: decisions}, categories:
    {item_id: category}}. A dimension missing from an item's decisions, or a selected item
    missing from labels, is unresolved: any unresolved label gives status "incomplete" with
    unresolved counts and no figures.
    """
    dimensions = [dimension["id"] for dimension in rubric["dimensions"]]
    limits = _thresholds(rubric, dimensions)
    arms = {"baseline": baseline, "corrected": corrected}
    for name, arm in arms.items():
        _check_arm(name, arm, dimensions)
    if baseline["assessment_id"] == corrected["assessment_id"]:
        raise ValueError("baseline and corrected must be different assessments")
    if set(baseline["selected_ids"]) & set(corrected["selected_ids"]):
        raise ValueError("baseline and corrected selections share items")
    supplied = _check_course(course_checks)
    head = {"comparison_schema": COMPARISON_SCHEMA, "rubric_version": rubric["version"]}
    unresolved = {name: _unresolved(arm, dimensions) for name, arm in arms.items()}
    if any(row["unresolved_items"] for row in unresolved.values()):
        return head | {
            "status": "incomplete",
            "arms": unresolved,
            "course_decision": {"result": "incomplete"},
        }
    figures = {name: _figures(arm, dimensions) for name, arm in arms.items()}

    base_failure = figures["baseline"]["failure_rate"]
    corrected_failure = figures["corrected"]["failure_rate"]
    if base_failure == 0:
        status = "undefined"
    elif base_failure < limits["baseline_failure_minimum"]:
        status = "baseline_below_minimum"
    else:
        status = "evaluated"
    value = (base_failure - corrected_failure) / base_failure if status == "evaluated" else None
    target = limits["target"]
    reduction = {
        "status": status,
        "baseline_failure": base_failure,
        "corrected_failure": corrected_failure,
        "baseline_failure_minimum": limits["baseline_failure_minimum"],
        "target": {"operator": ">", "value": target},
        "value": value,
        "meets_target": value is not None and value > target,
        "at_or_above_0_8": value is not None and value >= target,
        "boundary_disclosure": limits["boundary_disclosure"] if value == target else None,
    }

    after = figures["corrected"]
    overall = _minimum(after["overall_pass_rate"], limits["overall_pass_rate_minimum"])
    per_dimension = {
        d: _minimum(after["dimensions"][d]["pass_rate"], limits["dimension_minimums"][d])
        for d in dimensions
    }
    minimums = {
        "overall_pass_rate": overall,
        "dimensions": per_dimension,
        "all_met": overall["met"] and all(row["met"] for row in per_dimension.values()),
    }

    api = {"dimension": TARGETED_DIMENSION}
    for name, row in figures.items():
        n = row["n"]
        failures = n - row["dimensions"][TARGETED_DIMENSION]["pass_count"]
        lower, upper = clopper_pearson(failures, n)
        api[name] = {
            "n": n,
            "failures": failures,
            "failure_rate": Fraction(failures, n),
            "failure_rate_interval": {
                "method": "clopper_pearson",
                "confidence": CONFIDENCE,
                "lower": lower,
                "upper": upper,
            },
        }
    before_api, after_api = api["baseline"], api["corrected"]
    p = fisher_exact_one_sided(
        before_api["failures"], before_api["n"], after_api["failures"], after_api["n"]
    )
    api_reduction = None
    if before_api["failures"]:
        before_rate = before_api["failure_rate"]
        api_reduction = (before_rate - after_api["failure_rate"]) / before_rate
    api |= {
        "relative_reduction": {
            "status": "undefined" if api_reduction is None else "evaluated",
            "value": api_reduction,
        },
        "fisher_exact": {
            "alternative": "corrected_fails_less",
            "p": p,
            "significance": SIGNIFICANCE,
        },
        "targeted_improvement": after_api["failure_rate"] < before_api["failure_rate"]
        and p < SIGNIFICANCE,
    }

    course = {
        name: {
            "retained_items": _minimum(supplied[name]["retained_items"], limits["items_minimum"]),
            "human_labels": _minimum(figures[name]["n"], limits["labels_minimum"]),
            "initial_attempt_schema_pass_rate": _minimum(
                supplied[name]["initial_attempt_schema_pass_rate"], limits["validity_minimum"]
            ),
        }
        for name in arms
    }
    checks = {f"{name}_{key}": row["met"] for name in arms for key, row in course[name].items()}
    checks["baseline_failure_minimum"] = base_failure >= limits["baseline_failure_minimum"]
    checks["relative_failure_reduction_target"] = reduction["meets_target"]
    checks["corrected_overall_pass_rate"] = overall["met"]
    checks |= {f"corrected_{d}_pass_rate": per_dimension[d]["met"] for d in dimensions}
    unmet = [name for name, met in checks.items() if not met]
    if not unmet:
        result = "pass"
    elif status != "evaluated" and set(unmet) <= NOT_EVALUABLE:
        result = "not_evaluable"
    else:
        result = "fail"
    return _jsonable(
        head
        | {
            "status": "complete",
            "arms": figures,
            "relative_failure_reduction": reduction,
            "corrected_minimums": minimums,
            "api_correctness": api,
            "course_checks": course,
            "course_decision": {"result": result, "checks": checks, "unmet": unmet},
        }
    )


def fisher_exact_one_sided(
    baseline_failures: int, baseline_n: int, corrected_failures: int, corrected_n: int
) -> Fraction:
    """One-sided Fisher exact p for "corrected fails less".

    With both margins fixed, the corrected arm's failure count is hypergeometric under the
    null; p is the exact probability of at most the observed corrected failures.
    """
    _check_count(baseline_failures, baseline_n)
    _check_count(corrected_failures, corrected_n)
    total = baseline_n + corrected_n
    failures = baseline_failures + corrected_failures
    tail = sum(
        comb(failures, k) * comb(total - failures, corrected_n - k)
        for k in range(corrected_failures + 1)
    )
    return Fraction(tail, comb(total, corrected_n))


def clopper_pearson(count: int, n: int) -> tuple[float, float]:
    """Exact two-sided 95% Clopper-Pearson interval for the proportion count/n.

    Each bound is bisected on exact binomial tail sums to a 2**-60 bracket, whose outer end
    is returned; the bound is exactly 0 when count is 0 and exactly 1 when count is n.
    """
    _check_count(count, n)
    tail = (1 - CONFIDENCE) / 2
    lower, upper = 0.0, 1.0
    if count:
        # P(X >= count) rises with p; below the bound it is under the tail.
        lower = float(_bisect(lambda p: _binomial(n, p, range(count, n + 1)) < tail)[0])
    if count < n:
        # P(X <= count) falls with p; below the bound it is over the tail.
        upper = float(_bisect(lambda p: _binomial(n, p, range(count + 1)) > tail)[1])
    return lower, upper


def _binomial(n: int, p: Fraction, counts: range) -> Fraction:
    return sum((comb(n, k) * p**k * (1 - p) ** (n - k) for k in counts), Fraction(0))


def _bisect(below) -> tuple[Fraction, Fraction]:
    """Bracket the point in (0, 1) where the monotone predicate `below` turns false."""
    low, high = Fraction(0), Fraction(1)
    for _ in range(BISECTION_STEPS):
        middle = (low + high) / 2
        if below(middle):
            low = middle
        else:
            high = middle
    return low, high


def _check_count(count, n) -> None:
    if type(count) is not int or type(n) is not int or n < 1 or not 0 <= count <= n:
        raise ValueError(f"expected integers 0 <= count <= n and n >= 1, not {count!r} of {n!r}")


def _exact(value) -> Fraction:
    if type(value) not in (int, float):
        raise ValueError(f"expected a number, not {value!r}")
    return Fraction(str(value))


def _count(value) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"expected a non-negative integer, not {value!r}")
    return value


def _thresholds(rubric: dict, dimensions: list[str]) -> dict:
    reduction = rubric["relative_failure_reduction"]
    if reduction["conservative_target"]["operator"] != ">":
        raise ValueError("only a strict '>' relative failure reduction target is implemented")
    if rubric["overall_pass"]["rule"] != "all_eight_dimensions_pass":
        raise ValueError("only the all_eight_dimensions_pass overall rule is implemented")
    if rubric["label_values"] != [0, 1]:
        raise ValueError("only binary 0/1 labels are implemented")
    minimums = rubric["per_dimension_pass_rate_minimum"]
    if set(minimums) != set(dimensions) or TARGETED_DIMENSION not in dimensions:
        raise ValueError("per-dimension minimums must cover exactly the rubric dimensions")
    dataset = rubric["dataset"]
    return {
        "dimension_minimums": {d: _exact(minimums[d]) for d in dimensions},
        "overall_pass_rate_minimum": _exact(rubric["overall_pass"]["pass_rate_minimum"]),
        "baseline_failure_minimum": _exact(rubric["baseline_overall_failure_minimum"]),
        "target": _exact(reduction["conservative_target"]["value"]),
        "boundary_disclosure": reduction["exact_boundary_rule"],
        "items_minimum": _count(dataset["minimum_items_per_run"]),
        "labels_minimum": _count(dataset["minimum_human_labels_per_run"]),
        "validity_minimum": _exact(rubric["structural_validity_minimum"]),
    }


def _check_arm(name: str, arm, dimensions: list[str]) -> None:
    if not isinstance(arm, dict) or set(arm) != ARM_FIELDS:
        raise ValueError(f"{name} arm needs exactly the fields {sorted(ARM_FIELDS)}")
    if type(arm["assessment_id"]) is not str or not arm["assessment_id"]:
        raise ValueError(f"{name} assessment_id must be a non-empty string")
    selected = arm["selected_ids"]
    if (
        not isinstance(selected, (list, tuple))
        or not selected
        or not all(type(item) is str and item for item in selected)
    ):
        raise ValueError(f"{name} selected_ids must be a non-empty list of item IDs")
    if len(set(selected)) != len(selected):
        raise ValueError(f"{name} selected_ids contain duplicates")
    labels, categories = arm["labels"], arm["categories"]
    if not isinstance(labels, dict) or not isinstance(categories, dict):
        raise ValueError(f"{name} labels and categories must be mappings by item ID")
    if extra := set(labels) - set(selected):
        raise ValueError(f"{name} labels include unselected items: {sorted(extra, key=str)}")
    if set(categories) != set(selected) or not all(
        type(category) is str and category for category in categories.values()
    ):
        raise ValueError(f"{name} categories must name a category for exactly the selected items")
    for item, decisions in labels.items():
        if not isinstance(decisions, dict):
            raise ValueError(f"{name} decisions for {item} must be a mapping")
        if unknown := set(decisions) - set(dimensions):
            raise ValueError(f"{name} {item} has unknown dimensions: {sorted(unknown, key=str)}")
        for dimension, value in decisions.items():
            if type(value) is not int or value not in (0, 1):
                raise ValueError(f"{name} {item} {dimension} must be 0 or 1, not {value!r}")


def _check_course(course_checks) -> dict:
    if not isinstance(course_checks, dict) or set(course_checks) != {"baseline", "corrected"}:
        raise ValueError("course_checks needs exactly baseline and corrected")
    supplied = {}
    for name, row in course_checks.items():
        if not isinstance(row, dict) or set(row) != COURSE_FIELDS:
            raise ValueError(f"course_checks.{name} needs exactly {sorted(COURSE_FIELDS)}")
        retained, rate = row["retained_items"], row["initial_attempt_schema_pass_rate"]
        if type(retained) is not int or retained < 0:
            raise ValueError(f"course_checks.{name}.retained_items must be a non-negative integer")
        if type(rate) not in (int, float) or not 0 <= rate <= 1:
            raise ValueError(
                f"course_checks.{name}.initial_attempt_schema_pass_rate must be in [0, 1]"
            )
        supplied[name] = {
            "retained_items": retained,
            "initial_attempt_schema_pass_rate": _exact(rate),
        }
    return supplied


def _unresolved(arm: dict, dimensions: list[str]) -> dict:
    decisions = [arm["labels"].get(item, {}) for item in arm["selected_ids"]]
    return {
        "assessment_id": arm["assessment_id"],
        "selected_items": len(decisions),
        "unresolved_items": sum(any(d not in row for d in dimensions) for row in decisions),
        "unresolved_by_dimension": {d: sum(d not in row for row in decisions) for d in dimensions},
    }


def _figures(arm: dict, dimensions: list[str]) -> dict:
    selected, labels = arm["selected_ids"], arm["labels"]
    n = len(selected)
    failing = {item for item in selected if any(labels[item][d] == 0 for d in dimensions)}
    passes = {d: sum(labels[item][d] for item in selected) for d in dimensions}
    categories = {}
    for item in selected:
        row = categories.setdefault(arm["categories"][item], {"n": 0, "failing_items": 0})
        row["n"] += 1
        row["failing_items"] += int(item in failing)
    return {
        "assessment_id": arm["assessment_id"],
        "n": n,
        "failing_items": len(failing),
        "failure_rate": Fraction(len(failing), n),
        "overall_pass_rate": Fraction(n - len(failing), n),
        "dimensions": {
            d: {"pass_count": passes[d], "pass_rate": Fraction(passes[d], n)} for d in dimensions
        },
        "categories": dict(sorted(categories.items())),
    }


def _minimum(observed, minimum) -> dict:
    return {"observed": observed, "minimum": minimum, "met": observed >= minimum}


def _jsonable(value):
    """Write each exact Fraction as an "n/d" string with its float beside it."""
    if isinstance(value, Fraction):
        return {"fraction": f"{value.numerator}/{value.denominator}", "float": float(value)}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value
