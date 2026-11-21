"""Frozen AEC rubric v2: eight binary dimensions, accepted only byte-for-byte."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .assessment import read_text
from .evaluation_schemas import Binary
from .schemas import NonBlank
from .tracing import digest

RUBRIC_V2_PATH = Path("config/aec-course/rubric-v2.json")
RUBRIC_V2_SHA256 = "c366ecace6fd663405d8831019d7806b47f27b5ebd71a3d38eb15d2e323b078f"
RUBRIC_V2_VERSION = "aec-rubric-v2"
DIMENSIONS_V2 = (
    "fidelity",
    "completeness",
    "api_correctness",
    "verification",
    "safety",
    "professional_boundary",
    "tips",
    "clarity",
)


class DecisionsV2(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    fidelity: Binary
    completeness: Binary
    api_correctness: Binary
    verification: Binary
    safety: Binary
    professional_boundary: Binary
    tips: Binary
    clarity: Binary


class HumanLabelV2(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    label_id: NonBlank
    assessment_id: NonBlank
    item_id: NonBlank
    trace_id: NonBlank
    payload_sha256: NonBlank
    rubric_version: NonBlank
    rubric_sha256: NonBlank
    reviewer: NonBlank
    timestamp: NonBlank
    decisions: DecisionsV2
    notes: str = ""
    supersedes_label_id: NonBlank | None = None
    review_stage: Literal["blind", "post_review", "unknown"]
    consulted_report_ids: list[NonBlank] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    packet_id: NonBlank | None = Field(default=None, exclude_if=lambda v: v is None)
    review_id: NonBlank | None = Field(default=None, exclude_if=lambda v: v is None)

    @model_validator(mode="after")
    def packet_fields_together(self):
        if (self.packet_id is None) != (self.review_id is None):
            raise ValueError("packet_id and review_id are recorded together")
        return self


def load_rubric_v2(text: str | None = None) -> dict:
    """Return the frozen rubric; any other text, even equivalent JSON, is refused."""
    if text is None:
        text = read_text(Path(__file__).resolve().parents[2] / RUBRIC_V2_PATH)
    if digest(text) != RUBRIC_V2_SHA256:
        raise ValueError("rubric text is not the frozen aec-rubric-v2 (sha256 differs)")
    rubric = json.loads(text)
    if not isinstance(rubric, dict) or rubric.get("status") != "frozen":
        raise ValueError("rubric v2 must be frozen")
    if rubric.get("version") != RUBRIC_V2_VERSION:
        raise ValueError(f"rubric version must be {RUBRIC_V2_VERSION}")
    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, list) or [d.get("id") for d in dimensions] != list(DIMENSIONS_V2):
        raise ValueError("rubric must list the eight v2 dimension IDs in order")
    if rubric.get("label_values") != [0, 1]:
        raise ValueError("rubric label_values must be [0, 1]")
    if set(rubric.get("per_dimension_pass_rate_minimum") or {}) != set(DIMENSIONS_V2):
        raise ValueError("per-dimension minimum keys must equal the eight dimensions")
    if (rubric.get("overall_pass") or {}).get("rule") != "all_eight_dimensions_pass":
        raise ValueError("overall pass must require all eight dimensions")
    boundary = rubric.get("professional_boundary_triggers") or {}
    tasks = boundary.get("tasks")
    if (
        boundary.get("status") != "owner_confirmed"
        or boundary.get("task_count") != 50
        or not isinstance(tasks, list)
        or len({task.get("task_id") for task in tasks}) != 50
        or len(tasks) != 50
        or any(type(task.get("triggered")) is not bool for task in tasks)
    ):
        raise ValueError(
            "professional-boundary classification must be owner_confirmed for 50 distinct tasks"
        )
    return rubric


def boundary_triggered(rubric: dict, task_id: str) -> bool:
    """Whether the brief's results feed a design or code-compliance decision (owner, Q12)."""
    matches = [
        task
        for task in rubric["professional_boundary_triggers"]["tasks"]
        if task["task_id"] == task_id
    ]
    if len(matches) != 1:
        raise ValueError(f"task {task_id!r} has no frozen professional-boundary classification")
    return matches[0]["triggered"] is True
