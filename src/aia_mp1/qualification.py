"""Validate an attributed judge selection and its retained supporting evidence."""

import hashlib
import re
from pathlib import Path

from .assessment import read_json
from .tracing import digest


def validate_qualification(config, assessment: dict) -> dict:
    if not config.qualification_path or not config.model_identity or not config.model_sha256:
        raise ValueError("assessed judge requires model identity and qualification receipt")
    path = Path(config.qualification_path)
    receipt = read_json(path)
    expected_settings = {
        k: getattr(config, k) for k in ("mode", "temperature", "max_tokens", "timeout_seconds")
    }
    if config.reasoning_effort is not None:
        expected_settings["reasoning_effort"] = config.reasoning_effort
    if getattr(config, "server_reasoning_budget", None) is not None:
        expected_settings["server_reasoning_budget"] = config.server_reasoning_budget
    for field in ("selected_by", "selected_at", "stronger_model_basis", "model_sha256"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError("judge qualification is incomplete")
    if (
        receipt.get("schema_version") != "1"
        or receipt.get("model") != config.model
        or receipt.get("model_identity") != config.model_identity
        or receipt.get("generator_model_identity") != assessment["generator_model_identity"]
        or config.model_identity == assessment["generator_model_identity"]
        or receipt["model_sha256"] != config.model_sha256
        or config.model_sha256 == assessment["generator_model_sha256"]
        or receipt["stronger_model_basis"] != config.stronger_model_basis
        or receipt.get("settings") != expected_settings
    ):
        raise ValueError("judge qualification does not match selected model/settings")
    evidence = receipt.get("evidence", [])
    if not re.fullmatch("[a-f0-9]{64}", receipt["model_sha256"]):
        raise ValueError("judge model checksum must be SHA-256")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("judge qualification needs retained evidence")
    for item in evidence:
        evidence_path = path.parent / item["path"]
        if (
            evidence_path.is_symlink()
            or hashlib.sha256(evidence_path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("judge qualification evidence changed")
    return {"receipt": receipt, "sha256": digest(receipt)}
