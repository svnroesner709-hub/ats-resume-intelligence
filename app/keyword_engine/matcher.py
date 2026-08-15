"""
Phase 8 core: deterministic keyword coverage matching against the large
domain database in app/knowledge_base/keywords/, plus an optional LLM
semantic-enrichment pass for near-misses the dictionary can't catch
(spec Layer 9: "not simplistic keyword counting... semantic equivalents").

Deterministic matching always runs (no API key needed) and is the primary
signal. LLM enrichment is additive and clearly tagged `via: "llm_semantic"`
so it's never confused with an actual dictionary hit in the evidence shown
to the user.
"""
from __future__ import annotations

import re

from app.config import LLM_ENABLED
from app.knowledge_base.loader import KeywordCategory, keyword_database
from app.llm.client import LLMCallError, LLMNotConfiguredError, call_tool
from app.llm.schemas import SEMANTIC_KEYWORD_ENRICHMENT_SCHEMA
from app.models import (
    CategoryCoverage,
    Finding,
    FindingCategory,
    KeywordCoverageResult,
    MatchedKeyword,
    PriorityBucket,
    RiskClassification,
    Severity,
    SourceCitation,
    SourceConfidence,
    TargetProfile,
)

# Categories whose keywords in `industry`/`career_path` mark them "relevant"
# to a given target profile. Falls back to ALL categories (general domain
# density) when the user supplied no target info at all.
_RELEVANCE_HINTS = {
    "aerospace_defense": ["aerospace", "defense", "space", "aviation", "avionics"],
    "program_management": ["program management", "project management", "pm", "technical program"],
    "manufacturing_quality": ["manufacturing", "production", "quality", "operations"],
    "systems_engineering_certification": ["systems engineering", "certification", "test", "engineering"],
    "government_contracting": ["government", "contracting", "defense", "dod", "federal"],
    "tools_systems": [],  # never a primary "relevant" category on its own
}

_MAX_ENRICHMENT_CANDIDATES = 30
_MAX_NOTABLE_MISSING = 15


def relevant_category_keys(target: TargetProfile) -> set[str]:
    haystack = " ".join(
        filter(None, [target.industry, target.career_path, target.target_role, target.background_notes])
    ).lower()
    if not haystack.strip():
        return {c.key for c in keyword_database()}  # no target info -> general density across everything

    relevant = set()
    for key, hints in _RELEVANCE_HINTS.items():
        if any(h in haystack for h in hints):
            relevant.add(key)
    # Always include PM + aerospace/defense as a sane floor for this tool's domain,
    # even if the free-text target fields didn't happen to use those exact words.
    relevant.update({"program_management", "aerospace_defense"})
    return relevant


def _term_pattern(form: str, case_sensitive: bool) -> re.Pattern:
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(r"\b" + re.escape(form) + r"\b", flags)


def _forms_to_check(term) -> list[tuple[str, bool]]:
    """Returns (form, case_sensitive) pairs. Abbreviations are matched
    case-SENSITIVELY: short acronyms like "TO" (Task order), "SE" (Systems
    Engineering), or "CM" (Configuration Management) are common English
    words when lowercased, so case-insensitive matching produced false
    positives (e.g. "to" inside an ordinary sentence). Full terms/synonyms
    are distinctive multi-word phrases, so case-insensitive matching there
    is safe and desirable."""
    forms = [(term.term, False)] + [(s, False) for s in term.synonyms]
    forms += [(a, True) for a in term.abbreviations]
    return forms


def _dictionary_match(full_text: str, categories: tuple[KeywordCategory, ...]) -> tuple[list[MatchedKeyword], dict[str, list[str]]]:
    matched: list[MatchedKeyword] = []
    unmatched_by_category: dict[str, list[str]] = {}

    for cat in categories:
        unmatched_terms = []
        for term in cat.terms:
            hit_form = None
            for form, case_sensitive in _forms_to_check(term):
                if _term_pattern(form, case_sensitive).search(full_text):
                    hit_form = form
                    break
            if hit_form:
                matched.append(
                    MatchedKeyword(
                        term=term.term,
                        category=cat.key,
                        category_label=cat.label,
                        matched_form=hit_form,
                        via="dictionary",
                        confidence=SourceConfidence.E,
                    )
                )
            else:
                unmatched_terms.append(term.term)
        unmatched_by_category[cat.key] = unmatched_terms

    return matched, unmatched_by_category


def _try_llm_enrichment(full_text: str, unmatched_by_category: dict[str, list[str]], relevant_keys: set[str]) -> list[MatchedKeyword]:
    candidates = []
    for key in relevant_keys:
        candidates.extend(unmatched_by_category.get(key, []))
    candidates = candidates[:_MAX_ENRICHMENT_CANDIDATES]
    if not candidates:
        return []

    system = (
        "You are assisting a deterministic ATS resume-analysis tool. You will be given resume text and a list of "
        "candidate domain terms that did NOT appear verbatim (or as a known abbreviation/synonym) in the resume. "
        "Identify ONLY cases where the resume text clearly, specifically implies that exact concept -- do not guess "
        "or infer generously. It is correct and expected to return few or zero matches if the resume doesn't "
        "genuinely support them. Never invent a term that isn't in the candidate list."
    )
    user_content = (
        f"Candidate terms (only match from this exact list):\n{', '.join(candidates)}\n\n"
        f"Resume text:\n{full_text[:8000]}"
    )

    try:
        result = call_tool(
            system=system,
            user_content=user_content,
            tool_name=SEMANTIC_KEYWORD_ENRICHMENT_SCHEMA["name"],
            tool_description=SEMANTIC_KEYWORD_ENRICHMENT_SCHEMA["description"],
            input_schema=SEMANTIC_KEYWORD_ENRICHMENT_SCHEMA["input_schema"],
            max_tokens=1500,
        )
    except (LLMNotConfiguredError, LLMCallError):
        return []

    candidates_lower = {c.lower(): c for c in candidates}
    term_to_category = {
        term: (cat.key, cat.label)
        for cat in keyword_database()
        for term in [t.term for t in cat.terms]
    }

    enriched: list[MatchedKeyword] = []
    for m in result.get("matches", []):
        term_raw = str(m.get("term", ""))
        canonical = candidates_lower.get(term_raw.lower())
        if not canonical or canonical not in term_to_category:
            continue  # guard against the model returning a term outside the candidate list
        cat_key, cat_label = term_to_category[canonical]
        enriched.append(
            MatchedKeyword(
                term=canonical,
                category=cat_key,
                category_label=cat_label,
                matched_form=str(m.get("matched_because", ""))[:200],
                via="llm_semantic",
                confidence=SourceConfidence.E,
            )
        )
    return enriched


def run_keyword_engine(full_text: str, target: TargetProfile, next_id) -> tuple[KeywordCoverageResult, list[Finding], set[str]]:
    categories = keyword_database()
    relevant_keys = relevant_category_keys(target)

    matched, unmatched_by_category = _dictionary_match(full_text, categories)

    llm_ran = False
    if LLM_ENABLED:
        enriched = _try_llm_enrichment(full_text, unmatched_by_category, relevant_keys)
        if enriched:
            llm_ran = True
            matched_terms_set = {(m.term, m.category) for m in matched}
            for e in enriched:
                if (e.term, e.category) not in matched_terms_set:
                    matched.append(e)
                    matched_terms_set.add((e.term, e.category))

    matched_by_category: dict[str, set[str]] = {}
    for m in matched:
        matched_by_category.setdefault(m.category, set()).add(m.term)

    category_coverage: list[CategoryCoverage] = []
    for cat in categories:
        total = len(cat.terms)
        matched_count = len(matched_by_category.get(cat.key, set()))
        ratio = (matched_count / total) if total else 0.0
        category_coverage.append(
            CategoryCoverage(category=cat.key, label=cat.label, total_terms=total, matched_terms=matched_count, coverage_ratio=round(ratio, 3))
        )

    notable_missing: list[str] = []
    for cat in categories:
        if cat.key not in relevant_keys:
            continue
        matched_terms_here = matched_by_category.get(cat.key, set())
        for term in cat.terms:
            if term.term not in matched_terms_here:
                notable_missing.append(term.term)
            if len(notable_missing) >= _MAX_NOTABLE_MISSING:
                break
        if len(notable_missing) >= _MAX_NOTABLE_MISSING:
            break

    coverage_result = KeywordCoverageResult(
        matched=matched,
        notable_missing=notable_missing,
        categories=category_coverage,
        llm_enrichment_ran=llm_ran,
    )

    findings = _build_findings(coverage_result, relevant_keys, next_id)
    return coverage_result, findings, relevant_keys


def _build_findings(coverage: KeywordCoverageResult, relevant_keys: set[str], next_id) -> list[Finding]:
    findings: list[Finding] = []
    source = [
        SourceCitation(
            source="Internal keyword-database heuristic (Level E, not yet backed by a fetched citation)",
            confidence=SourceConfidence.E,
            claim="Coverage against a curated aerospace/defense/PM/manufacturing/certification/government-contracting term database.",
            supports_rule="keyword_coverage",
        )
    ]

    for cat in coverage.categories:
        if cat.category not in relevant_keys:
            continue
        if cat.coverage_ratio < 0.1 and cat.total_terms >= 15:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.KEYWORD_MATCH,
                    classification=RiskClassification.POSITIONING_OPPORTUNITY,
                    severity=Severity.YELLOW,
                    title=f"Little {cat.label} terminology detected",
                    description=(
                        f"Only {cat.matched_terms} of {cat.total_terms} tracked {cat.label} terms were found "
                        f"(dictionary + semantic match combined)."
                    ),
                    why_it_matters="Recruiters and some ATS keyword filters scan for domain-specific terminology; genuinely-held experience that isn't named explicitly may not register.",
                    ats_evidence=f"{cat.matched_terms}/{cat.total_terms} terms matched in category '{cat.label}'.",
                    recruiter_impact="A resume light on named domain terminology can read as less technically specific, even when the underlying experience is strong.",
                    recommended_change=f"If genuinely applicable, name specific {cat.label.lower()} terms/tools/standards explicitly rather than only describing the work generically.",
                    confidence=SourceConfidence.E,
                    sources=source,
                    priority=PriorityBucket.OPTIONAL_POLISH,
                )
            )
    return findings
