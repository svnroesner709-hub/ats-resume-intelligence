"""
On-document keyword highlighting: locates where a matched keyword actually
sits on the rendered page (PDF) or in the rendered HTML (DOCX) so the GUI
can paint a highlighter-style mark directly over the resume text -- not
just list the term in the Keywords tab's chip row.

PDF: uses PyMuPDF's Page.search_for(), which is case-insensitive by
default (verified against this project's own fixtures) -- consistent with
how full terms/synonyms are matched in app/keyword_engine/matcher.py. For
short, case-sensitive-matched abbreviations (the same class of term that
motivated matcher.py's case-sensitive-abbreviation fix, e.g. avoiding "TO"
matching "to"), each candidate rect's actual text is re-checked with exact
case before accepting it, so an abbreviation doesn't highlight an unrelated
lowercase word elsewhere on the page.

DOCX: no page geometry exists, so matched terms are wrapped in <mark> tags
within the already-rendered HTML, operating only on text nodes (never
inside a tag) so the markup itself can't be corrupted.

Only "dictionary" matches (via=="dictionary") are highlighted -- an
LLM-semantic match's matched_form is a paraphrased explanation, not a
literal quote from the document, so searching for it verbatim wouldn't
correspond to a real position.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF

from app.models import MatchedKeyword, PageInfo

_MIN_NEEDLE_LEN = 2


def _is_case_sensitive_form(needle: str) -> bool:
    """Heuristic mirroring matcher.py's own case-sensitive-abbreviation
    rule: short, all-caps forms are almost certainly abbreviations that
    were matched case-sensitively, so their on-page highlight must be
    verified case-sensitively too."""
    return len(needle) <= 6 and needle.isupper()


def find_pdf_keyword_boxes(pdf_path: Path, matched_terms: list[MatchedKeyword]) -> dict[int, list[dict]]:
    """Returns page_number -> list of {term, via, x0, y0, x1, y1} in PDF
    point coordinates (same space as pdf_renderer's page images)."""
    dictionary_matches = [m for m in matched_terms if m.via == "dictionary" and m.matched_form]
    if not dictionary_matches:
        return {}

    results: dict[int, list[dict]] = {}
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            page_hits = []
            for m in dictionary_matches:
                needle = m.matched_form.strip()
                if len(needle) < _MIN_NEEDLE_LEN:
                    continue
                case_sensitive = _is_case_sensitive_form(needle)
                for rect in page.search_for(needle):
                    if case_sensitive:
                        actual = page.get_textbox(rect).strip()
                        if actual != needle:
                            continue
                    page_hits.append(
                        {"term": m.term, "via": m.via, "x0": rect.x0, "y0": rect.y0, "x1": rect.x1, "y1": rect.y1}
                    )
            if page_hits:
                results[page_index] = page_hits
    return results


def build_pdf_keyword_overlays(
    pdf_path: Path, matched_terms: list[MatchedKeyword], pages: list[PageInfo]
) -> dict[str, list[dict]]:
    """Normalizes find_pdf_keyword_boxes' point coordinates to 0-1 page
    fractions, matching the convention app/annotation/mapper.py already
    uses for finding overlays, so the frontend scales both the same way."""
    raw = find_pdf_keyword_boxes(pdf_path, matched_terms)
    page_dims = {p.page_number: (p.width, p.height) for p in pages}

    normalized: dict[str, list[dict]] = {}
    for page_index, hits in raw.items():
        width, height = page_dims.get(page_index, (0, 0))
        if not width or not height:
            continue
        normalized[str(page_index)] = [
            {
                "term": h["term"],
                "via": h["via"],
                "x0": h["x0"] / width,
                "y0": h["y0"] / height,
                "x1": h["x1"] / width,
                "y1": h["y1"] / height,
            }
            for h in hits
        ]
    return normalized


_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")


def highlight_docx_html(html: str, matched_terms: list[MatchedKeyword]) -> str:
    """Wraps matched dictionary-hit terms in <mark class="kw-doc-highlight">
    within the mammoth-rendered HTML. Splits on tags first and only
    substitutes within text-node segments so markup can never be altered."""
    forms = sorted(
        {m.matched_form.strip() for m in matched_terms if m.via == "dictionary" and m.matched_form and len(m.matched_form.strip()) >= _MIN_NEEDLE_LEN},
        key=len,
        reverse=True,  # longest-first avoids a short form pre-empting a longer overlapping one
    )
    if not forms or not html:
        return html

    pattern = re.compile(r"\b(" + "|".join(re.escape(f) for f in forms) + r")\b", re.IGNORECASE)

    parts = _TAG_SPLIT_RE.split(html)
    for i in range(0, len(parts), 2):  # even indices are text nodes; odd indices are the tags themselves
        if parts[i]:
            parts[i] = pattern.sub(r'<mark class="kw-doc-highlight">\1</mark>', parts[i])
    return "".join(parts)
