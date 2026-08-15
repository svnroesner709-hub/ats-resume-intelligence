"""
PDF extraction method 3: pdfminer.six.

A third, independent extraction engine used purely as a cross-check for
Layer 1 ("compare extraction outputs" / "perform multiple extraction
methods where possible"). pdfminer's reading-order algorithm differs from
both PyMuPDF's and pdfplumber's, so divergence here is a genuine signal
of an ATS-relevant reading-order or text-recovery problem, not noise.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pdfminer.high_level import extract_text


@dataclass
class PdfMinerExtraction:
    full_text: str
    method: str = "pdfminer"
    error: str | None = None


def extract(path: Path) -> PdfMinerExtraction:
    try:
        text = extract_text(str(path)) or ""
    except Exception as exc:
        return PdfMinerExtraction(full_text="", error=str(exc))
    return PdfMinerExtraction(full_text=text)
