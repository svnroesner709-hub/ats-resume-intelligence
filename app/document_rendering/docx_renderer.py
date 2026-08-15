"""
Phase 3: DOCX viewer support via mammoth (DOCX -> semantic HTML).

mammoth is deliberately conservative -- it maps Word styles to clean HTML
(headings, lists, bold/italic, tables) rather than trying to pixel-match
Word's rendering. That's a feature here: it also approximates what an
ATS's own DOCX-to-text/HTML conversion tends to see, so mammoth's own
"messages" log (unrecognized styles, skipped images) doubles as a second
signal for potential ATS parsing gaps.
"""
from __future__ import annotations

from pathlib import Path

import mammoth


def render_html(docx_path: Path) -> dict:
    with open(docx_path, "rb") as f:
        result = mammoth.convert_to_html(f)

    return {
        "html": result.value,
        "warnings": [str(m) for m in result.messages],
    }
