"""
Tests the LLM-backed modules (career_engine, aerospace_engine's bullet
quality pass, jd_matching, keyword_engine's semantic enrichment) by
monkeypatching app.llm.client.call_tool with canned responses -- NEVER a
real network/API call, so this suite costs nothing and needs no key.

A separate, opt-in real-API smoke test would be a natural addition once
this project has a CI environment with a budget for it; not included here.
"""
from __future__ import annotations

from app.models import TargetProfile


def _next_id():
    counter = {"n": 0}

    def f():
        counter["n"] += 1
        return f"F{counter['n']:03d}"

    return f


def test_career_engine_builds_findings_from_flags(monkeypatch):
    from app.career_engine import engine as career_engine

    canned = {
        "narrative_sentence": "A technical program manager delivering aerospace hardware programs.",
        "implied_role": "Technical Program Manager",
        "role_alignment_score": 82,
        "role_alignment_rationale": "Matches the stated target closely.",
        "seniority_calibration": "matches",
        "seniority_score": 75,
        "seniority_rationale": "Scope described matches senior IC level.",
        "summary_present": False,
        "summary_evaluation": "Linear trajectory; a summary would add little.",
        "summary_differentiation_score": None,
        "years_experience_note": "Not displayed; not needed given clear title progression.",
        "recruiter_readability_score": 70,
        "recruiter_readability_rationale": "Clear, if slightly dense.",
        "flags": [
            {"title": "Ambiguous narrative", "severity": "orange", "why_it_matters": "Reads as two roles at once.", "recommended_change": "Pick one narrative thread."},
        ],
    }
    monkeypatch.setattr(career_engine, "call_tool", lambda **kwargs: canned)

    result, findings = career_engine.evaluate_positioning("resume text", TargetProfile(), _next_id())

    assert result["role_alignment_score"] == 82
    assert len(findings) == 1
    assert findings[0].category.value == "career_positioning"
    assert findings[0].severity.value == "orange"
    assert findings[0].sources[0].source.startswith("LLM judgment")


def test_aerospace_engine_flags_low_scoring_bullet(monkeypatch):
    from app.aerospace_engine import engine as aerospace_engine

    canned = {
        "bullets": [
            {
                "bullet_text": "Helped with schedule tracking.",
                "ownership_score": 2, "specificity_score": 2, "scope_score": 2,
                "technical_context_score": 2, "metric_strength_score": 1, "outcome_score": 1,
                "weakest_dimension": "metric_strength_score",
                "missing_variable": "schedule recovery amount",
                "rewrite_suggestion": None,
            },
        ],
        "ownership_language_note": "Bullets lean heavily on participation language.",
    }
    monkeypatch.setattr(aerospace_engine, "call_tool", lambda **kwargs: canned)

    text = "- Directed the recovery.\n- Helped with schedule tracking."
    result, findings = aerospace_engine.run_pm_positioning(text, TargetProfile(), _next_id())

    assert result["llm_ran"] is True
    assert len(result["bullets"]) == 1
    low_score_findings = [f for f in findings if f.category.value == "accomplishment_strength"]
    assert len(low_score_findings) == 1
    assert "schedule recovery amount" in low_score_findings[0].recommended_change


def test_jd_matching_builds_requirement_rows(monkeypatch):
    from app.jd_matching import engine as jd_engine

    canned = {
        "requirements": [
            {
                "requirement": "5+ years program management experience",
                "jd_importance": "required",
                "resume_coverage": "strong_match",
                "evidence": "Program Manager, 2019-Present",
                "recommendation": None,
            },
            {
                "requirement": "Security clearance",
                "jd_importance": "preferred",
                "resume_coverage": "missing",
                "evidence": None,
                "recommendation": "Add clearance status if held.",
            },
        ],
        "overall_fit_note": "Strong core PM background; clearance status unclear.",
    }
    monkeypatch.setattr(jd_engine, "call_tool", lambda **kwargs: canned)

    target = TargetProfile(job_description="Looking for a PM with 5+ years experience and a clearance.")
    result = jd_engine.build_requirement_coverage_matrix("resume text", target)

    assert result.status == "computed"
    assert len(result.requirements) == 2
    assert result.requirements[0].resume_coverage == "strong_match"
    assert result.requirements[1].resume_coverage == "missing"


def test_keyword_enrichment_only_accepts_candidate_terms(monkeypatch):
    from app.keyword_engine import matcher

    # Model returns one valid candidate term and one hallucinated term not
    # in the candidate list -- the hallucinated one must be dropped.
    canned = {
        "matches": [
            {"term": "Airframe", "matched_because": "Describes fuselage structural work.", "confidence": "high"},
            {"term": "Not A Real Candidate Term", "matched_because": "should be dropped", "confidence": "high"},
        ]
    }
    monkeypatch.setattr(matcher, "LLM_ENABLED", True)
    monkeypatch.setattr(matcher, "call_tool", lambda **kwargs: canned)

    target = TargetProfile(industry="Aerospace / Defense")
    coverage, findings, relevant = matcher.run_keyword_engine(
        "Managed structural work on fuselage assemblies without naming specific terms.", target, _next_id()
    )

    llm_matches = [m for m in coverage.matched if m.via == "llm_semantic"]
    assert len(llm_matches) == 1
    assert llm_matches[0].term == "Airframe"
    assert coverage.llm_enrichment_ran is True


def test_llm_not_configured_degrades_cleanly():
    """With no ANTHROPIC_API_KEY, career_engine raises LLMNotConfiguredError
    and aerospace_engine's run_pm_positioning degrades to deterministic-only
    without raising -- the two designed degradation paths."""
    from app.career_engine import engine as career_engine
    from app.aerospace_engine import engine as aerospace_engine
    from app.llm.client import LLMNotConfiguredError

    try:
        career_engine.evaluate_positioning("some resume text", TargetProfile(), _next_id())
        assert False, "expected LLMNotConfiguredError"
    except LLMNotConfiguredError:
        pass

    result, findings = aerospace_engine.run_pm_positioning("- Led the program.", TargetProfile(), _next_id())
    assert result["llm_ran"] is False
    assert result["ownership_count"] == 1
