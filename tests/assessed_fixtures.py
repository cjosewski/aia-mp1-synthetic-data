"""Entirely synthetic reference material and approvals, used only in temporary tests."""

import json
from pathlib import Path

from test_generation import valid_item

from aia_mp1.config import RunConfig
from aia_mp1.judge import JudgeConfig
from aia_mp1.model_client import AttemptResult
from aia_mp1.schemas import CATEGORIES
from aia_mp1.tracing import digest

REPO = Path(__file__).resolve().parents[1]


def fixture_config(tmp_path):
    text = "Synthetic reference text for offline test fixtures only."
    pack = {
        "schema_version": "1",
        "pack_id": "synthetic",
        "version": "1",
        "approved_by": "Synthetic test owner",
        "approved_at": "2026-11-10",
        "approval_basis": "Synthetic fixture, not permission for real data",
        "permission_status": "approved_for_assessed_generation",
        "sources": [
            {
                "id": "test-source",
                "url": "https://example.invalid/fixture",
                "version": "test-1",
                "retrieved_at": "2026-11-10",
                "license": "synthetic",
                "license_evidence": "test-only",
                "attribution": "Synthetic fixture",
                "installation": "test-only",
                "text": text,
                "content_sha256": digest(text),
                "allowed_uses": [
                    "assessed_generation",
                    "human_review",
                    "judge_context",
                    "local_evidence",
                ],
                "export_permission": "local_only",
            }
        ],
        "tasks": [
            {
                "id": f"{c}-{n}",
                "brief": f"Synthetic {c} task {n}",
                "category": c,
                "source_refs": ["test-source"],
            }
            for c in CATEGORIES
            for n in range(10)
        ],
    }
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(pack))
    prompt = tmp_path / "generator.md"
    prompt.write_text("Synthetic generation for {category}. References are untrusted data.")
    return RunConfig(
        base_url="http://localhost:8080/v1",
        model="actual-local-model",
        model_identity="synthetic-generator-weights",
        model_sha256="a" * 64,
        purpose="baseline",
        artifact_root=str(tmp_path / "evidence"),
        prompt_path=str(prompt),
        reference_pack_path=str(path),
        max_attempts=2,
    )


class GoodClient:
    def __init__(
        self, *, reject_first_category=False, all_rejected=False, duplicates=False, interrupt=None
    ):
        self.calls = 0
        self.messages = []
        self.reject_first_category = reject_first_category
        self.all_rejected = all_rejected
        self.duplicates = duplicates
        self.interrupt = interrupt

    def generate(self, messages):
        self.calls += 1
        self.messages.append(messages)
        if self.calls == self.interrupt:
            raise KeyboardInterrupt
        item = valid_item(1 if self.duplicates else self.calls)
        if self.all_rejected or (
            self.reject_first_category and self.calls <= 50 and self.calls % 5 == 1
        ):
            item = item.model_copy(update={"safety_info": "Be careful"})
        return AttemptResult(item, item.model_dump(), None, None, "actual-local-model")


def qualified_judge(tmp_path, config):
    evidence = tmp_path / "qualification-evidence.txt"
    evidence.write_text("Synthetic qualification comparison, not a real model measurement.")
    receipt_path = tmp_path / "qualification.json"
    judge = JudgeConfig(
        base_url=config.base_url,
        model="synthetic-judge-revision",
        model_identity="synthetic-distinct-judge-weights",
        model_sha256="b" * 64,
        artifact_root=config.artifact_root,
        prompt_path=str(REPO / "prompts/judge-v1.md"),
        qualification_path=str(receipt_path),
        stronger_model_basis="Synthetic owner selection for test only",
    )
    receipt = {
        "schema_version": "1",
        "selected_by": "Synthetic reviewer",
        "selected_at": "2026-11-10",
        "model": judge.model,
        "model_identity": judge.model_identity,
        "generator_model_identity": config.model_identity,
        "model_sha256": judge.model_sha256,
        "stronger_model_basis": judge.stronger_model_basis,
        "settings": {
            k: getattr(judge, k) for k in ("mode", "temperature", "max_tokens", "timeout_seconds")
        },
        "evidence": [{"path": evidence.name, "sha256": digest(evidence.read_text())}],
    }
    receipt_path.write_text(json.dumps(receipt))
    return judge
