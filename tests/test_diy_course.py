"""Run the isolated course profile in a fresh interpreter like the CLI."""

import os
import subprocess
import sys
from pathlib import Path


def test_course_domain_rejects_engineering_inputs_and_screens_all_dimensions():
    code = """
from pathlib import Path
from aia_mp1.assessment import read_json, validate_rubric
from aia_mp1.config import load_config, load_inputs
from aia_mp1.gate import _heuristic_checks
from aia_mp1.schemas import CATEGORIES, QAItem
from aia_mp1.sources import context_for

config = load_config(Path("config/diy/baseline.json"))
_, pack = load_inputs(config)
assert len({context_for(pack, c, n)["task"]["brief"] for c in CATEGORIES for n in range(10)}) == 50
validate_rubric(read_json(Path("config/diy/rubric.json")))
try:
    validate_rubric(read_json(Path("config/rubric.json")))
except ValueError:
    pass
else:
    raise AssertionError("engineering rubric accepted for course review")
item = QAItem(question="Synthetic unrelated question", answer="short", equipment_problem="fixture",
              tools_required=["Trade-only instrument"], steps=["Open breaker panel", "repeat", "repeat"],
              safety_info="Be careful", tips=["repeat"])
checks = _heuristic_checks(item)
assert set(checks) == set("D1 D2 D3 D4 D5 D6".split())
assert all(check["status"] == "failed" for check in checks.values())
"""
    subprocess.run(
        [sys.executable, "-c", code],
        env={**os.environ, "AIA_MP1_DOMAIN": "home-diy"},
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )
