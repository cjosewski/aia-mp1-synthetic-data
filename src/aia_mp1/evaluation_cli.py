"""Assessment, human labeling, judge and calibration CLI surfaces."""

from pathlib import Path

from .assessment import create_assessment
from .calibration import calibration_report
from .evaluation_schemas import DIMENSIONS, Judgment
from .judge import JudgeConfig, judge_run, judge_status
from .labels import interactive_label, label_status, record_label
from .model_client import InstructorClient


def add_commands(commands):
    assessment = commands.add_parser(
        "assessment", help="freeze a diagnostic or assessed review queue"
    )
    assessment.add_argument("--run-id", required=True)
    assessment.add_argument(
        "--purpose", choices=("diagnostic", "baseline", "corrected"), default="diagnostic"
    )
    assessment.add_argument("--rubric", type=Path, default=Path("config/rubric.json"))
    assessment.add_argument("--label-count", type=int, default=5)
    assessment.add_argument("--seed", default="mp1-v1")
    label = commands.add_parser(
        "label", help="record authentic human decisions; resumes incomplete reviews"
    )
    label.add_argument("--reviewer", required=True)
    label.add_argument("--item-id")
    label.add_argument("--decisions", type=int, nargs=6, metavar="0_OR_1")
    label.add_argument("--notes", default="")
    label.add_argument("--supersedes")
    status = commands.add_parser("label-status", help="show review coverage and current label IDs")
    judge = commands.add_parser("judge", help="run an independently prompted local judge")
    judge.add_argument("--config", type=Path, required=True)
    judge.add_argument("--resume", action="store_true")
    judge_info = commands.add_parser("judge-status", help="validate and summarize judge evidence")
    calibration = commands.add_parser("calibrate", help="save an exact agreement/readiness report")
    calibration.add_argument("--report-id", required=True)
    for command in (assessment, label, status, judge, judge_info, calibration):
        command.add_argument("--assessment-id", required=True)
        command.add_argument(
            "--artifact-root", type=Path, default=Path("../artifacts/evidence/P1-03")
        )
    for command in (judge, judge_info, calibration):
        command.add_argument("--judge-run-id", required=True)


def run_command(args) -> tuple[dict, int]:
    root, assessment_id = args.artifact_root, args.assessment_id
    if args.command == "assessment":
        result = create_assessment(
            root,
            args.run_id,
            assessment_id,
            args.rubric,
            purpose=args.purpose,
            label_count=args.label_count,
            seed=args.seed,
        )
        return {
            k: result[k]
            for k in ("assessment_id", "purpose", "assessment_eligible", "selected_ids")
        }, 0
    if args.command == "label-status":
        return label_status(root, assessment_id), 0
    if args.command == "label":
        if args.item_id is not None or args.decisions is not None or args.supersedes is not None:
            if args.item_id is None or args.decisions is None:
                raise ValueError("explicit labeling requires --item-id and six --decisions")
            result = record_label(
                root,
                assessment_id,
                args.item_id,
                dict(zip(DIMENSIONS, args.decisions, strict=True)),
                args.reviewer,
                notes=args.notes,
                supersedes=args.supersedes,
            )
            return result, 0
        result = interactive_label(root, assessment_id, args.reviewer)
        return result, 0 if result["status"] == "complete" else 1
    if args.command == "judge":
        config = JudgeConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
        with InstructorClient(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key(),
            mode=config.mode,
            timeout_seconds=config.timeout_seconds,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            response_model=Judgment,
        ) as client:
            result = judge_run(
                root, assessment_id, args.judge_run_id, config, client, resume=args.resume
            )
        return result, 0 if result["status"] == "complete" else 1
    if args.command == "judge-status":
        return judge_status(root, assessment_id, args.judge_run_id), 0
    if args.command == "calibrate":
        result = calibration_report(root, assessment_id, args.judge_run_id, args.report_id)
        return result, 0 if result["status"] == "ready" else 1
    raise ValueError("unknown evaluation command")
