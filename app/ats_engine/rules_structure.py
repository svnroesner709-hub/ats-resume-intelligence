"""
Layer 2 rules: structural ATS compatibility -- columns, tables, text boxes,
hidden text, fonts, hyperlinks.
"""
from __future__ import annotations

from app.ats_engine.context import AnalysisContext
from app.ats_engine.layout import detect_multi_column_page, is_font_recognized, normalize_font_name
from app.knowledge_base.loader import safe_fonts, structural_rule_meta
from app.models import (
    BBox,
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


def rule_multi_column(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []
    meta = structural_rule_meta("multi_column")

    if ctx.file_type == "pdf" and ctx.pymupdf is not None:
        flagged_pages = [p.page_number for p in ctx.pymupdf.pages if detect_multi_column_page(p)]
        if flagged_pages:
            pages_str = ", ".join(str(p + 1) for p in flagged_pages)
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.STRUCTURE,
                    classification=RiskClassification.PROBABLE_ATS_RISK,
                    severity=Severity.ORANGE,
                    title="Multi-column layout detected",
                    description=f"Page(s) {pages_str} appear to use a multi-column layout (distinct left/right text blocks with a clear gutter between them).",
                    why_it_matters=meta["why_it_matters"],
                    ats_evidence=f"Detected on page(s): {pages_str}, via left/right block clustering with a horizontal gutter gap.",
                    recommended_change="Switch to a single-column layout, or verify reading order carefully if columns are kept for design reasons.",
                    confidence=SourceConfidence(meta.get("confidence", "E")),
                    sources=_citation("multi_column"),
                    priority=PriorityBucket.STRONGLY_RECOMMENDED,
                )
            )
    elif ctx.file_type == "docx" and ctx.docx is not None:
        if ctx.docx.column_count > 1:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.STRUCTURE,
                    classification=RiskClassification.PROBABLE_ATS_RISK,
                    severity=Severity.ORANGE,
                    title="Document uses a multi-column section layout",
                    description=f"The document's section formatting specifies {ctx.docx.column_count} columns.",
                    why_it_matters=meta["why_it_matters"],
                    ats_evidence=f"w:cols/@w:num = {ctx.docx.column_count} in the document's section properties.",
                    recommended_change="Switch to a single-column layout.",
                    confidence=SourceConfidence(meta.get("confidence", "E")),
                    sources=_citation("multi_column"),
                    priority=PriorityBucket.STRONGLY_RECOMMENDED,
                )
            )
    return findings


def rule_tables(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []
    meta = structural_rule_meta("tables")

    if ctx.file_type == "pdf" and ctx.pdfplumber is not None:
        for t in ctx.pdfplumber.tables:
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.STRUCTURE,
                    classification=RiskClassification.POSSIBLE_ATS_RISK,
                    severity=Severity.YELLOW,
                    title=f"Table detected on page {t.page + 1}",
                    description=f"A {t.n_rows}-row x {t.n_cols}-column table was detected on page {t.page + 1}.",
                    why_it_matters=meta["why_it_matters"],
                    ats_evidence=f"pdfplumber table detection: page {t.page + 1}, bbox {tuple(round(v, 1) for v in t.bbox)}.",
                    recommended_change="Consider converting the table to plain paragraph/bullet text if it holds core resume content (dates, titles, skills).",
                    confidence=SourceConfidence(meta.get("confidence", "E")),
                    sources=_citation("tables"),
                    location=BBox(page=t.page, x0=t.bbox[0], y0=t.bbox[1], x1=t.bbox[2], y1=t.bbox[3]),
                    priority=PriorityBucket.OPTIONAL_POLISH,
                )
            )
    elif ctx.file_type == "docx" and ctx.docx is not None:
        for i, t in enumerate(ctx.docx.tables):
            findings.append(
                Finding(
                    id=next_id(),
                    category=FindingCategory.STRUCTURE,
                    classification=RiskClassification.POSSIBLE_ATS_RISK,
                    severity=Severity.YELLOW,
                    title=f"Table detected ({t.n_rows}x{t.n_cols})",
                    description=f"A {t.n_rows}-row x {t.n_cols}-column table was detected. Sample content: \"{t.sample_text[:120]}\"",
                    why_it_matters=meta["why_it_matters"],
                    ats_evidence=f"python-docx table #{i + 1}: {t.n_rows} rows x {t.n_cols} cols.",
                    recommended_change="Consider converting to plain paragraph/bullet text if it holds core resume content.",
                    confidence=SourceConfidence(meta.get("confidence", "E")),
                    sources=_citation("tables"),
                    priority=PriorityBucket.OPTIONAL_POLISH,
                )
            )
    return findings


def rule_text_boxes(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []
    if ctx.file_type != "docx" or ctx.docx is None:
        return findings
    meta = structural_rule_meta("text_boxes")

    for i, tb_text in enumerate(ctx.docx.textbox_text):
        snippet = tb_text[:160]
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.STRUCTURE,
                classification=RiskClassification.CONFIRMED_ATS_RISK,
                severity=Severity.RED,
                title="Content found inside a text box (outside normal document flow)",
                description=f"Text box #{i + 1} contains: \"{snippet}\". This content is not part of the normal paragraph flow that python-docx (and most ATS parsers) read.",
                why_it_matters=meta["why_it_matters"],
                ats_evidence="Found inside a w:txbxContent element; absent from the document's normal paragraph text.",
                recommended_change="Move this content into a regular paragraph in the main document body.",
                confidence=SourceConfidence(meta.get("confidence", "E")),
                sources=_citation("text_boxes"),
                priority=PriorityBucket.MUST_FIX,
            )
        )
    return findings


def rule_hidden_text(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []
    if ctx.file_type != "docx" or ctx.docx is None:
        return findings
    meta = structural_rule_meta("hidden_text")

    all_hidden = list(ctx.docx.hidden_text_runs) + list(ctx.docx.white_text_runs)
    if all_hidden:
        joined = "; ".join(f'"{t[:80]}"' for t in all_hidden[:5])
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.STRUCTURE,
                classification=RiskClassification.CONFIRMED_ATS_RISK,
                severity=Severity.RED,
                title="Hidden or white-on-white text detected",
                description=f"Found {len(all_hidden)} run(s) of hidden/white-colored text, e.g. {joined}.",
                why_it_matters=meta["why_it_matters"],
                ats_evidence=f"{len(ctx.docx.hidden_text_runs)} run(s) with w:vanish set; {len(ctx.docx.white_text_runs)} run(s) with color FFFFFF.",
                recommended_change="Remove hidden/white text entirely. If it was meant as ATS keyword optimization, add the same terms as genuine, visible, truthful content instead.",
                confidence=SourceConfidence(meta.get("confidence", "E")),
                sources=_citation("hidden_text"),
                priority=PriorityBucket.MUST_FIX,
            )
        )
    return findings


def rule_fonts(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []
    if ctx.file_type != "pdf" or ctx.pymupdf is None:
        return findings
    meta = structural_rule_meta("uncommon_font")
    safe = safe_fonts()

    unrecognized = set()
    for raw in ctx.pymupdf.fonts_used:
        if raw and not is_font_recognized(raw, safe):
            unrecognized.add(normalize_font_name(raw))
    unrecognized.discard("")

    if unrecognized:
        names = ", ".join(sorted(unrecognized))
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.TYPOGRAPHY,
                classification=RiskClassification.POSSIBLE_ATS_RISK,
                severity=Severity.YELLOW,
                title="Uses font(s) outside the commonly-recognized safe list",
                description=f"Font(s) not on the recognized safe list: {names}.",
                why_it_matters=meta["why_it_matters"],
                ats_evidence=f"Fonts detected in the PDF's text spans: {', '.join(sorted(ctx.pymupdf.fonts_used))}.",
                recommended_change="Consider a widely-supported font (Arial, Calibri, Georgia, Times New Roman) unless this one is confirmed to embed and extract cleanly.",
                confidence=SourceConfidence(meta.get("confidence", "E")),
                sources=_citation("uncommon_font"),
                priority=PriorityBucket.OPTIONAL_POLISH,
            )
        )
    return findings


def rule_hyperlinks(ctx: AnalysisContext, next_id) -> list[Finding]:
    findings: list[Finding] = []
    count = 0
    if ctx.file_type == "pdf" and ctx.pymupdf is not None:
        count = len(ctx.pymupdf.hyperlinks)
    elif ctx.file_type == "docx" and ctx.docx is not None:
        count = ctx.docx.hyperlink_count

    if count > 0:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.STRUCTURE,
                classification=RiskClassification.NO_MEANINGFUL_RISK,
                severity=Severity.INFO,
                title=f"{count} hyperlink(s) found",
                description=f"The document contains {count} hyperlink(s) (e.g. LinkedIn, portfolio).",
                why_it_matters="Hyperlinks are broadly supported, but some ATS parsers strip the link and keep only the visible anchor text.",
                ats_evidence=f"{count} hyperlink object(s) detected.",
                recommended_change="Make sure the visible text near each link (not just the URL) is meaningful on its own.",
                confidence=SourceConfidence.E,
                sources=[],
                priority=PriorityBucket.NO_ACTION,
            )
        )
    return findings
