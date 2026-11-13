"""Offline V8 package validation, ledger inspection and paired reports."""

import argparse
import json
from pathlib import Path

from .factcheck_report import build_report
from .factcheck_stages import Experiment, Ledger, load_json, new_json, validate_experiment


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser(
        "validate-package", help="validate inputs and local source hashes"
    )
    validate.add_argument("--package", type=Path, required=True)
    validate.add_argument("--source-root", type=Path, required=True)
    status = commands.add_parser("status", help="read and replay a development ledger")
    status.add_argument("--directory", type=Path, required=True)
    report = commands.add_parser(
        "report", help="compare saved results with separate frozen ratings"
    )
    report.add_argument("--directory", type=Path, required=True)
    report.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="JSON mapping selected item IDs to D1-D6 binary decisions",
    )
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-package":
            experiment = Experiment.model_validate(load_json(args.package))
            validate_experiment(experiment, args.source_root)
            result = {
                "valid": True,
                "selected": 5,
                "live_ready": False,
                "note": "source meaning, permission scope and token fit still need review",
            }
        elif args.command == "status":
            ledger = Ledger(args.directory)
            experiment, state = ledger.read()
            selected = ledger.next_stage(experiment, state)
            result = {
                "starts": len(state["starts"]),
                "finished": len(state["finishes"]),
                "unknown": state["pending"]["attempt_id"] if state["pending"] else None,
                "halt": state["halt"],
                "consecutive_failures": state["failures"],
                "next": {"item_id": selected[0].item_id, "stage": selected[1]}
                if selected
                else None,
            }
        else:
            output = args.output.resolve()
            if output.is_relative_to(Path(__file__).resolve().parents[2]):
                raise ValueError("raw comparison reports must stay outside Git")
            result = build_report(Ledger(args.directory), load_json(args.reference))
            new_json(output, result)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        # Avoid echoing source text, raw model output or Pydantic input values.
        print("Invalid or changed V8 artifact; preserve it and inspect the local inputs.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
