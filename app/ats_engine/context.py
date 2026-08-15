"""
AnalysisContext: the single bundle of everything the rule functions in
rules_*.py need. Built once per uploaded document in main.py and passed
to every rule so rules stay pure functions of (context) -> list[Finding].
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models import ExtractionComparison
from app.parsers.docx_parser import DocxExtraction
from app.parsers.pdf_pdfplumber import PdfPlumberExtraction
from app.parsers.pdf_pymupdf import PyMuPdfExtraction


@dataclass
class AnalysisContext:
    file_type: str  # "pdf" | "docx"
    full_text: str
    extraction_comparison: ExtractionComparison

    # PDF-specific (None for DOCX)
    pymupdf: PyMuPdfExtraction | None = None
    pdfplumber: PdfPlumberExtraction | None = None

    # DOCX-specific (None for PDF)
    docx: DocxExtraction | None = None

    # Header/footer text collected regardless of file type, for the
    # "contact info only in header/footer" check.
    header_texts: list[str] | None = None
    footer_texts: list[str] | None = None

    def __post_init__(self):
        if self.header_texts is None:
            self.header_texts = []
        if self.footer_texts is None:
            self.footer_texts = []
