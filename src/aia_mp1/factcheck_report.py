"""Paired development reporting; authentic reference ratings enter only here."""

from .evaluation_schemas import DIMENSIONS, Decisions
from .factcheck_stages import Ledger, canonical
from .tracing import digest


def build_report(ledger: Ledger, references: dict[str, dict]) -> dict:
    experiment, state = ledger.read()
    selected = [case.item_id for case in experiment.cases]
    if not isinstance(references, dict) or set(references) != set(selected):
        raise ValueError("report reference must cover exactly the selected cases")
    truth = {key: Decisions.model_validate(value).model_dump() for key, value in references.items()}
    if digest(references) != experiment.reference_sha256:
        raise ValueError("ratings differ from the reference hash frozen before requests")
    arms = {}
    decisions = {}
    for arm, stage in (("control", "control"), ("treatment", "score")):
        outcomes = {}
        for case in experiment.cases:
            rows = [
                r for r in state["finishes"] if r["item_id"] == case.item_id and r["stage"] == stage
            ]
            accepted = next((r for r in rows if r["result"]["canonical"] is not None), None)
            if accepted:
                outcomes[case.item_id] = canonical(accepted).decisions()
        decisions[arm] = outcomes
        metrics = {}
        for dimension in DIMENSIONS:
            compared = len(outcomes)
            matches = sum(
                scores[dimension] == truth[key][dimension] for key, scores in outcomes.items()
            )
            false_approvals = sum(
                scores[dimension] == 1 and truth[key][dimension] == 0
                for key, scores in outcomes.items()
            )
            false_rejections = sum(
                scores[dimension] == 0 and truth[key][dimension] == 1
                for key, scores in outcomes.items()
            )
            metrics[dimension] = {
                "matches": matches,
                "compared": compared,
                "agreement": matches / compared if compared else None,
                "false_approvals": false_approvals,
                "false_rejections": false_rejections,
            }
        arms[arm] = {
            "resolved": len(outcomes),
            "selected": len(selected),
            "unresolved": len(selected) - len(outcomes),
            "dimensions": metrics,
            "total_matches": sum(m["matches"] for m in metrics.values()),
            "compared_decisions": len(outcomes) * 6,
        }
    paired_ids = [key for key in selected if all(key in decisions[arm] for arm in arms)]
    paired = []
    for key in paired_ids:
        for dimension in DIMENSIONS:
            before, after = (
                decisions[arm][key][dimension] == truth[key][dimension] for arm in arms
            )
            if before != after:
                paired.append(
                    {
                        "item_id": key,
                        "dimension": dimension,
                        "change": "gain" if after else "regression",
                    }
                )
    stages = {}
    for stage in ("control", "facts", "score"):
        starts = [r for r in state["starts"] if r["stage"] == stage]
        finishes = [r for r in state["finishes"] if r["stage"] == stage]
        accepted = [r for r in finishes if r["result"]["status"] != "failed"]
        first_ids = {
            next(r["attempt_id"] for r in starts if r["item_id"] == key)
            for key in {r["item_id"] for r in starts}
        }
        stage_rows = []
        for case in experiment.cases:
            rows = [r for r in finishes if r["item_id"] == case.item_id]
            started = [r for r in starts if r["item_id"] == case.item_id]
            success = next((r for r in rows if r["result"]["status"] != "failed"), None)
            status = (
                success["result"]["status"]
                if success
                else "unknown"
                if len(started) > len(rows)
                else "failed"
                if rows
                else "not_attempted"
            )
            fact_failures = [
                r
                for r in state["finishes"]
                if r["item_id"] == case.item_id
                and r["stage"] == "facts"
                and r["result"]["status"] == "failed"
            ]
            if stage == "score" and not started and len(fact_failures) == 2:
                status = "skipped_dependency"
            stage_rows.append(
                {
                    "item_id": case.item_id,
                    "category": case.category,
                    "status": status,
                    "starts": len(started),
                }
            )
        stages[stage] = {
            "selected": len(selected),
            "starts": len(starts),
            "finished": len(finishes),
            "unknown": len(starts) - len(finishes),
            "structurally_accepted": len(accepted),
            "first_attempt_accepted": sum(r["attempt_id"] in first_ids for r in accepted),
            "retry_recovered": sum(r["attempt_id"] not in first_ids for r in accepted),
            "schema_valid": sum(r["result"]["schema_valid"] for r in finishes),
            "initial_attempts": len(first_ids),
            "first_attempt_schema_valid": sum(
                r["result"]["schema_valid"] for r in finishes if r["attempt_id"] in first_ids
            ),
            "unresolved_responses": sum(r["result"]["status"] == "unresolved" for r in finishes),
            "failures": len(finishes) - len(accepted),
            "elapsed_seconds": sum(r["completion"]["elapsed_seconds"] for r in finishes),
            "cases": stage_rows,
        }
    findings = [
        f
        for r in state["finishes"]
        if r["stage"] == "facts" and r["result"]["status"] == "accepted"
        for f in r["result"]["parsed"]["findings"]
    ]
    tokens, token_observations = 0, 0
    for row in state["finishes"]:
        raw = row["completion"]["raw_response"]
        usage = raw.get("usage") if isinstance(raw, dict) else None
        value = usage.get("completion_tokens") if isinstance(usage, dict) else None
        if type(value) is int and value >= 0:
            tokens += value
            token_observations += 1
    control, treatment = (arms[key] for key in ("control", "treatment"))
    numeric_gate = (
        len(paired_ids) == 5
        and treatment["total_matches"] > control["total_matches"]
        and all(
            treatment["dimensions"][d]["matches"] >= max(4, control["dimensions"][d]["matches"])
            for d in DIMENSIONS
        )
        and all(treatment["dimensions"][d]["false_approvals"] == 0 for d in ("D2", "D3"))
        and sum(treatment["dimensions"][d]["false_approvals"] for d in DIMENSIONS)
        <= sum(control["dimensions"][d]["false_approvals"] for d in DIMENSIONS)
    )
    return {
        "protocol": experiment.protocol,
        "purpose": "known-case development only",
        "ledger_head_sha256": state["head"],
        "reference_sha256": digest(references),
        "selected": selected,
        "starts": len(state["starts"]),
        "cumulative_starts": experiment.prior_starts + len(state["starts"]),
        "request_ceiling": experiment.max_starts,
        "unknown": state["pending"]["attempt_id"] if state["pending"] else None,
        "stop_reason": (
            state["halt"]
            or (
                "unknown_outcome"
                if state["pending"]
                else "consecutive_failures"
                if state["failures"] >= 2
                else "budget"
                if len(state["starts"]) >= experiment.max_starts
                else "complete"
                if ledger.next_stage(experiment, state) is None
                else "incomplete"
            )
        ),
        "stages": stages,
        "arms": arms,
        "fact_status_counts": {
            s: sum(f["status"] == s for f in findings)
            for s in ("supported", "contradicted", "insufficient")
        },
        "source_adequacy": "requires semantic audit; status counts are model assertions",
        "paired_item_ids": paired_ids,
        "paired_changes": paired,
        "paired_gains": sum(p["change"] == "gain" for p in paired),
        "paired_regressions": sum(p["change"] == "regression" for p in paired),
        "completion_tokens": tokens,
        "token_observations": token_observations,
        "token_missing": len(state["finishes"]) - token_observations,
        "numeric_advancement_gate": numeric_gate,
        "advancement": "semantic_audit_required" if numeric_gate else "not_demonstrated",
        "qualified": False,
    }
