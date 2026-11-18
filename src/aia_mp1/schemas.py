"""Canonical generated payload and its separately versioned provenance envelope."""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DOMAIN = os.environ.get("AIA_MP1_DOMAIN", "engineering")
if DOMAIN not in {"engineering", "home-diy", "aec-course"}:
    raise ValueError("AIA_MP1_DOMAIN must be engineering, home-diy or aec-course")
EngineeringCategory = Literal[
    "gis_scripting", "aec_automation", "structural_analysis", "cad_apis", "simulation"
]
RepairCategory = Literal[
    "appliance_repair",
    "plumbing_repair",
    "electrical_repair",
    "hvac_maintenance",
    "general_home_repair",
]
Category = RepairCategory if DOMAIN == "home-diy" else EngineeringCategory
CATEGORIES: tuple[str, ...] = get_args(Category)
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
    reference_context: dict | None = Field(default=None, exclude_if=lambda v: v is None)
    item: QAItem
