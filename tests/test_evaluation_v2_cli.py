"""The v2 CLI: every command's happy path; expected failures exit 2 with one error line."""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from v2_fixtures import REVIEWER, arms, complete_sheet, pin_task_pack

from aia_mp1.evaluation_v2_cli import main


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    root, config = arms(tmp_path)
    pack = Path(config.reference_pack_path)
    pin_task_pack(monkeypatch, pack)
    return root, pack, tmp_path


def run(capsys, *args):
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


def test_every_command_runs_end_to_end(evidence, capsys, monkeypatch):
    root, pack, tmp_path = evidence
    at = ["--artifact-root", str(root)]
    for cohort, assessment_id in (
        ("cohort-a", "assess-a"),
        ("cohort-b", "assess-b"),
        ("cohort-a", "scratch"),
    ):
        code, out, err = run(
            capsys,
            "create-assessment",
            *at,
            "--cohort-id",
            cohort,
            "--assessment-id",
            assessment_id,
            "--declare-no-prior-reviews",
        )
        assert code == 0 and not err and len(json.loads(out)["selected_ids"]) == 20
    code, out, _ = run(capsys, "status", *at, "--assessment-id", "scratch")
    pending = json.loads(out)["pending_item_ids"]
    assert code == 0 and len(pending) == 20
    code, out, _ = run(
        capsys,
        *("label", *at, "--assessment-id", "scratch", "--reviewer", REVIEWER),
        *("--item-id", pending[0], "--decisions", *"11011111", "--notes", "Synthetic note"),
    )
    assert code == 0 and json.loads(out)["decisions"]["api_correctness"] == 0
    monkeypatch.setattr(sys, "stdin", io.StringIO("1\n1\n1\n1\n1\n1\n1\nCLI note\n.\n"))
    code, out, _ = run(capsys, "label", *at, "--assessment-id", "scratch", "--reviewer", REVIEWER)
    assert code == 1 and "Saved item" in out and '"completed": 2' in out
    assert not any(item_id in out for item_id in pending)
    output = tmp_path / "reviewer"
    code, out, _ = run(
        capsys,
        *("prepare-packet", *at, "--packet-id", "packet-x", "--task-pack", str(pack)),
        *("--assessment-id", "assess-a", "--assessment-id", "assess-b", "--output", str(output)),
    )
    assert code == 0 and json.loads(out)["items"] == 40
    answers = output / "MY-ANSWERS.md"
    answers.write_text(complete_sheet(answers.read_text()))
    code, out, _ = run(
        capsys,
        *("import-answers", *at, "--packet-id", "packet-x"),
        *("--answers", str(answers), "--reviewer", REVIEWER),
    )
    assert code == 0 and json.loads(out)["labels"] == 40
    freeze = ("freeze-reference", *at, "--reviewer", REVIEWER, "--assessment-id")
    code, out, err = run(capsys, *freeze, "assess-a")
    assert code == 2 and not out and err.startswith("error: ") and "declare" in err
    for assessment_id in ("assess-a", "assess-b"):
        code, out, _ = run(capsys, *freeze, assessment_id, "--declare-blind")
        assert code == 0 and json.loads(out)["packet_ids"] == ["packet-x"]
    compare = ("compare", *at, "--baseline", "assess-a", "--corrected", "assess-b")
    code, out, err = run(capsys, *compare, "--comparison-id", "first")
    assert code == 2 and "undeclared generator differences" in err
    code, out, _ = run(
        capsys,
        *compare,
        *("--comparison-id", "first", "--declare", "settings.prompt_variant=Synthetic variant"),
    )
    result = json.loads(out)
    assert code == 0 and result["status"] == "complete" and Path(result["output"]).is_file()


def test_expected_failures_exit_2_with_one_error_line(evidence, capsys):
    root, pack, tmp_path = evidence
    at = ["--artifact-root", str(root)]
    create = ("create-assessment", *at, "--cohort-id", "cohort-a", "--declare-no-prior-reviews")
    main([*create, "--assessment-id", "assess-a"])
    capsys.readouterr()
    main(["status", *at, "--assessment-id", "assess-a"])
    item = json.loads(capsys.readouterr().out)["pending_item_ids"][0]
    label = ("label", *at, "--assessment-id", "assess-a", "--reviewer", REVIEWER)
    failures = [
        (
            ("create-assessment", *at, "--cohort-id", "nowhere", "--assessment-id", "x")
            + ("--declare-no-prior-reviews",),
            "No such",
        ),
        ((*create, "--assessment-id", "assess-a"), "exists"),
        (
            ("create-assessment", *at, "--cohort-id", "cohort-a", "--assessment-id", "y"),
            "no prior reviews",
        ),
        (("status", *at, "--assessment-id", "nowhere"), "No such"),
        ((*label, "--item-id", item, "--decisions", *"11111112"), "clarity"),
        ((*label, "--supersedes", "earlier-label"), "explicit labeling requires"),
        ((*label, "--notes", "Interactive notes are typed"), "explicit labels only"),
        (
            ("prepare-packet", *at, "--packet-id", "p", "--assessment-id", "assess-a")
            + ("--task-pack", str(pack), "--output", str(tmp_path / "out")),
            "two distinct",
        ),
        (
            ("import-answers", *at, "--packet-id", "nowhere", "--answers", str(pack))
            + ("--reviewer", REVIEWER),
            "No such",
        ),
        (
            ("freeze-reference", *at, "--assessment-id", "assess-a", "--reviewer", REVIEWER)
            + ("--declare-blind",),
            "20",
        ),
        (
            ("compare", *at, "--baseline", "assess-a", "--corrected", "assess-a")
            + ("--comparison-id", "c"),
            "two different",
        ),
        (
            ("compare", *at, "--baseline", "assess-a", "--corrected", "x", "--comparison-id", "c")
            + ("--declare", "no-separator"),
            "FIELD=REASON",
        ),
    ]
    for args, message in failures:
        assert main(list(args)) == 2, args
        out, err = capsys.readouterr()
        assert not out and err.startswith("error: ") and err.count("\n") == 1, args
        assert message in err and "Traceback" not in err, (args, err)


def test_module_entry_point_exits_2_without_a_traceback(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "aia_mp1.evaluation_v2_cli", "status"]
        + ["--artifact-root", str(tmp_path), "--assessment-id", "nowhere"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2 and not result.stdout
    assert result.stderr.startswith("error: ") and "Traceback" not in result.stderr
