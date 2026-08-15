"""
Layer 1 core logic: compare independent extraction outputs and surface
divergence as evidence, rather than asserting parsing quality from a
single method's output.

This is file-type agnostic -- it just takes a list of (method_name, text)
results and diffs them. Callers (main.py) build that list from
pdf_pymupdf / pdf_pdfplumber / pdf_pdfminer for PDFs, or from python-docx
vs. the mammoth-rendered plain text for DOCX.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

from app.models import ExtractionComparison, ExtractionMethodResult

_REPLACEMENT_CHAR = "�"
# Deliberately excludes \x0c (form feed): pdfminer.six's extract_text()
# routinely inserts form-feed characters as a page-break marker between
# pages -- that's a normal artifact of that extractor, not evidence of
# corrupted/garbled text, so it must not trip the garbling detector.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0e-\x1f]")


def _normalize_for_diff(text: str) -> str:
    """Collapse whitespace so comparison focuses on content, not layout
    whitespace differences between extraction algorithms."""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def detect_garbling(text: str) -> list[str]:
    issues = []
    if _REPLACEMENT_CHAR in text:
        count = text.count(_REPLACEMENT_CHAR)
        issues.append(f"{count} unrecognized/undecodable character(s) (U+FFFD) found in extracted text.")
    control_matches = _CONTROL_CHAR_RE.findall(text)
    if control_matches:
        issues.append(f"{len(control_matches)} stray control character(s) found in extracted text.")
    return issues


def compare_extractions(results: list[ExtractionMethodResult]) -> ExtractionComparison:
    ok_results = [r for r in results if r.ok]
    divergences: list[str] = []

    for r in results:
        if not r.ok:
            divergences.append(f"Extraction method '{r.method}' failed entirely: {r.error}")
        else:
            divergences.extend(f"[{r.method}] {msg}" for msg in detect_garbling(r.text))

    if len(ok_results) >= 2:
        max_chars = max(r.char_count for r in ok_results)
        for r in ok_results:
            if max_chars > 0 and r.char_count < 0.5 * max_chars:
                divergences.append(
                    f"Extraction method '{r.method}' recovered only {r.char_count} characters "
                    f"vs. up to {max_chars} from another method -- likely missing content "
                    f"(text in an image, an unusual container, or a parsing failure specific to that method)."
                )

        # Pairwise similarity across normalized text.
        pair_ratios = []
        normalized = [_normalize_for_diff(r.text) for r in ok_results]
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                a, b = normalized[i], normalized[j]
                if not a and not b:
                    ratio = 1.0
                else:
                    ratio = difflib.SequenceMatcher(None, a, b).ratio()
                pair_ratios.append(ratio)
        agreement_ratio = sum(pair_ratios) / len(pair_ratios) if pair_ratios else 1.0
    elif len(ok_results) == 1:
        agreement_ratio = 1.0
    else:
        agreement_ratio = 0.0

    return ExtractionComparison(
        methods=results,
        agreement_ratio=round(agreement_ratio, 4),
        divergences=divergences,
    )
