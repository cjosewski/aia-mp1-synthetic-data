"""Canonical generated payload and its separately versioned provenance envelope."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CATEGORIES: tuple[str, ...] = (
    "gis_scripting",
    "aec_automation",
    "structural_analysis",
    "cad_apis",
    "simulation",
)
Category = Literal[
    "gis_scripting", "aec_automation", "structural_analysis", "cad_apis", "simulation"
]
NonBlank = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)]


class QAItem(BaseModel):
    """The portal's seven fields; legacy spelling never appears in serialized output."""

    model_config = ConfigDict(strict=True, extra="forbid")

    question: NonBlank
    answer: NonBlank
    equipment_problem: NonBlank
    tools_required: Annotated[list[NonBlank], Field(min_length=1)]
    steps: Annotated[list[NonBlank], Field(min_length=3)]
    safety_info: NonBlank
    tips: Annotated[list[NonBlank], Field(min_length=1)]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_problem(cls, value: Any) -> Any:
        """Accept the copied checklist's key explicitly, without mutating its raw evidence."""
        if not isinstance(value, dict) or "problem" not in value:
            return value
        normalized = dict(value)
        legacy = normalized.pop("problem")
        if "equipment_problem" in normalized:
            if normalized["equipment_problem"] != legacy:
                raise ValueError("conflicting problem and equipment_problem values")
        else:
            normalized["equipment_problem"] = legacy
        return normalized


class GeneratedItem(BaseModel):
    """One schema-valid result, with provenance outside the seven-field item."""

    model_config = ConfigDict(strict=True, extra="forbid")

    schema_version: Literal["1"] = "1"
    run_id: NonBlank
    trace_id: NonBlank
    item_id: NonBlank
    attempt_id: NonBlank
    parent_attempt_id: NonBlank | None = None
    category: Category
    prompt_variant: NonBlank
    prompt_hash: NonBlank
    model: NonBlank
    source_refs: list[NonBlank]
    item: QAItem
