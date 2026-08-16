"""
Deterministic half of Target Role Alignment. Works with NO API key and
NO job description -- just a free-text Target Role field (e.g. "Technical
Program Manager") -- so this is real, immediate feedback on how the
resume's terminology profile matches a named target role, always
available. app/career_engine/engine.py's LLM call adds qualitative
narrative judgment (what role the resume *currently* reads as, vs. the
target) on top when configured.

Explicitly designed around the fact that a target role is often different
from the candidate's current/implied role -- this scores fit against the
*target*'s expected profile and surfaces the specific gap terms, which is
tailoring guidance, not a verdict on the candidate's current trajectory.
"""
from __future__ import annotations

from app.knowledge_base.loader import RoleProfile, role_taxonomy
from app.models import (
    Finding,
    FindingCategory,
    KeywordCoverageResult,
    PriorityBucket,
    RiskClassification,
    Severity,
    SourceCitation,
    SourceConfidence,
)

_SIGNATURE_WEIGHT = 0.6  # signature terms are more diagnostic than general category density
_CATEGORY_WEIGHT = 0.4


def match_role_profile(target_role_text: str | None) -> RoleProfile | None:
    """Best-effort alias match. Exact alias match wins; otherwise the
    longest alias that appears in (or contains) the input text wins, so
    'Senior Technical Program Manager' still matches the 'technical
    program manager' alias."""
    if not target_role_text or not target_role_text.strip():
        return None
    text = target_role_text.lower().strip()

    best: RoleProfile | None = None
    best_len = 0
    for profile in role_taxonomy():
        for alias in profile.aliases:
            if alias == text:
                return profile
            if (alias in text or text in alias) and len(alias) > best_len:
                best = profile
                best_len = len(alias)
    return best


def _citation(profile_label: str) -> list[SourceCitation]:
    return [
        SourceCitation(
            source="Internal role-taxonomy heuristic (Level E, not yet backed by a fetched citation)",
            confidence=SourceConfidence.E,
            claim=f"Expected terminology profile for '{profile_label}', compiled from domain knowledge.",
            supports_rule="role_taxonomy_alignment",
        )
    ]


def compute_role_alignment(
    coverage: KeywordCoverageResult, target_role_text: str | None, next_id
) -> tuple[dict | None, list[Finding]]:
    profile = match_role_profile(target_role_text)
    if profile is None:
        return None, []

    matched_terms = {m.term for m in coverage.matched}
    coverage_by_cat = {c.category: c.coverage_ratio for c in coverage.categories}

    weighted_sum = sum(coverage_by_cat.get(cat, 0.0) * w for cat, w in profile.category_weights.items())
    weight_total = sum(profile.category_weights.values()) or 1.0
    category_fit = weighted_sum / weight_total

    signature_hits = [t for t in profile.signature_terms if t in matched_terms]
    signature_missing = [t for t in profile.signature_terms if t not in matched_terms]
    signature_ratio = (len(signature_hits) / len(profile.signature_terms)) if profile.signature_terms else 0.0

    score = round(100 * (_CATEGORY_WEIGHT * category_fit + _SIGNATURE_WEIGHT * signature_ratio))

    findings: list[Finding] = []
    if signature_missing:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.CAREER_POSITIONING,
                classification=RiskClassification.POSITIONING_OPPORTUNITY,
                severity=Severity.YELLOW if signature_ratio >= 0.3 else Severity.ORANGE,
                title=f"Missing terminology commonly expected for {profile.label}",
                description=(
                    f"{len(signature_missing)} of {len(profile.signature_terms)} signature terms for "
                    f"'{profile.label}' weren't found: {', '.join(signature_missing)}."
                ),
                why_it_matters=(
                    f"Resumes targeting {profile.label} roles typically name these concepts explicitly. A target "
                    f"role is often different from your current role -- this isn't a judgment on your background, "
                    f"it's guidance on how to describe genuinely-held experience in the language this target role expects."
                ),
                ats_evidence=f"{len(signature_hits)}/{len(profile.signature_terms)} signature terms matched via the keyword engine.",
                recruiter_impact="A recruiter scanning specifically for this role may not register relevant experience that isn't described in its expected terms.",
                recommended_change=(
                    f"If genuinely applicable to your experience, name these explicitly rather than only describing "
                    f"the work generically: {', '.join(signature_missing[:6])}."
                ),
                confidence=SourceConfidence.E,
                sources=_citation(profile.label),
                priority=PriorityBucket.STRONGLY_RECOMMENDED if signature_ratio < 0.3 else PriorityBucket.OPTIONAL_POLISH,
            )
        )

    result = {
        "matched_role_key": profile.key,
        "matched_role_label": profile.label,
        "category_fit": round(category_fit, 3),
        "signature_hits": signature_hits,
        "signature_missing": signature_missing,
        "signature_ratio": round(signature_ratio, 3),
        "score": score,
    }
    return result, findings
