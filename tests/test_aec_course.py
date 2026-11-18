"""Exercise profile selection at the same process boundary as the reviewer."""

import os
import subprocess
import sys
from pathlib import Path


def test_aec_review_uses_engineering_categories_and_literal_course_rubric():
    script = """
import json
from pathlib import Path
from aia_mp1.assessment import validate_rubric
from aia_mp1.cli import parser
from aia_mp1.acceptance import POLICIES, COURSE_POLICY
from aia_mp1.schemas import CATEGORIES
from aia_mp1.judge import JudgeConfig

args = parser().parse_args(["assessment", "--assessment-id", "synthetic", "--cohort-id", "example"])
rubric = json.loads(args.rubric.read_text())
validate_rubric(rubric)
assert CATEGORIES == ("gis_scripting", "aec_automation", "structural_analysis", "cad_apis", "simulation")
assert POLICIES == (COURSE_POLICY,)
assert "$50" in rubric["dimensions"][2]["pass_anchor"]
assert "DIY capability" in rubric["dimensions"][3]["pass_anchor"]
assert JudgeConfig(domain="aec-course", base_url="http://localhost:8080/v1",model="test").prompt_variant == "aec-course-judge-v1"
try:
    validate_rubric(json.loads(Path("config/rubric.json").read_text()))
except ValueError:
    pass
else:
    raise AssertionError("legacy scoring anchors accepted for the course assessment")
"""
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "AIA_MP1_DOMAIN": "aec-course"},
        check=True,
    )
