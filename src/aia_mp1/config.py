"""Explicit local endpoint configuration; credentials never enter run manifests."""

import ipaddress
import json
import os
import re
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from .schemas import DOMAIN

Nonblank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    base_url: Nonblank
    domain: Literal["engineering", "home-diy", "aec-course"] = Field(
        default="engineering", exclude_if=lambda v: v == "engineering"
    )
    model: Nonblank
    purpose: Literal["smoke", "baseline", "corrected"] = "smoke"
    reference_pack_path: Nonblank | None = None
    model_identity: Nonblank | None = None
    model_sha256: Nonblank | None = None
    api_key_env: Nonblank | None = "AIA_MP1_API_KEY"
    api_key_file: Nonblank | None = None
    mode: Literal["json", "tools"] = "json"
    temperature: float = Field(default=0.6, ge=0, le=2)
    timeout_seconds: float = Field(default=60, gt=0, le=300)
    max_tokens: int = Field(default=1600, ge=1, le=8192)
    max_attempts: int = Field(default=3, ge=1, le=5)
    artifact_root: Nonblank = "../artifacts/evidence/P1-03"
    prompt_path: Nonblank = "prompts/generator-v1.md"
    prompt_variant: Nonblank = "baseline"
    sources_path: Nonblank = "config/sources.json"
    source_refs: list[Nonblank] = Field(
        default_factory=lambda: ["personal-task-briefs-v1"], min_length=1
    )

    @field_validator("base_url")
    @classmethod
    def local_endpoint(cls, value: str) -> str:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError("base_url must be an explicit local HTTP(S) endpoint")
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("base_url cannot contain credentials, a query or a fragment")
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("invalid endpoint port")
        if url.hostname != "localhost":
            try:
                address = ipaddress.ip_address(url.hostname)
            except ValueError as exc:
                raise ValueError("use localhost or an explicit private/loopback IP") from exc
            if not (address.is_loopback or address.is_private) or address.is_unspecified:
                raise ValueError("this kickoff supports only explicit local endpoints")
        if url.path.rstrip("/") != "/v1":
            raise ValueError("base_url must end in /v1")
        return value.rstrip("/")

    @model_validator(mode="after")
    def credential_source(self):
        if self.domain != DOMAIN:
            raise ValueError("config domain must match AIA_MP1_DOMAIN")
        if bool(self.api_key_env) == bool(self.api_key_file):
            raise ValueError("set exactly one of api_key_env and api_key_file")
        if len(set(self.source_refs)) != len(self.source_refs):
            raise ValueError("source_refs must be unique")
        if self.model_sha256 is not None and not re.fullmatch("[a-f0-9]{64}", self.model_sha256):
            raise ValueError("model_sha256 must be a lowercase SHA-256 checksum")
        return self

    @field_validator("artifact_root")
    @classmethod
    def external_artifacts(cls, value: str) -> str:
        repository = Path(__file__).resolve().parents[2]
        if Path(value).resolve().is_relative_to(repository):
            raise ValueError("raw artifacts must be stored outside the implementation repository")
        return value

    def api_key(self) -> str:
        if self.api_key_file:
            try:
                value = Path(self.api_key_file).read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ValueError("cannot read configured local API-key file") from exc
        else:
            value = os.environ.get(self.api_key_env or "", "").strip()
        if not value:
            raise ValueError("configured local API key is missing or empty")
        return value

    def public_settings(self) -> dict:
        return self.model_dump(exclude={"api_key_env", "api_key_file"}) | {
            "authentication": "file" if self.api_key_file else "environment"
        }


def load_config(path: Path) -> RunConfig:
    return RunConfig.model_validate_json(path.read_text(encoding="utf-8"))


def load_inputs(config: RunConfig) -> tuple[str, dict]:
    prompt = Path(config.prompt_path).read_text(encoding="utf-8")
    if "{category}" not in prompt:
        raise ValueError("generator prompt must include {category}")
    if config.purpose != "smoke":
        from .sources import load_pack

        if not config.reference_pack_path or not config.model_identity or not config.model_sha256:
            raise ValueError("assessed generation requires reference pack and model identity")
        pack = load_pack(Path(config.reference_pack_path))
        return prompt, pack
    sources = json.loads(Path(config.sources_path).read_text(encoding="utf-8"))
    if not isinstance(sources, dict):
        raise ValueError("sources manifest must be a JSON object")
    entries = sources.get("sources", [])
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("sources manifest must contain a list of source objects")
    by_id = {entry.get("id"): entry for entry in entries}
    if len(by_id) != len(entries):
        raise ValueError("duplicate source identity")
    for source_id in config.source_refs:
        entry = by_id.get(source_id, {})
        allowed = entry.get("allowed_uses", [])
        if not isinstance(allowed, list) or not all(isinstance(use, str) for use in allowed):
            raise ValueError("source allowed_uses must be a list of strings")
        if entry.get("permission_status") != "approved_for_local_smoke" or (
            "local_smoke_generation" not in allowed
        ):
            raise ValueError(f"source {source_id!r} is not cleared for local smoke generation")
    return prompt, sources
