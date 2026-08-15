"""
Phase 5 scoring: only the two scores actually backed by implemented
engines (ATS Parsing Reliability, ATS Structural Compatibility) get a real
number. Everything else is explicitly marked "not yet implemented" --
never a plausible-looking placeholder number. See models.ScoreValue.
"""
from __future__ import annotations

from app.models import ExtractionComparison, Finding, FindingCategory, Scores, ScoreValue, Severity

_NOT_IMPLEMENTED_NOTE = "Requires career_engine/aerospace_engine/keyword_engine, which are scaffolded but not yet implemented (see README phase status)."


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def compute_parsing_reliability(findings: list[Finding], comparison: ExtractionComparison) -> ScoreValue:
    score = comparison.agreement_ratio * 100
    parsing_findings = [f for f in findings if f.category == FindingCategory.PARSING]
    for f in parsing_findings:
        if f.severity == Severity.RED:
            score -= 15
        elif f.severity == Severity.ORANGE:
            score -= 5
    score = _clamp(score)
    return ScoreValue(
        value=score,
        label="ATS Parsing Reliability",
        status="computed",
        explanation=(
            f"Based on {len(comparison.methods)}-method extraction agreement "
            f"({comparison.agreement_ratio * 100:.0f}%) and {len(parsing_findings)} parsing finding(s)."
        ),
    )


def compute_structural_compatibility(findings: list[Finding]) -> ScoreValue:
    relevant_categories = {
        FindingCategory.STRUCTURE,
        FindingCategory.CONTACT_INFO,
        FindingCategory.SECTION_ARCHITECTURE,
        FindingCategory.TYPOGRAPHY,
        FindingCategory.MICRO_FORMATTING,
    }
    relevant = [f for f in findings if f.category in relevant_categories]
    score = 100.0
    for f in relevant:
        if f.severity == Severity.RED:
            score -= 25
        elif f.severity == Severity.ORANGE:
            score -= 10
        elif f.severity == Severity.YELLOW:
            score -= 3
    score = _clamp(score)
    return ScoreValue(
        value=score,
        label="ATS Structural Compatibility",
        status="computed",
        explanation=f"Based on {len(relevant)} structural/contact/section finding(s) across the document.",
    )


def _not_implemented(label: str) -> ScoreValue:
    return ScoreValue(value=None, label=label, status="not yet implemented", explanation=_NOT_IMPLEMENTED_NOTE)


def compute_scores(findings: list[Finding], comparison: ExtractionComparison) -> Scores:
    parsing = compute_parsing_reliability(findings, comparison)
    structural = compute_structural_compatibility(findings)
    return Scores(
        ats_parsing_reliability=parsing,
        ats_structural_compatibility=structural,
        target_role_alignment=_not_implemented("Target Role Alignment"),
        aerospace_keyword_coverage=_not_implemented("Aerospace Keyword Coverage"),
        program_management_positioning=_not_implemented("Program Management Positioning"),
        recruiter_readability=_not_implemented("Recruiter Readability"),
        executive_seniority_signal=_not_implemented("Executive/Seniority Signal"),
        # "Overall" is only meaningful once the career/keyword engines exist;
        # a partial average would misleadingly look like a real composite.
        overall_resume_strength=_not_implemented("Overall Resume Strength"),
    )
