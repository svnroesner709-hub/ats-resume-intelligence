"""
Every score is built from an explicit, named checklist (ScoreCheck) derived
from data already computed elsewhere -- findings, extraction comparison,
keyword matches, contact info, ownership-verb scan, LLM analysis results.
Never a parallel re-implementation that could silently drift from the
actual rule/finding logic that produced the underlying evidence.

Where a score is naturally "percentage of checks passed" (Parsing
Reliability, Structural Compatibility, Keyword Coverage), the shown number
IS that percentage -- so the checklist fully explains the number, per the
explicit request that drove this feature. Where a score is an LLM holistic
judgment (the four LLM-backed scores), the number is the LLM's own 0-100
rating and the checklist shows corroborating verdicts alongside it, not a
formula that produced the number -- that distinction is stated in each
score's explanation so the two kinds of "checklist" are never confused.
"""
from __future__ import annotations

from app.models import (
    ContactInfo,
    ExtractionComparison,
    Finding,
    FindingCategory,
    KeywordCoverageResult,
    ScoreCheck,
    Scores,
    ScoreValue,
    Severity,
    SourceCitation,
    SourceConfidence,
)

_NOT_CONFIGURED_NOTE = "Requires ANTHROPIC_API_KEY in .env -- see .env.example. Phases 1-5 and Keyword Coverage work without it."


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _cite(rule_id: str, claim: str) -> SourceCitation:
    return SourceCitation(
        source="Internal ATS rule heuristic (not yet backed by a fetched citation)",
        confidence=SourceConfidence.E,
        claim=claim,
        supports_rule=rule_id,
    )


def _llm_cite(model: str, claim: str) -> SourceCitation:
    return SourceCitation(
        source=f"LLM judgment (model: {model})",
        confidence=SourceConfidence.E,
        claim=claim,
        supports_rule="llm_judgment",
    )


def _fired(findings: list[Finding], rule_id: str) -> bool:
    return any(s.supports_rule == rule_id for f in findings for s in f.sources)


def _has_title_containing(findings: list[Finding], category: FindingCategory, needle: str) -> bool:
    needle = needle.lower()
    return any(f.category == category and needle in f.title.lower() for f in findings)


def _checks_score(checks: list[ScoreCheck]) -> int:
    if not checks:
        return 100
    return _clamp(100 * sum(1 for c in checks if c.passed) / len(checks))


# ---------------------------------------------------------------------------
# ATS Parsing Reliability
# ---------------------------------------------------------------------------

def compute_parsing_reliability(findings: list[Finding], comparison: ExtractionComparison) -> ScoreValue:
    ok_methods = [m for m in comparison.methods if m.ok]
    checks = [
        ScoreCheck(
            name=f"Extraction methods agree >=90% ({', '.join(m.method for m in comparison.methods)})",
            passed=comparison.agreement_ratio >= 0.9,
            detail=f"{comparison.agreement_ratio * 100:.0f}% pairwise text similarity across {len(ok_methods)} method(s).",
            source=_cite("extraction_disagreement", "Independent-method text disagreement predicts inconsistent results across real ATS platforms."),
        ),
        ScoreCheck(
            name="All extraction methods succeeded",
            passed=len(ok_methods) == len(comparison.methods),
            detail=f"{len(ok_methods)}/{len(comparison.methods)} method(s) completed without error.",
            source=_cite("extraction_disagreement", "A parser that cannot read the file at all is a hard failure signal."),
        ),
        ScoreCheck(
            name="No garbled or undecodable characters",
            passed=not any("unrecognized/undecodable" in d or "control character" in d for d in comparison.divergences),
            detail="No U+FFFD replacement characters or stray control characters found in extracted text.",
            source=_cite("extraction_disagreement", "Garbled characters mean an ATS stores corrupted text for that region."),
        ),
        ScoreCheck(
            name="No method recovered substantially less text than others",
            passed=not any("recovered only" in d for d in comparison.divergences),
            detail="No extraction method returned <50% of the characters another method recovered.",
            source=_cite("extraction_disagreement", "A large char-count gap between methods usually means missing content (image, text box, or a method-specific parsing failure)."),
        ),
        ScoreCheck(
            name="No page without an extractable text layer",
            passed=not any(f.category == FindingCategory.PARSING and "no extractable text layer" in f.title.lower() for f in findings),
            detail="No page detected as image-only/scanned with zero underlying text.",
            source=_cite("image_only_page", "A page with no text layer cannot be read by any text-based ATS parser at all."),
        ),
    ]
    score = _checks_score(checks)
    return ScoreValue(
        value=score,
        label="ATS Parsing Reliability",
        status="computed",
        explanation=f"Percentage of {len(checks)} named parsing checks passed (see checklist) -- this number IS the pass rate, not a separate formula.",
        checks=checks,
    )


# ---------------------------------------------------------------------------
# ATS Structural Compatibility
# ---------------------------------------------------------------------------

def compute_structural_compatibility(findings: list[Finding], contact: ContactInfo) -> ScoreValue:
    checks = [
        ScoreCheck(
            name="Single-column layout",
            passed=not _fired(findings, "multi_column"),
            detail="No multi-column layout detected." if not _fired(findings, "multi_column") else "Multi-column layout detected -- see finding.",
            source=_cite("multi_column", "Some ATS parsers read across columns rather than down them, scrambling reading order."),
        ),
        ScoreCheck(
            name="No tables in resume body",
            passed=not _fired(findings, "tables"),
            detail="No table detected." if not _fired(findings, "tables") else "One or more tables detected -- see finding.",
            source=_cite("tables", "Tabular layouts are inconsistently parsed by some ATS configurations."),
        ),
        ScoreCheck(
            name="No content outside normal text flow (text boxes)",
            passed=not _fired(findings, "text_boxes"),
            detail="No text-box content detected." if not _fired(findings, "text_boxes") else "Content found in a text box -- see finding.",
            source=_cite("text_boxes", "Text-box content sits outside the normal document flow most parsers read."),
        ),
        ScoreCheck(
            name="No hidden or white-on-white text",
            passed=not _fired(findings, "hidden_text"),
            detail="No hidden/white text detected." if not _fired(findings, "hidden_text") else "Hidden or white-on-white text detected -- see finding.",
            source=_cite("hidden_text", "Hidden text reads as an attempt to game keyword matching."),
        ),
        ScoreCheck(
            name="Standard/recognized font family used",
            passed=not _fired(findings, "uncommon_font"),
            detail="All fonts on the recognized safe list." if not _fired(findings, "uncommon_font") else "Uncommon font(s) detected -- see finding.",
            source=_cite("uncommon_font", "Uncommon fonts occasionally substitute or extract poorly in some converters."),
        ),
        ScoreCheck(
            name="Contact info present in main body (not header/footer only)",
            passed=not contact.found_in_header_or_footer,
            detail="Contact info found in the main body." if not contact.found_in_header_or_footer else "Contact info found only in a header/footer region -- see finding.",
            source=_cite("header_footer_contact", "Some ATS parsers skip header/footer regions entirely."),
        ),
        ScoreCheck(
            name="Email address extracted",
            passed=contact.email is not None,
            detail=f"Email: {contact.email}" if contact.email else "No email address could be extracted.",
            source=_cite("missing_contact_field", "Most ATS platforms build the candidate record from parsed contact fields."),
        ),
        ScoreCheck(
            name="Phone number extracted",
            passed=contact.phone is not None,
            detail=f"Phone: {contact.phone}" if contact.phone else "No phone number could be extracted.",
            source=_cite("missing_contact_field", "Most ATS platforms build the candidate record from parsed contact fields."),
        ),
        ScoreCheck(
            name="'Experience' section heading present",
            passed=not _has_title_containing(findings, FindingCategory.SECTION_ARCHITECTURE, "experience"),
            detail="Heading detected." if not _has_title_containing(findings, FindingCategory.SECTION_ARCHITECTURE, "experience") else "No clearly labeled Experience heading detected.",
            source=_cite("missing_section_heading", "ATS platforms often bucket content into fields using recognized section headings."),
        ),
        ScoreCheck(
            name="'Education' section heading present",
            passed=not _has_title_containing(findings, FindingCategory.SECTION_ARCHITECTURE, "education"),
            detail="Heading detected." if not _has_title_containing(findings, FindingCategory.SECTION_ARCHITECTURE, "education") else "No clearly labeled Education heading detected.",
            source=_cite("missing_section_heading", "ATS platforms often bucket content into fields using recognized section headings."),
        ),
        ScoreCheck(
            name="'Skills' section heading present",
            passed=not _has_title_containing(findings, FindingCategory.SECTION_ARCHITECTURE, "skills"),
            detail="Heading detected." if not _has_title_containing(findings, FindingCategory.SECTION_ARCHITECTURE, "skills") else "No clearly labeled Skills heading detected.",
            source=_cite("missing_section_heading", "ATS platforms often bucket content into fields using recognized section headings."),
        ),
    ]
    score = _checks_score(checks)
    return ScoreValue(
        value=score,
        label="ATS Structural Compatibility",
        status="computed",
        explanation=f"Percentage of {len(checks)} named structural checks passed (see checklist) -- this number IS the pass rate, not a separate formula.",
        checks=checks,
    )


# ---------------------------------------------------------------------------
# Aerospace Keyword Coverage (deterministic, always computed)
# ---------------------------------------------------------------------------

def compute_keyword_coverage(coverage: KeywordCoverageResult, relevant_keys: set[str]) -> ScoreValue:
    relevant = [c for c in coverage.categories if c.category in relevant_keys] or coverage.categories
    checks = [
        ScoreCheck(
            name=f"{c.label} terminology present",
            passed=c.coverage_ratio >= 0.15,
            detail=f"{c.matched_terms}/{c.total_terms} tracked terms matched ({c.coverage_ratio * 100:.0f}%).",
            source=_cite("keyword_coverage", "Coverage against a curated aerospace/defense/PM/manufacturing/certification/government-contracting term database."),
        )
        for c in relevant
    ]
    score = _clamp(100 * sum(c.coverage_ratio for c in relevant) / len(relevant)) if relevant else None
    enrichment_note = " Includes an LLM semantic-enrichment pass." if coverage.llm_enrichment_ran else " Dictionary matching only (LLM enrichment not run)."
    return ScoreValue(
        value=score,
        label="Aerospace Keyword Coverage",
        status="computed",
        explanation=(
            f"Average term-coverage ratio across {len(relevant)} domain categor{'y' if len(relevant) == 1 else 'ies'} "
            f"relevant to the stated target/industry.{enrichment_note} A low score means the resume doesn't name much "
            f"domain terminology explicitly -- not that the underlying experience is weak."
        ),
        checks=checks,
    )


# ---------------------------------------------------------------------------
# Program Management Positioning (deterministic ownership scan, +LLM depth)
# ---------------------------------------------------------------------------

def compute_pm_positioning(pm_data: dict) -> ScoreValue:
    ratio = pm_data.get("ownership_ratio")
    if ratio is None and not pm_data.get("llm_ran"):
        return ScoreValue(value=None, label="Program Management Positioning", status="not yet implemented",
                           explanation="No bullet-style lines were detected to scan for ownership language.")

    checks = []
    if ratio is not None:
        checks.append(
            ScoreCheck(
                name="More ownership language than weak-participation language",
                passed=ratio > 0.5,
                detail=f"{pm_data['ownership_count']} ownership-verb line(s) vs. {pm_data['weak_count']} weak-participation line(s) ({ratio * 100:.0f}% ownership).",
                source=_cite("ownership_language_scan", "Program-management resumes should show ownership of outcomes, not just participation."),
            )
        )

    bullets = pm_data.get("bullets") or []
    llm_component = None
    if pm_data.get("llm_ran") and bullets:
        avgs = []
        for b in bullets:
            dims = [b.get(k, 0) for k in ("ownership_score", "specificity_score", "scope_score", "technical_context_score", "metric_strength_score", "outcome_score")]
            avgs.append(sum(dims) / len(dims))
        llm_component = sum(avgs) / len(avgs) * 10  # 0-10 -> 0-100
        checks.append(
            ScoreCheck(
                name="Bullets show strong Action+Scope+Technical Context+Result (LLM-scored)",
                passed=llm_component >= 60,
                detail=f"Averaged {llm_component / 10:.1f}/10 across {len(bullets)} scored bullet(s).",
                source=SourceCitation(source="LLM judgment", confidence=SourceConfidence.E, claim="Per-bullet quality scoring.", supports_rule="llm_judgment"),
            )
        )

    if ratio is not None and llm_component is not None:
        score = _clamp((ratio * 100 + llm_component) / 2)
        explanation = "Average of the deterministic ownership-language ratio and the LLM's per-bullet quality scoring."
    elif llm_component is not None:
        score = _clamp(llm_component)
        explanation = "LLM per-bullet quality scoring (no bullet-style lines found for the deterministic verb scan)."
    else:
        score = _clamp(ratio * 100)
        explanation = "Deterministic ownership-vs-weak-participation verb ratio only (set ANTHROPIC_API_KEY for LLM-scored bullet depth)."

    return ScoreValue(value=score, label="Program Management Positioning", status="computed", explanation=explanation, checks=checks)


# ---------------------------------------------------------------------------
# Target Role Alignment (deterministic role-taxonomy fit, +LLM narrative)
# ---------------------------------------------------------------------------

def compute_target_role_alignment(
    role_alignment_data: dict | None, positioning_result: dict | None, positioning_error: str | None, model: str
) -> ScoreValue:
    checks: list[ScoreCheck] = []
    det_score = None
    llm_score = None

    if role_alignment_data:
        det_score = role_alignment_data["score"]
        checks.append(
            ScoreCheck(
                name=f"Signature terms for '{role_alignment_data['matched_role_label']}' present",
                passed=role_alignment_data["signature_ratio"] >= 0.5,
                detail=(
                    f"{len(role_alignment_data['signature_hits'])}/"
                    f"{len(role_alignment_data['signature_hits']) + len(role_alignment_data['signature_missing'])} "
                    f"signature terms matched."
                ),
                source=_cite("role_taxonomy_alignment", f"Terms characteristic of a {role_alignment_data['matched_role_label']} resume."),
            )
        )
        checks.append(
            ScoreCheck(
                name=f"Domain-category mix fits '{role_alignment_data['matched_role_label']}'",
                passed=role_alignment_data["category_fit"] >= 0.15,
                detail=f"Weighted category coverage fit: {role_alignment_data['category_fit'] * 100:.0f}%.",
                source=_cite("role_taxonomy_alignment", "Weighted mix of keyword-database categories expected for this role."),
            )
        )

    if positioning_result:
        llm_score = positioning_result.get("role_alignment_score", 0)
        checks.append(
            ScoreCheck(
                name="Implied role matches target (LLM judgment)",
                passed=llm_score >= 70,
                detail=f"Implied role: {positioning_result.get('implied_role', 'unclear')}.",
                source=_llm_cite(model, "Implied-role classification vs. target."),
            )
        )

    if det_score is None and llm_score is None:
        status = "llm_error" if positioning_error else "not yet implemented"
        explanation = positioning_error or (
            "Enter a Target Role (e.g. 'Technical Program Manager') for deterministic role-fit scoring -- free, no "
            "API key needed -- and/or set ANTHROPIC_API_KEY for qualitative narrative judgment too."
        )
        return ScoreValue(value=None, label="Target Role Alignment", status=status, explanation=explanation)

    if det_score is not None and llm_score is not None:
        score = _clamp((det_score + llm_score) / 2)
        explanation = (
            f"Average of deterministic terminology fit against the '{role_alignment_data['matched_role_label']}' "
            f"profile and the LLM's qualitative role-alignment judgment."
        )
    elif det_score is not None:
        score = det_score
        explanation = (
            f"Deterministic terminology fit against the '{role_alignment_data['matched_role_label']}' profile only "
            f"(set ANTHROPIC_API_KEY for qualitative narrative judgment too)."
        )
    else:
        score = _clamp(llm_score)
        explanation = positioning_result.get("role_alignment_rationale", "")

    return ScoreValue(value=score, label="Target Role Alignment", status="computed", explanation=explanation, checks=checks)


# ---------------------------------------------------------------------------
# Recruiter Readability (deterministic bullshit/redundancy detectors, +LLM)
# ---------------------------------------------------------------------------

def compute_recruiter_readability(
    readability_data: dict, positioning_result: dict | None, positioning_error: str | None, model: str
) -> ScoreValue:
    buzzword_hits = readability_data["buzzword_hits"]
    redundant_verbs = readability_data["redundant_verbs"]

    penalty = min(50, len(buzzword_hits) * 10) + min(30, len(redundant_verbs) * 15)
    det_score = _clamp(100 - penalty)

    checks = [
        ScoreCheck(
            name="No generic corporate filler phrases without supporting evidence",
            passed=len(buzzword_hits) == 0,
            detail=(
                "None found." if not buzzword_hits
                else f"{len(buzzword_hits)} found, e.g. \"{buzzword_hits[0]['phrase']}\"."
            ),
            source=_cite("bullshit_detector", "Generic corporate phrasing without concrete evidence reads as filler, not a substantive claim."),
        ),
        ScoreCheck(
            name="No single verb overused across bullets",
            passed=len(redundant_verbs) == 0,
            detail=(
                "Good verb variety." if not redundant_verbs
                else f"'{redundant_verbs[0]['verb']}' used {redundant_verbs[0]['count']} times."
            ),
            source=_cite("redundancy_detector", "A single generic verb repeated many times reads as low-effort and obscures which accomplishments actually differ."),
        ),
    ]

    llm_score = None
    if positioning_result:
        llm_score = positioning_result.get("recruiter_readability_score", 0)
        checks.append(
            ScoreCheck(
                name="Narrative answers 'what does this person do?' in one clear read (LLM judgment)",
                passed=bool(positioning_result.get("narrative_sentence")),
                detail=positioning_result.get("narrative_sentence", ""),
                source=_llm_cite(model, "One-sentence narrative extraction."),
            )
        )

    if llm_score is not None:
        score = _clamp((det_score + llm_score) / 2)
        explanation = "Average of deterministic filler/redundancy scanning and the LLM's holistic readability judgment."
    else:
        score = det_score
        explanation = "Deterministic filler/redundancy scanning only (set ANTHROPIC_API_KEY for holistic narrative-clarity judgment too)."
        if positioning_error:
            explanation += f" LLM pass attempted but failed: {positioning_error}"

    return ScoreValue(value=score, label="Recruiter Readability", status="computed", explanation=explanation, checks=checks)


def _llm_gated_score(label: str, positioning_result: dict | None, positioning_error: str | None,
                      value_key: str, rationale_key: str, extra_checks: list[ScoreCheck]) -> ScoreValue:
    if positioning_result is None:
        status = "llm_error" if positioning_error else "not yet implemented"
        return ScoreValue(value=None, label=label, status=status, explanation=positioning_error or _NOT_CONFIGURED_NOTE)
    return ScoreValue(
        value=_clamp(positioning_result.get(value_key, 0)),
        label=label,
        status="computed",
        explanation=positioning_result.get(rationale_key, ""),
        checks=extra_checks,
    )


def compute_seniority_signal(positioning_result: dict | None, positioning_error: str | None, model: str) -> ScoreValue:
    checks = []
    if positioning_result:
        checks.append(ScoreCheck(
            name="Wording calibrated to demonstrated scope (neither undersold nor oversold)",
            passed=positioning_result.get("seniority_calibration") == "matches",
            detail=f"Calibration verdict: {positioning_result.get('seniority_calibration', 'unclear')}.",
            source=_llm_cite(model, "Seniority calibration judgment."),
        ))
    return _llm_gated_score("Executive/Seniority Signal", positioning_result, positioning_error, "seniority_score", "seniority_rationale", checks)


def compute_overall(scores: dict[str, ScoreValue]) -> ScoreValue:
    computed = {k: v for k, v in scores.items() if v.status == "computed" and v.value is not None}
    if not computed:
        return ScoreValue(value=None, label="Overall Resume Strength", status="not yet implemented", explanation=_NOT_CONFIGURED_NOTE)
    avg = sum(v.value for v in computed.values()) / len(computed)
    return ScoreValue(
        value=_clamp(avg),
        label="Overall Resume Strength",
        status="computed",
        explanation=(
            f"Unweighted average of {len(computed)}/{len(scores)} sub-scores currently computed "
            f"({', '.join(v.label for v in computed.values())}). A diagnostic index, not a precise measurement -- "
            f"and it understates completeness while any sub-scores remain unconfigured."
        ),
    )


def compute_scores(
    findings: list[Finding],
    comparison: ExtractionComparison,
    contact: ContactInfo,
    keyword_coverage: KeywordCoverageResult,
    relevant_keyword_categories: set[str],
    pm_positioning_data: dict,
    role_alignment_data: dict | None,
    readability_data: dict,
    positioning_result: dict | None,
    positioning_error: str | None,
    llm_model: str,
) -> Scores:
    parsing = compute_parsing_reliability(findings, comparison)
    structural = compute_structural_compatibility(findings, contact)
    keyword = compute_keyword_coverage(keyword_coverage, relevant_keyword_categories)
    pm_positioning = compute_pm_positioning(pm_positioning_data)
    role_alignment = compute_target_role_alignment(role_alignment_data, positioning_result, positioning_error, llm_model)
    readability = compute_recruiter_readability(readability_data, positioning_result, positioning_error, llm_model)
    seniority = compute_seniority_signal(positioning_result, positioning_error, llm_model)

    partial = {
        "ats_parsing_reliability": parsing,
        "ats_structural_compatibility": structural,
        "target_role_alignment": role_alignment,
        "aerospace_keyword_coverage": keyword,
        "program_management_positioning": pm_positioning,
        "recruiter_readability": readability,
        "executive_seniority_signal": seniority,
    }
    overall = compute_overall(partial)

    return Scores(**partial, overall_resume_strength=overall)
