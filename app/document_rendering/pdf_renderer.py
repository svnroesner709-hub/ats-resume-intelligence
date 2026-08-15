"""
Phase 3: Document viewer support -- render each PDF page to a PNG image at
a fixed zoom so the GUI can show the resume exactly as a human (and,
loosely, an ATS's PDF-to-text step) would encounter it, with overlay
highlight boxes positioned using the same coordinate space.
"""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

RENDER_ZOOM = 2.0  # 2x = ~144 DPI, sharp enough for on-screen review


def render_pages(pdf_path: Path, output_dir: Path) -> list[dict]:
    """Render every page of `pdf_path` to PNG in `output_dir`.

    Returns a list of {page_number, width, height, image_path} where
    width/height are in PDF point units (the same coordinate space used by
    pdf_pymupdf.extract's bboxes), so the frontend can scale overlay boxes
    by (rendered_pixel_size / point_size).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_info: list[dict] = []
    matrix = fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM)

    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            image_name = f"page-{page_index}.png"
            pix.save(str(output_dir / image_name))
            pages_info.append(
                {
                    "page_number": page_index,
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "image_path": image_name,
                }
            )
    return pages_info
