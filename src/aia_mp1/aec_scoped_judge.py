"""Score an AEC task with explicit required steps and optional scope notes."""

from aia_mp1.aec_development import (
    CoverageFinding,
    DevelopmentJudgment,
    TipFinding,
    checked_judgment,
)
from aia_mp1.evaluation_schemas import DIMENSIONS, DimensionJudgment
from aia_mp1.evidence_judge import StrictModel
from aia_mp1.passage_evidence import PassageID


class CitedDecision(DimensionJudgment):
    candidate_ids: list[PassageID]


class CitedRatings(StrictModel):
    D1: CitedDecision
    D2: CitedDecision
    D3: CitedDecision
    D4: CitedDecision
    D5: CitedDecision
    D6: CitedDecision


class ScopedJudgment(StrictModel):
    coverage: list[CoverageFinding]
    tips: list[TipFinding]
    ratings: CitedRatings


def project(result, content, rubric, required):
    # Each binary decision selects its own frozen rubric anchor. Candidate
    # citations and the actual score/justification come verbatim from the judge.
    ratings = {}
    for dimension in DIMENSIONS:
        row = getattr(result.ratings, dimension)
        anchor = "pass" if row.decision else "fail"
        ratings[dimension] = {
            "requirement": f"R.{dimension}.{anchor}",
            "evidence": row.candidate_ids,
            "counter": [],
            "decision": row.decision,
            "justification": row.justification,
        }
    evidence = DevelopmentJudgment(coverage=result.coverage, tips=result.tips, ratings=ratings)
    return checked_judgment(evidence, content, rubric, required)
