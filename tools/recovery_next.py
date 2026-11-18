"""Run one recovery preflight or one explicitly requested development attempt."""

import argparse
import json
import os
import platform
from pathlib import Path

from v15_remote import remote

from aia_mp1.recovery_ledger import RecoveryLedger
from aia_mp1.recovery_runner import run_next
from aia_mp1.recovery_tunnel import read_windows_tunnel


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="send exactly one new model request")
    args = parser.parse_args(argv)
    if platform.system() != "Linux" or "microsoft" not in platform.release().lower():
        parser.error("run this command from WSL2 Ubuntu")
    key = os.environ.get("AIA_MP1_LOCAL_API_KEY", "local-only-placeholder")
    if not key.strip():
        parser.error("AIA_MP1_LOCAL_API_KEY must not be blank")
    try:
        ledger = RecoveryLedger(args.journal)
        result = run_next(
            ledger, args.packet, key, remote, read_windows_tunnel, execute=args.execute
        )
    except Exception as exc:
        # Endpoint and exception messages can contain credentials or raw answers.
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "error_type": type(exc).__name__,
                    "journal": str(args.journal),
                    "model_starts_added": "inspect_journal",
                }
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": result["outcome"],
                "receipt": result.get("receipt", result.get("preflight_receipt")),
                "calibration_eligible": False,
            }
        )
    )
    return 0 if result["outcome"] in {"preflight_only", "response_retained"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
