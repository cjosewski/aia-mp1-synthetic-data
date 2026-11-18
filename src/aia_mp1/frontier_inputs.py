"""Source-free, label-free paired judge inputs for a possible hosted comparison."""

import json

from .evaluation_schemas import DIMENSIONS
from .judge import messages_for
from .schemas import CATEGORIES, QAItem
from .tracing import digest

TASK_FIELDS = {"id", "brief", "category"}
PUBLIC_FIELDS = {"item_id", "category", "messages", "messages_sha256"}


def paired_rubric(rubric: dict) -> dict:
    """Retain rubric meaning without private adaptation or source metadata."""
    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, list) or [row.get("id") for row in dimensions] != list(
        DIMENSIONS
    ):
        raise ValueError("six ordered frozen dimensions are required")
    if not isinstance(rubric.get("version"), str) or not rubric["version"].strip():
        raise ValueError("rubric version is required")
    rows = []
    for dimension in dimensions:
        if any(
            not isinstance(dimension.get(key), str) or not dimension[key].strip()
            for key in ("id", "name", "pass_anchor", "fail_anchor")
        ):
            raise ValueError("rubric anchor is missing")
        rows.append({key: dimension[key] for key in ("id", "name", "pass_anchor", "fail_anchor")})
    return {"version": rubric["version"], "dimensions": rows}


def paired_messages(prompt: str, rubric: dict, record: dict) -> dict:
    """Keep only authored task fields and the seven-field generated candidate.

    The source-pack records are local-only. They are inspected for permission
    status and never copied into the message or returned artifact.
    """
    context = record.get("reference_context")
    if not isinstance(context, dict) or not isinstance(context.get("task"), dict):
        raise ValueError("assessment item needs a frozen reference task")
    sources = context.get("sources")
    if (
        not isinstance(sources, list)
        or not sources
        or any(
            not isinstance(source, dict) or source.get("export_permission") != "local_only"
            for source in sources
        )
    ):
        raise ValueError("source permissions differ from the local-only cohort")
    task = context["task"]
    if not all(isinstance(task.get(key), str) and task[key].strip() for key in TASK_FIELDS):
        raise ValueError("authored task id, brief and category are required")
    if task["category"] not in CATEGORIES or task["category"] != record.get("category"):
        raise ValueError("task and generated category differ")
    item = QAItem.model_validate(record["item"]).model_dump(mode="json")
    safe = {
        "item": item,
        "reference_context": {"task": {key: task[key] for key in ("id", "brief", "category")}},
    }
    messages = messages_for(prompt, paired_rubric(rubric), safe)
    result = {
        "item_id": record["item_id"],
        "category": task["category"],
        "messages": messages,
        "messages_sha256": digest({"messages": messages}),
    }
    validate_paired_message(result, prompt, rubric)
    return result


def validate_paired_message(result: dict, prompt: str, rubric: dict) -> None:
    """Reject changed wire inputs or any extra field before either judge arm."""
    if not isinstance(result, dict) or set(result) != PUBLIC_FIELDS:
        raise ValueError("paired input has unexpected fields")
    if not isinstance(result["item_id"], str) or not result["item_id"].strip():
        raise ValueError("paired input is missing item identity")
    messages = result["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError("paired messages are missing")
    body = json.loads(messages[1]["content"])
    if (
        set(body) != {"untrusted_item", "untrusted_reference_context"}
        or set(body["untrusted_reference_context"]) != {"task"}
        or set(body["untrusted_reference_context"]["task"]) != TASK_FIELDS
        or body["untrusted_reference_context"]["task"]["category"] != result["category"]
    ):
        raise ValueError("paired content has extra source fields")
    item = QAItem.model_validate(body["untrusted_item"]).model_dump(mode="json")
    task = body["untrusted_reference_context"]["task"]
    expected = messages_for(
        prompt, paired_rubric(rubric), {"item": item, "reference_context": {"task": task}}
    )
    if messages != expected or result["messages_sha256"] != digest({"messages": messages}):
        raise ValueError("paired wire differs from the frozen prompt and content")
