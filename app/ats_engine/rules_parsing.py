"""
Layer 1 rules: turn extraction-comparison evidence and image-only-page
detection into Findings. These are the highest-confidence findings the
engine produces because they're based on directly observed extraction
behavior, not inferred layout risk.
"""
from __future__ import annotations

from app.ats_engine.context import AnalysisContext
from app.knowledge_base.loader import structural_rule_meta
from app.models import (
    Finding,
    FindingCategory,
    PriorityBucket,
    RiskClassification,
    Severity,
    SourceCitation,
    SourceConfidence,
)


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


def rule_extraction_agreement(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []
    comparison = ctx.extraction_comparison
    meta = structural_rule_meta("extraction_disagreement")

    if comparison.agreement_ratio < 0.7 and len([m for m in comparison.methods if m.ok]) >= 2:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.PARSING,
                classification=RiskClassification.CONFIRMED_ATS_RISK,
                severity=Severity.RED,
                title="Independent extraction methods disagree significantly",
                description=(
                    f"Text extracted by different parsing methods only agrees "
                    f"{comparison.agreement_ratio * 100:.0f}% of the time. That level of "
                    f"divergence usually means the document's layout confuses at least one "
                    f"class of text extractor."
                ),
                why_it_matters=meta["why_it_matters"],
                ats_evidence=(
                    f"Compared {len(comparison.methods)} extraction methods "
                    f"({', '.join(m.method for m in comparison.methods)}); pairwise text "
                    f"similarity averaged {comparison.agreement_ratio * 100:.0f}%."
                ),
                recommended_change="Simplify the layout (single column, no floating text) and re-check.",
                confidence=SourceConfidence(meta.get("confidence", "E")),
                sources=_citation("extraction_disagreement"),
                priority=PriorityBucket.MUST_FIX,
            )
        )
    elif comparison.agreement_ratio < 0.9 and len([m for m in comparison.methods if m.ok]) >= 2:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.PARSING,
                classification=RiskClassification.PROBABLE_ATS_RISK,
                severity=Severity.ORANGE,
                title="Extraction methods show moderate disagreement",
                description=(
                    f"Text extracted by different parsing methods agrees "
                    f"{comparison.agreement_ratio * 100:.0f}% of the time -- workable, but "
                    f"worth a manual double-check of section ordering."
                ),
                why_it_matters=meta["why_it_matters"],
                ats_evidence=(
                    f"Compared {len(comparison.methods)} extraction methods; pairwise text "
                    f"similarity averaged {comparison.agreement_ratio * 100:.0f}%."
                ),
                recommended_change="Manually verify reading order top-to-bottom against the rendered preview.",
                confidence=SourceConfidence(meta.get("confidence", "E")),
                sources=_citation("extraction_disagreement"),
                priority=PriorityBucket.STRONGLY_RECOMMENDED,
            )
        )

    for divergence_msg in comparison.divergences:
        if divergence_msg.startswith("Extraction method") and "failed entirely" in divergence_msg:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.PARSING,
                    classification=RiskClassification.CONFIRMED_ATS_RISK,
                    severity=Severity.RED,
                    title="One extraction method could not read this document at all",
                    description=divergence_msg,
                    why_it_matters="If a well-established open-source parser cannot read the file, some ATS parsers likely can't either.",
                    ats_evidence=divergence_msg,
                    recommended_change="Re-export the file (e.g. print-to-PDF from the original Word doc) and re-check.",
                    confidence=SourceConfidence.E,
                    sources=_citation("extraction_disagreement"),
                    priority=PriorityBucket.MUST_FIX,
                )
            )
        elif "unrecognized/undecodable" in divergence_msg or "control character" in divergence_msg:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.PARSING,
                    classification=RiskClassification.CONFIRMED_ATS_RISK,
                    severity=Severity.RED,
                    title="Garbled characters found in extracted text",
                    description=divergence_msg,
                    why_it_matters="Garbled characters mean an ATS will store corrupted text for that portion of the resume -- keywords in that region won't match searches.",
                    ats_evidence=divergence_msg,
                    recommended_change="Check for broken ligatures, unusual Unicode bullet/dash characters, or a corrupted font subset near the affected text.",
                    confidence=SourceConfidence.E,
                    sources=_citation("extraction_disagreement"),
                    priority=PriorityBucket.MUST_FIX,
                )
            )
        elif "recovered only" in divergence_msg:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.PARSING,
                    classification=RiskClassification.PROBABLE_ATS_RISK,
                    severity=Severity.ORANGE,
                    title="One extraction method recovered much less text than the others",
                    description=divergence_msg,
                    why_it_matters=meta["why_it_matters"],
                    ats_evidence=divergence_msg,
                    recommended_change="Check whether content is embedded as an image, inside a text box, or in an unusual container.",
                    confidence=SourceConfidence.E,
                    sources=_citation("extraction_disagreement"),
                    priority=PriorityBucket.STRONGLY_RECOMMENDED,
                )
            )

    return findings


def rule_image_only_pages(ctx: AnalysisContext, next_id) -> list[Finding]:
    if ctx.file_type != "pdf" or ctx.pymupdf is None:
        return []

    findings: list[Finding] = []
    meta = structural_rule_meta("image_only_page")

    for page in ctx.pymupdf.pages:
        if not page.has_text and page.has_images:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.PARSING,
                    classification=RiskClassification.CONFIRMED_ATS_RISK,
                    severity=Severity.RED,
                    title=f"Page {page.page_number + 1} has no extractable text layer",
                    description=(
                        f"Page {page.page_number + 1} appears to be a scanned image or a "
                        f"flattened/rasterized page with no underlying text -- zero characters "
                        f"were extracted from it directly, and it contains image data."
                    ),
                    why_it_matters=meta["why_it_matters"],
                    ats_evidence=f"Page {page.page_number + 1}: has_text=False, has_images=True.",
                    recommended_change="Re-export this page from the original source document as real (non-rasterized) text, or run OCR and verify the OCR text layer is embedded in the PDF.",
                    confidence=SourceConfidence.E,
                    sources=_citation("image_only_page"),
                    location=None,
                    priority=PriorityBucket.MUST_FIX,
                )
            )
    return findings
