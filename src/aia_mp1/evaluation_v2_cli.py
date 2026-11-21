"""Offline aec-rubric-v2 evaluation commands; an expected failure exits 2 with one error line."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .assessment_v2 import create_assessment_v2
from .comparison_v2 import compare_assessments, comparison_path
from .labels_v2 import interactive_label_v2, label_status_v2, record_label_v2
from .reference_v2 import freeze_reference_v2
from .review_packet_v2 import import_packet_answers, prepare_masked_packet
from .rubric_v2 import DIMENSIONS_V2


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m aia_mp1.evaluation_v2_cli", description=__doc__
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-assessment", help="freeze a v2 selection from a cohort")
    create.add_argument("--cohort-id", required=True)
    create.add_argument("--assessment-id", required=True)
    create.add_argument(
        "--exclude-reviewed-in",
        action="append",
        default=[],
        metavar="ASSESSMENT_ID",
        help="earlier assessment whose labeled items are not eligible; repeatable",
    )
    create.add_argument(
        "--declare-no-prior-reviews",
        action="store_true",
        help="declare that no earlier review covers this cohort (otherwise list them)",
    )
    create.add_argument("--seed", default="mp1-v1")
    status = commands.add_parser("status", help="show label coverage of a v2 assessment")
    status.add_argument("--assessment-id", required=True)
    label = commands.add_parser("label", help="record authentic human decisions")
    label.add_argument("--assessment-id", required=True)
    label.add_argument("--reviewer", required=True)
    label.add_argument("--review-stage", choices=("blind", "post_review", "unknown"))
    label.add_argument("--item-id", help="explicit mode, for example an amendment")
    label.add_argument(
        "--decisions", type=int, nargs=8, metavar="0_OR_1", help=" ".join(DIMENSIONS_V2)
    )
    label.add_argument("--notes", default="")
    label.add_argument("--supersedes")
    label.add_argument("--consulted-report-id", action="append")
    packet = commands.add_parser("prepare-packet", help="write one masked two-arm packet")
    packet.add_argument("--packet-id", required=True)
    packet.add_argument(
        "--assessment-id",
        action="append",
        required=True,
        help="give twice: the baseline and the corrected assessment",
    )
    packet.add_argument("--task-pack", type=Path, required=True)
    packet.add_argument("--output", type=Path, required=True)
    packet.add_argument("--seed", default="mp1-v1")
    answers = commands.add_parser("import-answers", help="import a complete answer sheet")
    answers.add_argument("--packet-id", required=True)
    answers.add_argument("--answers", type=Path, required=True)
    answers.add_argument("--reviewer", required=True)
    freeze = commands.add_parser("freeze-reference", help="freeze declared blind labels")
    freeze.add_argument("--assessment-id", required=True)
    freeze.add_argument("--reviewer", required=True)
    freeze.add_argument(
        "--declare-blind", action="store_true", help="required: no judge output was consulted"
    )
    compare = commands.add_parser("compare", help="compare two frozen blind references")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--corrected", required=True)
    compare.add_argument("--comparison-id", required=True)
    compare.add_argument(
        "--declare",
        action="append",
        default=[],
        metavar="FIELD=REASON",
        help="a generator identity difference and its reason; repeatable",
    )
    for command in commands.choices.values():
        command.add_argument(
            "--artifact-root", type=Path, default=Path("../artifacts/evidence/P1-03")
        )
    return parser


def run(args) -> tuple[dict, int]:
    root = args.artifact_root
    if args.command == "create-assessment":
        manifest = create_assessment_v2(
            root,
            args.cohort_id,
            args.assessment_id,
            exclude_reviewed_in=args.exclude_reviewed_in,
            declare_no_prior_reviews=args.declare_no_prior_reviews,
            seed=args.seed,
        )
        eligibility = manifest["eligibility"]
        return {
            "assessment_id": manifest["assessment_id"],
            "purpose": manifest["purpose"],
            "prior_reviews": eligibility["prior_reviews"],
            "cohort_id": manifest["cohort_id"],
            "excluded": len(eligibility["excluded_ids"]),
            "eligible": len(eligibility["eligible_ids"]),
            "selected_ids": manifest["selected_ids"],
            "manifest_sha256": manifest["manifest_sha256"],
        }, 0
    if args.command == "status":
        return label_status_v2(root, args.assessment_id), 0
    if args.command == "label":
        if args.item_id is not None or args.decisions is not None or args.supersedes is not None:
            if args.item_id is None or args.decisions is None:
                raise ValueError("explicit labeling requires --item-id and eight --decisions")
            label = record_label_v2(
                root,
                args.assessment_id,
                args.item_id,
                dict(zip(DIMENSIONS_V2, args.decisions, strict=True)),
                args.reviewer,
                notes=args.notes,
                supersedes=args.supersedes,
                review_stage=args.review_stage,
                consulted_report_ids=args.consulted_report_id,
            )
            return label, 0
        if args.notes or args.consulted_report_id:
            raise ValueError("--notes and --consulted-report-id apply to explicit labels only")
        status = interactive_label_v2(
            root, args.assessment_id, args.reviewer, review_stage=args.review_stage
        )
        # Item IDs embed run IDs, so the reviewer's session ends without listing them.
        shown = {k: status[k] for k in ("assessment_id", "selected", "completed", "status")}
        return shown, 0 if status["status"] == "complete" else 1
    if args.command == "prepare-packet":
        packet = prepare_masked_packet(
            root, args.packet_id, args.assessment_id, args.task_pack, args.output, seed=args.seed
        )
        return {
            "packet_id": packet["packet_id"],
            "items": len(packet["items"]),
            "output": str(args.output),
            "packet_sha256": packet["sha256"],
        }, 0
    if args.command == "import-answers":
        result = import_packet_answers(root, args.packet_id, args.answers, args.reviewer)
        return {
            "packet_id": result["packet_id"],
            "labels": len(result["label_ids"]),
            "answers_sha256": result["answers_sha256"],
            "import_sha256": result["sha256"],
        }, 0
    if args.command == "freeze-reference":
        reference = freeze_reference_v2(
            root, args.assessment_id, args.reviewer, declare_blind=args.declare_blind
        )
        keys = ("assessment_id", "sha256", "reviewer", "declared_blind", "packet_ids")
        return {key: reference[key] for key in keys}, 0
    declared = {}
    for value in args.declare:
        field, separator, reason = value.partition("=")
        if not separator or not field.strip() or field.strip() in declared:
            raise ValueError("declare each difference once, as FIELD=REASON")
        declared[field.strip()] = reason
    document = compare_assessments(
        root, args.baseline, args.corrected, declared, args.comparison_id
    )
    return {
        "comparison_id": document["comparison_id"],
        "output": str(comparison_path(root, args.comparison_id)),
        "sha256": document["sha256"],
        "status": document["comparison"]["status"],
        "course_decision": document["comparison"]["course_decision"],
    }, 0


def _message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(map(str, error['loc'])) or 'value'}: {error['msg']}"
            for error in exc.errors()
        )
    if isinstance(exc, KeyError):
        return f"missing field {exc}"
    return " ".join(str(exc).split())


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        result, code = run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {_message(exc)}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
