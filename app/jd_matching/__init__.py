"""
STUB -- Phase 8, spec "TARGET ROLE MODE" (job-description matching).

Will own: given TargetProfile.job_description, build the
Requirement Coverage Matrix (Strong Match / Partial Match / Missing /
Probably Irrelevant) described in the spec, using keyword_engine's
semantic matching underneath. Depends on keyword_engine, which is itself
a stub -- see app/keyword_engine/__init__.py.
"""
from __future__ import annotations

from app.models import TargetProfile


def build_requirement_coverage_matrix(full_text: str, target: TargetProfile) -> dict:
    if not target.job_description:
        raise ValueError("No job description supplied -- JD matching requires TargetProfile.job_description.")
    raise NotImplementedError(
        "jd_matching.build_requirement_coverage_matrix is not yet implemented."
    )
