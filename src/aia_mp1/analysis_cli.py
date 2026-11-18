"""Offline analysis interface; pending is an expected measured state, exit 1."""

import argparse
import json
import sys
from pathlib import Path

from .acceptance import COURSE_POLICY, POLICIES
from .analysis import load_analysis, output_directory, write_analysis
from .analysis_export import export_local, render_charts
from .schemas import DOMAIN


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("report", "verify", "charts", "export"):
        p = sub.add_parser(command)
        p.add_argument("--artifact-root", type=Path, default=Path("../artifacts/evidence/P1-03"))
        p.add_argument("--report-id", required=True)
        if command == "report":
            p.add_argument("--acceptance-policy", choices=POLICIES, default=COURSE_POLICY)
            p.add_argument("--baseline", required=True, help="baseline assessment ID")
            p.add_argument("--baseline-judge")
            p.add_argument("--corrected", help="corrected assessment ID")
            p.add_argument("--corrected-judge")
            p.add_argument("--correction", default="", help="declared generator prompt change")
        if command == "export":
            p.add_argument("--export-id", required=True)
            p.add_argument("--no-charts", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            result = write_analysis(
                args.artifact_root,
                args.report_id,
                args.baseline,
                baseline_judge=args.baseline_judge,
                corrected_id=args.corrected,
                corrected_judge=args.corrected_judge,
                correction=args.correction,
                acceptance_policy=args.acceptance_policy,
            )
        else:
            result = load_analysis(args.artifact_root, args.report_id)
            if args.command == "charts":
                render_charts(
                    result,
                    output_directory(args.artifact_root, args.report_id)
                    / ("visualizations" if DOMAIN in {"home-diy", "aec-course"} else "charts"),
                )
            elif args.command == "export":
                export_local(
                    args.artifact_root, args.report_id, args.export_id, charts=not args.no_charts
                )
        print(
            json.dumps(
                {
                    "report_id": args.report_id,
                    "status": result["status"],
                    "report_sha256": result["sha256"],
                    "command": args.command,
                }
            )
        )
        return 0 if result["status"] == "ready" else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
