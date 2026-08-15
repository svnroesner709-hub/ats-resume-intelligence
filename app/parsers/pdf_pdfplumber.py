"""
PDF extraction method 2: pdfplumber.

Independent extraction engine (different underlying algorithm than PyMuPDF)
used for Layer 1 cross-comparison, and specifically for its table-detection
(`find_tables`) and character-level x-position data used for multi-column
layout heuristics in the ats_engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber


@dataclass
class TableFinding:
    page: int
    bbox: tuple[float, float, float, float]
    n_rows: int
    n_cols: int


@dataclass
class PdfPlumberExtraction:
    full_text: str
    tables: list[TableFinding]
    char_x_positions_by_page: dict[int, list[float]] = field(default_factory=dict)
    method: str = "pdfplumber"
    error: str | None = None


def extract(path: Path) -> PdfPlumberExtraction:
    text_parts: list[str] = []
    tables: list[TableFinding] = []
    char_x_positions_by_page: dict[int, list[float]] = {}

    try:
        with pdfplumber.open(path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

                for table in page.find_tables():
                    rows = table.extract() or []
                    n_cols = max((len(r) for r in rows), default=0)
                    tables.append(
                        TableFinding(
                            page=page_index,
                            bbox=table.bbox,
                            n_rows=len(rows),
                            n_cols=n_cols,
                        )
                    )

                char_x_positions_by_page[page_index] = [c["x0"] for c in page.chars]
    except Exception as exc:  # pdfplumber can raise on malformed PDFs
        return PdfPlumberExtraction(
            full_text="",
            tables=[],
            char_x_positions_by_page={},
            error=str(exc),
        )

    return PdfPlumberExtraction(
        full_text="\n".join(text_parts),
        tables=tables,
        char_x_positions_by_page=char_x_positions_by_page,
    )
