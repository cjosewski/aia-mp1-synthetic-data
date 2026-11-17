"""Versioned offline evidence bases and claim lineage; no inference or scoring.

The frozen v1 parent supplies exact text coverage. Child claims may overlap within
that parent, but cannot omit text or required dimensions. Classification, atomicity
and authored reasoning remain semantic audit responsibilities, never model choices.
"""

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from .evidence_judge import StrictModel
from .factcheck import SHA
from .recovery_checks import (
    Check,
    CheckID,
    CheckPlan,
    Observations,
    Span,
    check_span,
    validate_plan,
)
from .schemas import NonBlank
from .tracing import digest

EvidenceKind = Literal[
    "api_contract", "task_comparison", "mathematical_derivation", "workflow_reasoning"
]


class ReasoningNote(StrictModel):
    note_id: Annotated[str, Field(pattern=r"^N[0-9]{4}$")]
    kind: Literal["mathematical_derivation", "workflow_reasoning"]
    author: NonBlank
    origin: Literal["assistant_authored", "owner_authored"]
    created_at: NonBlank
    premises: Annotated[list[Span], Field(min_length=1)]
    reasoning: NonBlank
    limitations: NonBlank


class EvidenceCheck(Check):
    parent_check_id: CheckID
    evidence_kind: EvidenceKind
    basis_rationale: NonBlank


class EvidencePlan(StrictModel):
    protocol: Literal["recovery-evidence-v2"]
    input_sha256: SHA
    rubric_sha256: SHA
    parent_plan_sha256: SHA
    parent_plan: CheckPlan
    reasoning_notes: list[ReasoningNote]
    checks: Annotated[list[EvidenceCheck], Field(min_length=1)]


def fingerprint(value: StrictModel) -> str:
    return digest(value.model_dump(mode="json"))


def parse_plan(value: dict) -> CheckPlan | EvidencePlan:
    if isinstance(value, dict) and value.get("protocol") == "recovery-evidence-v2":
        return EvidencePlan.model_validate(value)
    return CheckPlan.model_validate(value)


def validate_evidence_plan(
    plan: EvidencePlan, content: dict, rubric: dict, source_root: Path
) -> dict:
    parent = plan.parent_plan
    if (
        plan.parent_plan_sha256 != fingerprint(parent)
        or plan.input_sha256 != parent.input_sha256
        or plan.rubric_sha256 != parent.rubric_sha256
    ):
        raise ValueError("evidence plan parent lineage changed")
    # Reuses the unchanged v1 coverage/source/permission validator. Do not mutate
    # the returned content catalog when introducing a different authority class.
    catalog = dict(validate_plan(parent, content, rubric, source_root))
    if [n.note_id for n in plan.reasoning_notes] != [
        f"N{i:04d}" for i in range(1, len(plan.reasoning_notes) + 1)
    ]:
        raise ValueError("reasoning note IDs must be ordered and unique")
    for note in plan.reasoning_notes:
        seen = set()
        for premise in note.premises:
            check_span(premise, content["passage_catalog"])
            role = content["passage_catalog"][premise.passage_id]["authority"]
            if role not in {"candidate", "task", "primary_excerpt"}:
                raise ValueError("reasoning premises must be explicit givens or primary evidence")
            key = (premise.passage_id, premise.start, premise.end)
            if key in seen:
                raise ValueError("duplicate reasoning premise")
            seen.add(key)
        catalog[f"E.{note.note_id}"] = {
            "text": note.reasoning,
            "authority": note.kind,
            "version": fingerprint(note),
        }
    if [c.check_id for c in plan.checks] != [f"K{i:04d}" for i in range(1, len(plan.checks) + 1)]:
        raise ValueError("child check IDs must be ordered and unique")
    parents = {c.check_id: c for c in parent.checks}
    covered = {key: set() for key in parents}
    signatures = set()
    used_notes = set()
    for check in plan.checks:
        if check.parent_check_id not in parents:
            raise ValueError("unknown parent check")
        original = parents[check.parent_check_id]
        subject = check.subject
        check_span(subject, catalog)
        if (
            subject.passage_id != original.subject.passage_id
            or subject.start < original.subject.start
            or subject.end > original.subject.end
        ):
            raise ValueError("child subject must stay within its frozen parent")
        if (
            check.kind != original.kind
            or len(set(check.dimensions)) != len(check.dimensions)
            or not set(original.dimensions) <= set(check.dimensions)
            or (check.evidence_kind == "api_contract" and "D3" not in check.dimensions)
        ):
            raise ValueError("evidence classification cannot remove required dimension review")
        signature = (check.parent_check_id, fingerprint(subject), check.question.strip())
        if signature in signatures:
            raise ValueError("duplicate child question and subject")
        signatures.add(signature)
        covered[check.parent_check_id].update(range(subject.start, subject.end))
        bindings = [s.passage_id for s in check.sources]
        if len(set(bindings)) != len(bindings):
            raise ValueError("duplicate bound evidence")
        authority = {
            "api_contract": "primary_excerpt",
            "task_comparison": "task",
            "mathematical_derivation": "mathematical_derivation",
            "workflow_reasoning": "workflow_reasoning",
        }[check.evidence_kind]
        for source in check.sources:
            row = catalog.get(source.passage_id)
            if row is None or row["authority"] != authority:
                raise ValueError("evidence binding has the wrong authority for this claim")
            if authority == "primary_excerpt":
                index = int(source.passage_id.removeprefix("R.fact."))
                version = content["primary_excerpts"][index]["version"]
            elif authority == "task":
                version = "frozen-task"
            else:
                version = row["version"]
                used_notes.add(source.passage_id)
            if source.version != version:
                raise ValueError("bound evidence version changed")
    for key, original in parents.items():
        positions = {
            original.subject.start + i
            for i, char in enumerate(original.subject.quote)
            if not char.isspace()
        }
        if not positions <= covered[key]:
            raise ValueError("child checks leave parent text uncovered")
    if used_notes != {f"E.{n.note_id}" for n in plan.reasoning_notes}:
        raise ValueError("unbound reasoning notes are not allowed in the model context")
    return catalog


def inspect_evidence(
    plan: EvidencePlan,
    content: dict,
    rubric: dict,
    source_root: Path,
    response: Observations | None = None,
) -> dict:
    catalog = validate_evidence_plan(plan, content, rubric, source_root)
    gaps = [c.check_id for c in plan.checks if not c.sources]
    result = {
        "protocol": plan.protocol,
        "plan_sha256": fingerprint(plan),
        "parent_plan_sha256": plan.parent_plan_sha256,
        "parent_checks": len(plan.parent_plan.checks),
        "checks": len(plan.checks),
        "evidence_kinds": dict(Counter(c.evidence_kind for c in plan.checks)),
        "source_gaps": gaps,
        "response_checked": response is not None,
        "unresolved": [],
        "contradicted": [],
        "structural_status": "source_gaps" if gaps else "awaiting_observations",
        "semantic_audit": "required",
        "evidence_kind_audit": "required",
        "authored_reasoning_audit": "required",
        "calibration_eligible": False,
        "model_calls": 0,
    }
    if response is None:
        return result
    if response.plan_sha256 != fingerprint(plan):
        raise ValueError("observations belong to a different evidence plan")
    rows = {row.check_id: row for row in response.observations}
    if len(rows) != len(response.observations) or set(rows) != {c.check_id for c in plan.checks}:
        raise ValueError("observations must cover every child check exactly once")
    for check in plan.checks:
        row = rows[check.check_id]
        allowed = {s.passage_id for s in check.sources}
        seen = set()
        for citation in row.citations:
            check_span(citation, catalog)
            if citation.passage_id not in allowed:
                raise ValueError("observation cites outside its frozen evidence bindings")
            key = (citation.passage_id, citation.start, citation.end)
            if key in seen:
                raise ValueError("duplicate evidence citation")
            seen.add(key)
        if row.status != "insufficient" and not row.citations:
            raise ValueError("conclusion requires exact bound evidence")
        if row.status == "insufficient":
            result["unresolved"].append(row.check_id)
        elif row.status == "contradicted":
            result["contradicted"].append(row.check_id)
    result["structural_status"] = (
        "unresolved" if result["unresolved"] else "awaiting_semantic_audit"
    )
    return result


def evidence_request(plan: EvidencePlan, content: dict, rubric: dict, source_root: Path) -> dict:
    """Validated text view for later transport; building it never authorizes dispatch."""
    validate_evidence_plan(plan, content, rubric, source_root)
    return deepcopy(
        {
            "protocol": plan.protocol,
            "plan_sha256": fingerprint(plan),
            "untrusted_item": content["untrusted_item"],
            "untrusted_reference_context": content["untrusted_reference_context"],
            "checks": [c.model_dump(mode="json") for c in plan.checks],
            "primary_excerpts": [
                {"passage_id": f"R.fact.{i}", "version": r["version"], "text": r["text"]}
                for i, r in enumerate(content["primary_excerpts"])
            ],
            "reasoning_notes": [
                {
                    "passage_id": f"E.{n.note_id}",
                    "version": fingerprint(n),
                    **n.model_dump(mode="json"),
                }
                for n in plan.reasoning_notes
            ],
        }
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "rubric", "sources", "plan"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--observations", type=Path)
    args = parser.parse_args(argv)
    try:

        def load(path):
            return json.loads(path.read_text(encoding="utf-8"))

        result = inspect_evidence(
            EvidencePlan.model_validate(load(args.plan)),
            load(args.input),
            load(args.rubric),
            args.sources,
            Observations.model_validate(load(args.observations)) if args.observations else None,
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(
            json.dumps({"error": "offline evidence validation failed", "type": type(exc).__name__})
        )
        return 2
    print(json.dumps(result, indent=2))
    return 1 if result["source_gaps"] or result["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
