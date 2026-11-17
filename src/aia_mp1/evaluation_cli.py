"""Assessment, human labeling, judge and calibration CLI surfaces."""

from pathlib import Path

from .acceptance import COURSE_POLICY, POLICIES
from .assessment import create_assessment, create_cohort_assessment
from .calibration import calibration_report
from .evaluation_schemas import DIMENSIONS, Judgment
from .judge import JudgeConfig, judge_run, judge_status
from .labels import interactive_label, label_status, record_label
from .model_client import InstructorClient


def add_commands(commands):
    assessment = commands.add_parser(
        "assessment", help="freeze a diagnostic or assessed review queue"
    )
    source = assessment.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-id")
    source.add_argument("--cohort-id")
    assessment.add_argument("--purpose", choices=("diagnostic", "baseline", "corrected"))
    assessment.add_argument("--rubric", type=Path, default=Path("config/rubric.json"))
    assessment.add_argument("--label-count", type=int)
    assessment.add_argument("--seed", default="mp1-v1")
    label = commands.add_parser(
        "label", help="record authentic human decisions; resumes incomplete reviews"
    )
    label.add_argument("--reviewer", required=True)
    label.add_argument("--item-id")
    label.add_argument("--decisions", type=int, nargs=6, metavar="0_OR_1")
    label.add_argument("--notes", default="")
    label.add_argument("--supersedes")
    label.add_argument("--review-stage", choices=("blind", "post_review", "unknown"))
    label.add_argument("--consulted-report-id", action="append")
    reference = commands.add_parser(
        "freeze-human-reference", help="freeze declared blind human reviews"
    )
    reference.add_argument("--reviewer", required=True)
    reference.add_argument("--declare-blind", action="store_true")
    status = commands.add_parser("label-status", help="show review coverage and current label IDs")
    judge = commands.add_parser("judge", help="run an independently prompted local judge")
    judge.add_argument("--config", type=Path, required=True)
    judge.add_argument("--resume", action="store_true")
    judge_info = commands.add_parser("judge-status", help="validate and summarize judge evidence")
    calibration = commands.add_parser("calibrate", help="save an exact agreement/readiness report")
    calibration.add_argument("--report-id", required=True)
    calibration.add_argument("--acceptance-policy", choices=POLICIES, default=COURSE_POLICY)
    for command in (assessment, label, status, judge, judge_info, calibration, reference):
        command.add_argument("--assessment-id", required=True)
        command.add_argument(
            "--artifact-root", type=Path, default=Path("../artifacts/evidence/P1-03")
        )
    for command in (judge, judge_info, calibration):
        command.add_argument("--judge-run-id", required=True)


def run_command(args) -> tuple[dict, int]:
    root, assessment_id = args.artifact_root, args.assessment_id
    if args.command == "assessment":
        if args.cohort_id:
            if args.purpose is not None or args.label_count is not None:
                raise ValueError("cohort purpose and 20-item selection cannot be overridden")
            result = create_cohort_assessment(
                root, args.cohort_id, assessment_id, args.rubric, seed=args.seed
            )
            return {
                k: result[k]
                for k in ("assessment_id", "purpose", "assessment_eligible", "selected_ids")
            }, 0
        result = create_assessment(
            root,
            args.run_id,
            assessment_id,
            args.rubric,
            purpose=args.purpose or "diagnostic",
            label_count=args.label_count if args.label_count is not None else 5,
            seed=args.seed,
        )
        return {
            k: result[k]
            for k in ("assessment_id", "purpose", "assessment_eligible", "selected_ids")
        }, 0
    if args.command == "label-status":
        return label_status(root, assessment_id), 0
    if args.command == "freeze-human-reference":
        from .human_reference import freeze_reference

        reference = freeze_reference(
            root, assessment_id, args.reviewer, declare_blind=args.declare_blind
        )
        return {
            k: reference[k] for k in ("sha256", "selected_ids", "reviewer", "declared_blind")
        }, 0
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
                review_stage=args.review_stage,
                consulted_report_ids=args.consulted_report_id,
            )
            return result, 0
        if args.consulted_report_id:
            raise ValueError("consulted report IDs require explicit amendment mode")
        result = interactive_label(
            root, assessment_id, args.reviewer, review_stage=args.review_stage
        )
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
            reasoning_effort=config.reasoning_effort,
        ) as client:
            result = judge_run(
                root, assessment_id, args.judge_run_id, config, client, resume=args.resume
            )
        return result, 0 if result["status"] == "complete" else 1
    if args.command == "judge-status":
        return judge_status(root, assessment_id, args.judge_run_id), 0
    if args.command == "calibrate":
        result = calibration_report(
            root,
            assessment_id,
            args.judge_run_id,
            args.report_id,
            acceptance_policy=args.acceptance_policy,
        )
        return result, 0 if result["status"] == "ready" else 1
    raise ValueError("unknown evaluation command")
