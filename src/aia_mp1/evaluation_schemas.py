"""Strict human and judge contracts; neither accepts missing dimensions as passes."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from .schemas import NonBlank

DIMENSIONS = ("D1", "D2", "D3", "D4", "D5", "D6")
Binary = Annotated[int, Field(strict=True, ge=0, le=1)]


class Decisions(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    D1: Binary
    D2: Binary
    D3: Binary
    D4: Binary
    D5: Binary
    D6: Binary


class DimensionJudgment(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    decision: Binary
    justification: NonBlank


class Judgment(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    D1: DimensionJudgment
    D2: DimensionJudgment
    D3: DimensionJudgment
    D4: DimensionJudgment
    D5: DimensionJudgment
    D6: DimensionJudgment

    def decisions(self) -> dict[str, int]:
        return {key: getattr(self, key).decision for key in DIMENSIONS}


class HumanLabel(BaseModel):
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
    decisions: Decisions
    notes: str = ""
    supersedes_label_id: NonBlank | None = None
