"""
Phase 8 JD mode: builds the Requirement Coverage Matrix (spec's "TARGET
ROLE MODE") when the user pastes a job description. LLM-powered -- only
runs when app.config.LLM_ENABLED and target.job_description is non-empty.

Raises LLMNotConfiguredError / LLMCallError on failure; app/main.py
catches these and sets AnalysisResult.jd_match.status accordingly.
"""
from __future__ import annotations

from app.llm.client import call_tool
from app.llm.schemas import JD_REQUIREMENT_MATRIX_SCHEMA
from app.models import JDMatchResult, JDRequirementRow, TargetProfile

_SYSTEM_PROMPT = """You are an institutional-quality aerospace/defense recruiter comparing a resume against a \
specific job description. Extract the JD's actual requirements/qualifications, then classify the resume's \
coverage of each one truthfully.

Hard rules:
- Do not rewrite the resume into the job description -- this is an honest coverage assessment, not a rewrite tool.
- "strong_match" requires clear, specific evidence in the resume text -- not just plausible inference.
- Prefer more, smaller, specific requirement rows over a few vague ones.
- evidence must be a real quote or close paraphrase from the resume, or null if there's no coverage.
"""


def build_requirement_coverage_matrix(full_text: str, target: TargetProfile) -> JDMatchResult:
    user_content = (
        f"Job description:\n{(target.job_description or '')[:6000]}\n\n"
        f"Resume text:\n{full_text[:12000]}"
    )

    result = call_tool(
        system=_SYSTEM_PROMPT,
        user_content=user_content,
        tool_name=JD_REQUIREMENT_MATRIX_SCHEMA["name"],
        tool_description=JD_REQUIREMENT_MATRIX_SCHEMA["description"],
        input_schema=JD_REQUIREMENT_MATRIX_SCHEMA["input_schema"],
        max_tokens=3000,
    )

    rows = [
        JDRequirementRow(
            requirement=r.get("requirement", ""),
            jd_importance=r.get("jd_importance", "preferred"),
            resume_coverage=r.get("resume_coverage", "missing"),
            evidence=r.get("evidence"),
            recommendation=r.get("recommendation"),
        )
        for r in result.get("requirements", [])
    ]

    return JDMatchResult(
        requirements=rows,
        overall_fit_note=result.get("overall_fit_note", ""),
        status="computed",
    )
