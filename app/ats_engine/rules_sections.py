"""
Layer 4 rules (structural half only -- section *presence/labeling*, not
the Layer 4 "does this section add value" judgment call, which belongs to
the not-yet-implemented career_engine).

Only flags Experience/Education/Skills as expected-by-default since those
three are close to universal for a resume at any seniority. Summary is
deliberately NOT flagged as missing -- the spec is explicit that a summary
should never be auto-recommended without judging whether the candidate's
narrative actually benefits from one, which is career_engine's job.
"""
from __future__ import annotations

import statistics

from app.ats_engine.context import AnalysisContext
from app.knowledge_base.loader import section_heading_variants, structural_rule_meta
from app.models import (
    Finding,
    FindingCategory,
    PriorityBucket,
    RiskClassification,
    Severity,
    SourceCitation,
    SourceConfidence,
)

_REQUIRED_BY_DEFAULT = ["experience", "education", "skills"]


def _citation(rule_id: str) -> list[SourceCitation]:
    meta = structural_rule_meta(rule_id)
    return [
        SourceCitation(
            source="Internal ATS rule heuristic (not yet backed by a fetched citation)",
            confidence=SourceConfidence(meta.get("confidence", "E")),
            claim=meta.get("why_it_matters", ""),
            supports_rule=rule_id,
        )
    ]


def _heading_candidates_docx(ctx: AnalysisContext) -> list[str]:
    candidates = []
    for p in ctx.docx.paragraphs:
        word_count = len(p.text.split())
        if p.is_heading:
            candidates.append(p.text)
        elif word_count <= 4 and p.text.isupper():
            candidates.append(p.text)
    return candidates


def _heading_candidates_pdf(ctx: AnalysisContext) -> list[str]:
    all_sizes = [
        size
        for page in ctx.pymupdf.pages
        for block in page.blocks
        for size in block.font_sizes
    ]
    if not all_sizes:
        return []
    median_size = statistics.median(all_sizes)

    candidates = []
    for page in ctx.pymupdf.pages:
        for block in page.blocks:
            text = block.text.strip()
            word_count = len(text.split())
            if word_count == 0 or word_count > 6:
                continue
            max_size = max(block.font_sizes) if block.font_sizes else 0
            looks_like_heading = max_size >= median_size * 1.15 or (block.is_bold and text.isupper())
            if looks_like_heading:
                candidates.append(text)
    return candidates


def rule_section_headings(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []

    if ctx.file_type == "docx" and ctx.docx is not None:
        candidates = _heading_candidates_docx(ctx)
    elif ctx.file_type == "pdf" and ctx.pymupdf is not None:
        candidates = _heading_candidates_pdf(ctx)
    else:
        candidates = []

    candidates_lower = [c.lower().strip() for c in candidates]
    variants = section_heading_variants()
    meta = structural_rule_meta("missing_section_heading")

    found_sections = set()
    for section_key, variant_list in variants.items():
        for candidate in candidates_lower:
            if any(variant in candidate for variant in variant_list):
                found_sections.add(section_key)
                break

    for section_key in _REQUIRED_BY_DEFAULT:
        if section_key not in found_sections:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.SECTION_ARCHITECTURE,
                    classification=RiskClassification.PROBABLE_ATS_RISK,
                    severity=Severity.ORANGE,
                    title=f"No clearly labeled '{section_key.title()}' section heading detected",
                    description=f"No heading matching common '{section_key}' section labels was detected using font-size/bold/style heuristics.",
                    why_it_matters=meta["why_it_matters"],
                    ats_evidence=f"Heading candidates detected: {candidates[:15]}" if candidates else "No heading-like text detected at all.",
                    recommended_change=f"Add a standard, clearly formatted '{section_key.title()}' heading above the relevant content.",
                    confidence=SourceConfidence(meta.get("confidence", "E")),
                    sources=_citation("missing_section_heading"),
                    priority=PriorityBucket.STRONGLY_RECOMMENDED,
                )
            )

    return findings
