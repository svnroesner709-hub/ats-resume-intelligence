"""
PDF extraction method 1 (primary): PyMuPDF (fitz).

Gives layout-aware extraction: per-block bounding boxes, font names/sizes,
hyperlinks, and page dimensions. This is the method the rendering and
ats_engine modules lean on most heavily because it's the only one of the
three that exposes real geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class TextBlock:
    page: int
    bbox: tuple[float, float, float, float]
    text: str
    font_names: set[str] = field(default_factory=set)
    font_sizes: set[float] = field(default_factory=set)
    is_bold: bool = False


@dataclass
class PageData:
    page_number: int
    width: float
    height: float
    blocks: list[TextBlock]
    has_text: bool
    has_images: bool


@dataclass
class PyMuPdfExtraction:
    pages: list[PageData]
    full_text: str
    hyperlinks: list[dict]
    fonts_used: set[str]
    method: str = "pymupdf"
    error: str | None = None


def extract(path: Path) -> PyMuPdfExtraction:
    pages: list[PageData] = []
    full_text_parts: list[str] = []
    hyperlinks: list[dict] = []
    fonts_used: set[str] = set()

    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc):
            page_dict = page.get_text("dict")
            blocks: list[TextBlock] = []
            has_images = False

            for raw_block in page_dict.get("blocks", []):
                if raw_block.get("type") == 1:
                    has_images = True
                    continue
                block_text_parts = []
                font_names: set[str] = set()
                font_sizes: set[float] = set()
                is_bold = False
                for line in raw_block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        block_text_parts.append(span_text)
                        font_names.add(span.get("font", ""))
                        font_sizes.add(round(span.get("size", 0), 1))
                        fonts_used.add(span.get("font", ""))
                        flags = span.get("flags", 0)
                        if flags & 2**4:  # bold flag bit in PyMuPDF span flags
                            is_bold = True
                    block_text_parts.append("\n")
                block_text = "".join(block_text_parts).strip()
                if block_text:
                    blocks.append(
                        TextBlock(
                            page=page_index,
                            bbox=tuple(raw_block.get("bbox", (0, 0, 0, 0))),
                            text=block_text,
                            font_names=font_names,
                            font_sizes=font_sizes,
                            is_bold=is_bold,
                        )
                    )

            for img in page.get_images(full=True):
                has_images = True

            page_full_text = page.get_text("text")
            full_text_parts.append(page_full_text)

            for link in page.get_links():
                if link.get("uri"):
                    hyperlinks.append({"page": page_index, "uri": link["uri"]})

            pages.append(
                PageData(
                    page_number=page_index,
                    width=page.rect.width,
                    height=page.rect.height,
                    blocks=blocks,
                    has_text=bool(page_full_text.strip()),
                    has_images=has_images,
                )
            )

    return PyMuPdfExtraction(
        pages=pages,
        full_text="\n".join(full_text_parts),
        hyperlinks=hyperlinks,
        fonts_used=fonts_used,
    )
