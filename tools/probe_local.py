"""Read-only local serving probe; does not start or configure a model server."""

import argparse
import json
from pathlib import Path

import httpx

from aia_mp1.config import RunConfig
from aia_mp1.tracing import now

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
config = RunConfig(base_url=args.base_url, model="probe-only")
report = {
    "checked_at": now(),
    "base_url": config.base_url,
    "requests": [],
    "ready": False,
    "note": "Read-only unauthenticated connectivity probe; no generation performed.",
}
with httpx.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
    for url in (config.base_url.removesuffix("/v1") + "/health", config.base_url + "/models"):
        try:
            response = client.get(url)
            result = {"url": url, "http_status": response.status_code}
            if response.status_code == 200 and url.endswith("/models"):
                result["model_ids"] = [entry["id"] for entry in response.json().get("data", [])]
                report["ready"] = bool(result["model_ids"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            result = {"url": url, "error_type": type(exc).__name__, "error": str(exc)}
        report["requests"].append(result)
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
