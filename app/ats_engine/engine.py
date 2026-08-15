"""
Orchestrator: run every parser + every rule for one uploaded document and
return the assembled (context, contact_info, findings) tuple that
main.py/scoring/annotation consume.
"""
from __future__ import annotations

from pathlib import Path

from app.ats_engine.contact_info import extract_contact_info
from app.ats_engine.context import AnalysisContext
from app.ats_engine.layout import extract_pdf_header_footer_text
from app.ats_engine.rules_contact import rule_contact_completeness
from app.ats_engine.rules_parsing import rule_extraction_agreement, rule_image_only_pages
from app.ats_engine.rules_sections import rule_section_headings
from app.ats_engine.rules_structure import (
    rule_fonts,
    rule_hyperlinks,
    rule_multi_column,
    rule_tables,
    rule_text_boxes,
    rule_hidden_text,
)
from app.models import ContactInfo, ExtractionMethodResult, Finding
from app.parsers import docx_parser, pdf_pdfminer, pdf_pdfplumber, pdf_pymupdf
from app.parsers.extraction_compare import compare_extractions

_PDF_RULES = [
    rule_extraction_agreement,
    rule_image_only_pages,
    rule_multi_column,
    rule_tables,
    rule_fonts,
    rule_hyperlinks,
    rule_section_headings,
]

_DOCX_RULES = [
    rule_extraction_agreement,
    rule_multi_column,
    rule_tables,
    rule_text_boxes,
    rule_hidden_text,
    rule_hyperlinks,
    rule_section_headings,
]


class _IdCounter:
    def __init__(self):
        self._n = 0

    def __call__(self) -> str:
        self._n += 1
        return f"F{self._n:03d}"


def build_pdf_context(path: Path) -> AnalysisContext:
    pymupdf_result = pdf_pymupdf.extract(path)
    pdfplumber_result = pdf_pdfplumber.extract(path)
    pdfminer_result = pdf_pdfminer.extract(path)

    method_results = [
        ExtractionMethodResult(method="pymupdf", text=pymupdf_result.full_text, char_count=len(pymupdf_result.full_text), ok=True),
        ExtractionMethodResult(
            method="pdfplumber",
            text=pdfplumber_result.full_text,
            char_count=len(pdfplumber_result.full_text),
            ok=pdfplumber_result.error is None,
            error=pdfplumber_result.error,
        ),
        ExtractionMethodResult(
            method="pdfminer.six",
            text=pdfminer_result.full_text,
            char_count=len(pdfminer_result.full_text),
            ok=pdfminer_result.error is None,
            error=pdfminer_result.error,
        ),
    ]
    comparison = compare_extractions(method_results)
    header_texts, footer_texts = extract_pdf_header_footer_text(pymupdf_result.pages)

    return AnalysisContext(
        file_type="pdf",
        full_text=pymupdf_result.full_text,
        extraction_comparison=comparison,
        pymupdf=pymupdf_result,
        pdfplumber=pdfplumber_result,
        header_texts=header_texts,
        footer_texts=footer_texts,
    )


def build_docx_context(path: Path, docx_html: str = "") -> AnalysisContext:
    docx_result = docx_parser.extract(path)

    # Second independent "extraction method" for comparison purposes: the
    # mammoth-rendered HTML with tags stripped. Different code path than
    # python-docx's paragraph walk, so genuine divergence here is signal.
    import re as _re

    html_text = _re.sub(r"<[^>]+>", " ", docx_html or "")
    html_text = _re.sub(r"\s+", " ", html_text).strip()

    method_results = [
        ExtractionMethodResult(
            method="python-docx",
            text=docx_result.full_text,
            char_count=len(docx_result.full_text),
            ok=docx_result.error is None,
            error=docx_result.error,
        ),
        ExtractionMethodResult(method="mammoth-html-stripped", text=html_text, char_count=len(html_text), ok=True),
    ]
    comparison = compare_extractions(method_results)

    return AnalysisContext(
        file_type="docx",
        full_text=docx_result.full_text,
        extraction_comparison=comparison,
        docx=docx_result,
        header_texts=list(docx_result.header_text),
        footer_texts=list(docx_result.footer_text),
    )


def run_rules(ctx: AnalysisContext) -> tuple[list[Finding], ContactInfo]:
    next_id = _IdCounter()
    findings: list[Finding] = []

    contact = extract_contact_info(ctx.full_text, ctx.header_texts or [], ctx.footer_texts or [])
    findings.extend(rule_contact_completeness(ctx, contact, next_id))

    rule_set = _PDF_RULES if ctx.file_type == "pdf" else _DOCX_RULES
    for rule_fn in rule_set:
        findings.extend(rule_fn(ctx, next_id))

    return findings, contact
