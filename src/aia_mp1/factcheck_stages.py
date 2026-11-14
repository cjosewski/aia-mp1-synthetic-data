"""Offline-testable V8 scheduling and durable evidence. No network launcher."""

import json
import os
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .assessment import exclusive, validate_rubric
from .evaluation_schemas import Judgment
from .evidence_judge import StrictModel, _unique_keys, completion_json
from .factcheck import (
    SHA,
    FactReport,
    Memo,
    ScoreReport,
    Stage,
    make_memo,
    project_passages,
    project_score,
    resolve_report,
    validate_input,
    validate_memo,
)
from .passage_evidence import PassageJudgment
from .schemas import CATEGORIES, Category, NonBlank
from .tracing import append_record, digest, now, write_checkpoint

SCHEMAS = {"control": PassageJudgment, "facts": FactReport, "score": ScoreReport}


class Runtime(StrictModel):
    model: NonBlank
    model_sha256: SHA
    build: NonBlank
    template_sha256: SHA
    context_size: Literal[16384]
    slots: Literal[1]
    temperature: Annotated[float, Field(ge=0.1, le=0.1)]
    max_tokens: Literal[4096]
    timeout_seconds: Literal[300]

    @field_validator("context_size", "slots", "max_tokens", "timeout_seconds", mode="before")
    @classmethod
    def exact_integer(cls, value):
        if type(value) is not int:
            raise ValueError("runtime counts must be integers, not booleans")
        return value


class Prompts(StrictModel):
    control: str
    facts: str
    score: str

    @field_validator("*")
    @classmethod
    def preserve_prompt(cls, value):
        if not value.strip():
            raise ValueError("prompt must be nonblank")
        return value


class Case(StrictModel):
    item_id: NonBlank
    category: Category
    content: dict


class Experiment(StrictModel):
    protocol: Literal["v8-development"]
    cases: Annotated[list[Case], Field(min_length=5, max_length=5)]
    rubric: dict
    prompts: Prompts
    runtime: Runtime
    reference_sha256: SHA
    prior_starts: Literal[92]
    max_starts: Literal[30]
    attempts_per_stage: Literal[2]
    consecutive_failure_limit: Literal[2]


class Completion(StrictModel):
    """Only redacted response bodies, never headers or credential-bearing exceptions."""

    raw_response: dict | str | None
    transport_failure: bool
    elapsed_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)]


def load_json(path: Path):
    if path.is_symlink():
        raise ValueError("symlink evidence is not supported")

    def reject_constant(_):
        raise ValueError("nonfinite JSON is not supported")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_keys,
        parse_constant=reject_constant,
    )


def validate_experiment(experiment: Experiment, source_root: Path | None = None) -> None:
    validate_rubric(experiment.rubric)
    if len({case.item_id for case in experiment.cases}) != 5 or {
        case.category for case in experiment.cases
    } != set(CATEGORIES):
        raise ValueError("experiment needs five unique cases, one per category")
    for case in experiment.cases:
        validate_input(case.content, experiment.rubric, source_root)


def contract_hash() -> str:
    # Bind validation/scheduling code and response schemas, not only model prompts.
    directory = Path(__file__).parent
    return digest(
        {
            "files": {
                name: digest((directory / name).read_text(encoding="utf-8"))
                for name in (
                    "factcheck.py",
                    "factcheck_stages.py",
                    "passage_evidence.py",
                    "evidence_judge.py",
                    "evaluation_schemas.py",
                    "schemas.py",
                    "factcheck_report.py",
                    "factcheck_transport.py",
                    "model_client.py",
                )
            },
            "schemas": {stage: schema.model_json_schema() for stage, schema in SCHEMAS.items()},
        }
    )


def new_json(path: Path, record: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def schedule(experiment: Experiment):
    for number, case in enumerate(experiment.cases, 1):
        for stage in ("control", "facts", "score") if number % 2 else ("facts", "score", "control"):
            yield case, stage


def evaluate(
    experiment: Experiment,
    case: Case,
    stage: Stage,
    attempt_id: str,
    completion: Completion,
    predecessor: dict | None,
) -> dict:
    """Recomputed during replay; persisted projections never authorize themselves."""
    result = {
        "status": "failed",
        "error_type": None,
        "parsed": None,
        "schema_valid": False,
        "memo": None,
        "canonical": None,
        "resolved": None,
        "fatal": False,
    }
    raw = completion.raw_response
    if completion.transport_failure:
        result["error_type"] = "transport"
        return result
    if (
        isinstance(raw, dict)
        and raw.get("model") is not None
        and raw["model"] != experiment.runtime.model
    ):
        result.update(error_type="model_identity", fatal=True)
        return result
    try:
        parsed = SCHEMAS[stage].model_validate(completion_json(raw))
        result["schema_valid"] = True
        if raw.get("model") != experiment.runtime.model:
            raise ValueError("completion must report the frozen model identity")
        catalog = validate_input(case.content, experiment.rubric)
        canonical = None
        if stage == "facts":
            memo = make_memo(
                raw,
                case.content,
                experiment.rubric,
                experiment.prompts.facts,
                experiment.runtime.model_dump(),
                attempt_id,
            )
            result["memo"] = memo.model_dump()
            result["resolved"] = {
                key: {
                    field: [
                        {"id": identifier, **catalog[identifier]}
                        for identifier in getattr(finding, field)
                    ]
                    for field in ("candidate_ids", "task_refs", "source_refs")
                }
                for key, finding in memo.findings.items()
            }
        elif stage == "control":
            canonical = project_passages(parsed, catalog)
            result["resolved"] = resolve_report(parsed, catalog)
        else:
            memo = accepted_memo(experiment, case, predecessor)
            canonical = project_score(parsed, memo, catalog)
            if canonical is not None:
                result["resolved"] = resolve_report(parsed.judgment, catalog)
        result["status"] = "unresolved" if stage == "score" and canonical is None else "accepted"
        result["parsed"] = parsed.model_dump()
        result["canonical"] = canonical.model_dump() if canonical is not None else None
    except (ValueError, TypeError, KeyError, IndexError):
        # Fixed diagnostic text, with the original redacted body preserved separately.
        result.update(
            status="failed",
            error_type="contract",
            parsed=None,
            memo=None,
            canonical=None,
            resolved=None,
        )
    return result


def accepted_memo(experiment: Experiment, case: Case, predecessor: dict | None) -> Memo:
    if predecessor is None or predecessor["result"]["status"] != "accepted":
        raise ValueError("score stage requires an accepted fact attempt")
    memo = Memo.model_validate(predecessor["result"]["memo"])
    validate_memo(
        memo,
        case.content,
        experiment.rubric,
        experiment.prompts.facts,
        experiment.runtime.model_dump(),
        predecessor["attempt_id"],
        predecessor["completion"]["raw_response"],
    )
    return memo


def request_for(experiment: Experiment, case: Case, stage: Stage, predecessor: dict | None) -> dict:
    content = dict(case.content)
    # Original text remains in candidate/context/excerpts. Send its typed locations
    # once, rather than repeating every passage's text in a second catalog.
    content["passage_catalog"] = {
        key: {"path": entry["path"], "authority": entry["authority"]}
        for key, entry in case.content["passage_catalog"].items()
    }
    if stage == "score":
        # The ledger retains the complete report; do not repeat each finding twice on the wire.
        content["untrusted_fact_memo"] = accepted_memo(experiment, case, predecessor).model_dump(
            exclude={"report"}
        )
    system = getattr(experiment.prompts, stage)
    if stage != "facts":
        system += "\n\nFrozen rubric:\n" + json.dumps(experiment.rubric, ensure_ascii=False)
    return {
        "model": experiment.runtime.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
        ],
        "response_schema": SCHEMAS[stage].model_json_schema(),
        "temperature": experiment.runtime.temperature,
        "max_tokens": experiment.runtime.max_tokens,
        "timeout_seconds": experiment.runtime.timeout_seconds,
    }


class Ledger:
    """Single-writer append-only events, hash chain and independently checked head.

    A missing finish is an unknown request, never a free retry. A crash between
    event append and head update requires inspection; no automatic tail repair.
    """

    def __init__(self, directory: Path):
        if directory.is_symlink():
            raise ValueError("symlink ledger is not supported")
        self.directory = directory.resolve()
        repository = Path(__file__).resolve().parents[2]
        if self.directory.is_relative_to(repository):
            raise ValueError("development evidence must stay outside Git")

    @classmethod
    def create(cls, directory: Path, experiment: Experiment, source_root: Path):
        validate_experiment(experiment, source_root)
        ledger = cls(directory)
        ledger.directory.mkdir(parents=True, exist_ok=False)
        manifest = {"experiment": experiment.model_dump(), "contract_sha256": contract_hash()}
        new_json(ledger.directory / "manifest.json", manifest)
        new_json(ledger.directory / "head.json", {"count": 0, "sha256": digest(manifest)})
        return ledger

    def read(self) -> tuple[Experiment, dict]:
        manifest = load_json(self.directory / "manifest.json")
        if (
            not isinstance(manifest, dict)
            or set(manifest) != {"experiment", "contract_sha256"}
            or manifest["contract_sha256"] != contract_hash()
        ):
            raise ValueError("frozen implementation contract differs")
        experiment = Experiment.model_validate(manifest["experiment"])
        validate_experiment(experiment)
        state = {
            "starts": [],
            "finishes": [],
            "pending": None,
            "failures": 0,
            "halt": None,
            "head": digest(manifest),
            "count": 0,
        }
        path = self.directory / "events.jsonl"
        if path.is_symlink():
            raise ValueError("symlink ledger is not supported")
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if text and not text.endswith("\n"):
                raise ValueError("incomplete event write; preserve and inspect")
            for line in text.splitlines():
                event = json.loads(line, object_pairs_hook=_unique_keys)
                if not isinstance(event, dict) or set(event) != {
                    "previous",
                    "timestamp",
                    "record",
                    "sha256",
                }:
                    raise ValueError("unexpected event envelope")
                if (
                    not isinstance(event["record"], dict)
                    or not isinstance(event["timestamp"], str)
                    or not event["timestamp"].strip()
                ):
                    raise ValueError("invalid event record or timestamp")
                unsigned = {key: event[key] for key in ("previous", "timestamp", "record")}
                if event["previous"] != state["head"] or event["sha256"] != digest(unsigned):
                    raise ValueError("event chain changed")
                self._replay(experiment, state, event["record"])
                state.update(head=event["sha256"], count=state["count"] + 1)
        if load_json(self.directory / "head.json") != {
            "count": state["count"],
            "sha256": state["head"],
        }:
            raise ValueError("event/head mismatch; preserve and inspect interrupted writes")
        return experiment, state

    @staticmethod
    def next_stage(experiment: Experiment, state: dict):
        if (
            state["pending"]
            or state["halt"]
            or state["failures"] >= 2
            or len(state["starts"]) >= experiment.max_starts
        ):
            return None
        for case, stage in schedule(experiment):
            prior = [
                row
                for row in state["finishes"]
                if row["item_id"] == case.item_id and row["stage"] == stage
            ]
            if any(row["result"]["status"] != "failed" for row in prior) or len(prior) >= 2:
                continue
            predecessor = next(
                (
                    row
                    for row in state["finishes"]
                    if row["item_id"] == case.item_id
                    and row["stage"] == "facts"
                    and row["result"]["status"] == "accepted"
                ),
                None,
            )
            if stage == "score" and predecessor is None:
                continue
            return case, stage, predecessor
        return None

    @staticmethod
    def _start(experiment, state, selected):
        case, stage, predecessor = selected
        request = request_for(experiment, case, stage, predecessor)
        return {
            "kind": "start",
            "attempt_id": f"attempt-{len(state['starts']) + 1:04d}",
            "item_id": case.item_id,
            "stage": stage,
            "input_sha256": digest(case.content),
            "runtime_sha256": digest(experiment.runtime.model_dump()),
            "predecessor_sha256": digest(predecessor) if stage == "score" else None,
            "request": request,
            "request_sha256": digest(request),
        }

    def _replay(self, experiment, state, record):
        if record.get("kind") == "start":
            selected = self.next_stage(experiment, state)
            if selected is None or record != self._start(experiment, state, selected):
                raise ValueError("start violates schedule, budget, request or predecessor lineage")
            state["starts"].append(record)
            state["pending"] = record
        elif record.get("kind") == "finish":
            pending = state["pending"]
            if (
                pending is None
                or set(record) != {"kind", "attempt_id", "item_id", "stage", "completion", "result"}
                or any(record[key] != pending[key] for key in ("attempt_id", "item_id", "stage"))
            ):
                raise ValueError("finish does not belong to the pending start")
            case = next(c for c in experiment.cases if c.item_id == pending["item_id"])
            predecessor = next(
                (row for row in state["finishes"] if digest(row) == pending["predecessor_sha256"]),
                None,
            )
            computed = evaluate(
                experiment,
                case,
                pending["stage"],
                pending["attempt_id"],
                Completion.model_validate(record["completion"]),
                predecessor,
            )
            if computed != record["result"]:
                raise ValueError("saved projection differs from raw response validation")
            state["finishes"].append(record)
            state["pending"] = None
            state["failures"] = state["failures"] + 1 if computed["status"] == "failed" else 0
            if computed["fatal"]:
                state["halt"] = computed["error_type"]
        elif record.get("kind") == "halt" and set(record) == {"kind", "reason"}:
            if state["halt"] or record["reason"] not in {"preflight_mismatch", "token_fit"}:
                raise ValueError("invalid halt receipt")
            state["halt"] = record["reason"]
        else:
            raise ValueError("unknown stage event")

    def _append(self, state, record):
        event = {"previous": state["head"], "timestamp": now(), "record": record}
        event["sha256"] = digest(event)
        append_record(self.directory / "events.jsonl", event)
        write_checkpoint(
            self.directory / "head.json", {"count": state["count"] + 1, "sha256": event["sha256"]}
        )

    def begin(self, observed_runtime: dict, source_root: Path) -> dict:
        """Durably reserve one request immediately before dispatch by a caller."""
        with exclusive(self.directory):
            experiment, state = self.read()
            selected = self.next_stage(experiment, state)
            if selected is None:
                raise ValueError("no request allowed: complete, halted or unknown outcome")
            try:
                if observed_runtime != experiment.runtime.model_dump():
                    raise ValueError("runtime changed")
                validate_experiment(experiment, source_root)
            except (ValueError, OSError):
                self._append(state, {"kind": "halt", "reason": "preflight_mismatch"})
                raise ValueError(
                    "runtime/source preflight differs; halt receipt retained"
                ) from None
            record = self._start(experiment, state, selected)
            self._append(state, record)
            return record

    def halt(self, reason: str) -> None:
        if reason not in {"preflight_mismatch", "token_fit"}:
            raise ValueError("unsupported preflight halt")
        with exclusive(self.directory):
            _, state = self.read()
            if state["pending"] or state["halt"]:
                raise ValueError("cannot replace an existing halt or unknown request")
            self._append(state, {"kind": "halt", "reason": reason})

    def finish(self, attempt_id: str, completion: Completion) -> dict:
        with exclusive(self.directory):
            experiment, state = self.read()
            pending = state["pending"]
            if pending is None or pending["attempt_id"] != attempt_id:
                raise ValueError("completion must resolve the pending request exactly once")
            case = next(c for c in experiment.cases if c.item_id == pending["item_id"])
            predecessor = next(
                (row for row in state["finishes"] if digest(row) == pending["predecessor_sha256"]),
                None,
            )
            result = evaluate(
                experiment, case, pending["stage"], attempt_id, completion, predecessor
            )
            record = {
                "kind": "finish",
                "attempt_id": attempt_id,
                "item_id": case.item_id,
                "stage": pending["stage"],
                "completion": completion.model_dump(),
                "result": result,
            }
            self._append(state, record)
            return record

    def run_next(self, observed_runtime: dict, source_root: Path, dispatch) -> dict:
        """One callback invocation; no retries or repair inside this boundary.

        Unexpected exceptions leave the start pending. The caller must provide a
        redacted Completion, including explicit transport failures when known.
        This package does not provide a network dispatch implementation yet.
        """
        started = self.begin(observed_runtime, source_root)
        completion = dispatch(started["request"])
        if not isinstance(completion, Completion):
            raise ValueError("dispatch must return Completion; request remains unknown")
        return self.finish(started["attempt_id"], completion)


def canonical(record: dict) -> Judgment | None:
    value = record["result"]["canonical"]
    return Judgment.model_validate(value) if value is not None else None
