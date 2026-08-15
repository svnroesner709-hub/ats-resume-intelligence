"""
Phase 10 stubs -- not yet implemented. Each raises NotImplementedError so
the API contract (route exists, returns 501) is already correct and the
GUI can show "coming soon" without a shape mismatch later.

Planned (per spec "EXPORT" section):
  - annotated_pdf_export: PDF with highlight overlays baked in
  - rewrite_export: full recommended rewrite of the resume
  - change_log_export: structured before/after change log
  - ats_safe_version_export: a maximally parser-safe reformat
  - human_optimized_version_export: a recruiter-readability-optimized reformat
  - target_job_specific_version_export: JD-tailored version (needs jd_matching)
"""
from __future__ import annotations

from app.models import AnalysisResult


def annotated_pdf_export(result: AnalysisResult) -> bytes:
    raise NotImplementedError("Annotated PDF export is not yet implemented.")


def rewrite_export(result: AnalysisResult) -> str:
    raise NotImplementedError("Full rewrite export is not yet implemented (requires career_engine).")


def change_log_export(result: AnalysisResult) -> str:
    raise NotImplementedError("Change log export is not yet implemented.")


def ats_safe_version_export(result: AnalysisResult) -> bytes:
    raise NotImplementedError("ATS-safe version export is not yet implemented.")


def human_optimized_version_export(result: AnalysisResult) -> bytes:
    raise NotImplementedError("Human-optimized version export is not yet implemented.")


def target_job_specific_version_export(result: AnalysisResult) -> bytes:
    raise NotImplementedError("Target-job-specific version export is not yet implemented (requires jd_matching).")
