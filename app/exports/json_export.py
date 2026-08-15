"""
Phase 10 (partial): the one export type implemented in this MVP -- a full
JSON analysis report, which is also the exact structure the GUI renders
from. Other export types described in the spec (annotated PDF, rewritten
resume, ATS-safe version, human-optimized version, target-job-specific
version) are NOT implemented yet; see exports/stubs.py.
"""
from __future__ import annotations

from app.models import AnalysisResult


def to_json_report(result: AnalysisResult) -> str:
    return result.model_dump_json(indent=2)
