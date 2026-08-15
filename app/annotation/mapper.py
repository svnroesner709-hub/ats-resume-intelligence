"""
Phase 4: highlight/annotation engine.

Converts Findings that carry a page-coordinate `location` into normalized
(0-1 fraction of page width/height) overlay boxes the frontend can
position over the rendered page PNG regardless of on-screen zoom. Findings
without a natural bounding box (most wording/contact/section findings)
simply don't get a page overlay -- they still show up in the side panel's
finding list, which is the correct behavior, not a gap: not everything a
resume reviewer flags has a single physical location on the page.
"""
from __future__ import annotations

from collections import defaultdict

from app.models import Finding, PageInfo


def build_overlays(findings: list[Finding], pages: list[PageInfo]) -> dict[int, list[dict]]:
    pages_by_number = {p.page_number: p for p in pages}
    overlays: dict[int, list[dict]] = defaultdict(list)

    for finding in findings:
        loc = finding.location
        if loc is None:
            continue
        page = pages_by_number.get(loc.page)
        if page is None or page.width <= 0 or page.height <= 0:
            continue
        overlays[loc.page].append(
            {
                "finding_id": finding.id,
                "severity": finding.severity.value,
                "x0": loc.x0 / page.width,
                "y0": loc.y0 / page.height,
                "x1": loc.x1 / page.width,
                "y1": loc.y1 / page.height,
            }
        )

    return dict(overlays)
