"""
STUB -- Phase 6, spec Layers 5 ("Career Narrative"), 10 ("Seniority
Calibration"), 11 ("Years-of-Experience Positioning"), 12 ("Professional
Summary Evaluation").

Responsibilities this module will own once implemented:
  - Answer "what does this person do?" in one sentence from the resume text
    and flag ambiguity against the user's TargetProfile.career_path.
  - Classify the implied role (Project Manager / Program Manager / TPM /
    Engineering Leader / M&P Engineer / etc.) -- see
    knowledge_base/role_taxonomy/ (currently an empty stub).
  - Judge seniority calibration: does the wording under- or over-sell scope
    vs. TargetProfile.seniority?
  - Judge whether total-years-of-experience framing helps or hurts
    positioning (with the spec's age-bias consideration).
  - Judge the professional summary on differentiation/specificity, not on
    "does a summary exist" -- never auto-recommend adding one.

Depends on real LLM-driven judgment (this is explicitly NOT a deterministic
rule-engine layer like ats_engine), so it is intentionally not built until
there's a real, tested prompt/evaluation harness for it -- see README.
"""
from __future__ import annotations

from app.models import AnalysisResult, TargetProfile


def evaluate_career_narrative(full_text: str, target: TargetProfile) -> dict:
    raise NotImplementedError(
        "career_engine.evaluate_career_narrative is not yet implemented. "
        "Scores that depend on it are reported as status='not yet implemented'."
    )
