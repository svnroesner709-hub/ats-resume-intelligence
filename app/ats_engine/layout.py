"""Layout heuristics shared by rules_structure.py (kept separate so the
detection logic is unit-testable without constructing full Finding objects)."""
from __future__ import annotations

import re

from app.parsers.pdf_pymupdf import PageData

_SUBSET_PREFIX_RE = re.compile(r"^[A-Z]{6}\+")
_STYLE_SUFFIX_RE = re.compile(r"[-,]?(Bold|Italic|Oblique|Regular|MT|PS|PSMT)+$", re.I)


def normalize_font_name(raw: str) -> str:
    name = _SUBSET_PREFIX_RE.sub("", raw or "")
    # strip style suffixes iteratively (e.g. "Arial-BoldMT" -> "Arial")
    prev = None
    while prev != name:
        prev = name
        name = _STYLE_SUFFIX_RE.sub("", name).strip()
    return name.strip()


def is_font_recognized(raw_font_name: str, safe_fonts_lower: set[str]) -> bool:
    normalized = normalize_font_name(raw_font_name).lower()
    if not normalized:
        return True  # nothing to judge
    for safe in safe_fonts_lower:
        if safe in normalized or normalized in safe:
            return True
    return False


def detect_multi_column_page(page: PageData, min_blocks_per_side: int = 2, gutter_ratio: float = 0.03) -> bool:
    """Heuristic: blocks narrower than ~62% of page width that cleanly split
    into a left group and a right group with a real horizontal gap between
    them (a gutter), each side with at least a couple of blocks."""
    width = page.width
    if width <= 0:
        return False

    narrow_blocks = [b for b in page.blocks if (b.bbox[2] - b.bbox[0]) < 0.62 * width]
    if len(narrow_blocks) < min_blocks_per_side * 2:
        return False

    mid = width / 2
    left_group = [b for b in narrow_blocks if b.bbox[0] < mid]
    right_group = [b for b in narrow_blocks if b.bbox[0] >= mid]
    if len(left_group) < min_blocks_per_side or len(right_group) < min_blocks_per_side:
        return False

    left_max_x1 = max(b.bbox[2] for b in left_group)
    right_min_x0 = min(b.bbox[0] for b in right_group)
    gap = right_min_x0 - left_max_x1
    return gap > gutter_ratio * width


def extract_pdf_header_footer_text(pages: list[PageData], margin_ratio: float = 0.1) -> tuple[list[str], list[str]]:
    """Best-effort header/footer text for PDFs: blocks whose full bbox sits
    within the top/bottom margin_ratio of the page height. PDFs have no
    formal header/footer container (unlike DOCX), so this is a position
    heuristic, not a structural fact -- callers should treat it accordingly."""
    header_texts: list[str] = []
    footer_texts: list[str] = []
    for page in pages:
        if page.height <= 0:
            continue
        top_bound = page.height * margin_ratio
        bottom_bound = page.height * (1 - margin_ratio)
        for block in page.blocks:
            y0, y1 = block.bbox[1], block.bbox[3]
            if y1 <= top_bound:
                header_texts.append(block.text)
            elif y0 >= bottom_bound:
                footer_texts.append(block.text)
    return header_texts, footer_texts
