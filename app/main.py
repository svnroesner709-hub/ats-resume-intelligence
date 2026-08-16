"""
FastAPI app: serves the local GUI and the analysis API.

Routes:
  GET  /                              -> static/index.html
  POST /api/analyze                   -> run full Phase 1-5 pipeline, return AnalysisResult
  GET  /api/pages/{file_id}/{name}    -> rendered PDF page PNGs
  GET  /api/export/{file_id}/json     -> download the JSON analysis report
  GET  /api/export/{file_id}/{kind}   -> 501, not-yet-implemented export kinds (spec's other export types)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.annotation.mapper import build_overlays
from app.aerospace_engine.engine import run_pm_positioning
from app.ats_engine.engine import build_docx_context, build_pdf_context, run_rules
from app.career_engine.engine import evaluate_positioning
from app.career_engine.readability_scan import run_readability_scan
from app.career_engine.role_alignment import compute_role_alignment
from app.config import LLM_ENABLED, LLM_MODEL
from app.document_rendering import docx_renderer, pdf_renderer
from app.exports import json_export, stubs as export_stubs
from app.ingestion.upload import FileTooLarge, UnsupportedFileType, store_upload
from app.jd_matching.engine import build_requirement_coverage_matrix
from app.keyword_engine.matcher import run_keyword_engine
from app.llm.client import LLMCallError, LLMNotConfiguredError
from app.models import (
    AnalysisResult,
    DocumentInfo,
    JDMatchResult,
    PageInfo,
    PriorityBucket,
    Scores,
    TargetProfile,
)
from app.scoring.engine import compute_scores

_NOT_CONFIGURED_NOTE = "Requires ANTHROPIC_API_KEY in .env -- see .env.example. Phases 1-5 and Keyword Coverage work without it."

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"

app = FastAPI(title="ATS Resume Intelligence")

# In-memory cache of the last analysis per file_id, for exports.
# MVP-scoped: local single-user tool, no persistence across restart.
_ANALYSIS_CACHE: dict[str, AnalysisResult] = {}

_SAFE_IMAGE_NAME_RE = re.compile(r"^page-\d+\.png$")
_SAFE_FILE_ID_RE = re.compile(r"^[a-f0-9]{16}$")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _make_id_continuation(existing_findings):
    """Returns a next_id() callable that continues the F### numbering used
    by ats_engine.engine.run_rules, so IDs from later engines (keyword,
    PM positioning, career positioning) never collide with earlier ones."""
    start = 0
    for f in existing_findings:
        if f.id.startswith("F") and f.id[1:].isdigit():
            start = max(start, int(f.id[1:]))

    counter = {"n": start}

    def next_id() -> str:
        counter["n"] += 1
        return f"F{counter['n']:03d}"

    return next_id


def _priority_lists(findings) -> tuple[list[str], list[str], list[str]]:
    must_fix = [f.id for f in findings if f.priority == PriorityBucket.MUST_FIX]
    strongly = [f.id for f in findings if f.priority == PriorityBucket.STRONGLY_RECOMMENDED]
    optional = [f.id for f in findings if f.priority == PriorityBucket.OPTIONAL_POLISH]
    return must_fix, strongly, optional


def _not_implemented_notes(scores: Scores, jd_match: Optional[JDMatchResult]) -> list[str]:
    notes = []
    for score in scores.model_dump().values():
        if score["status"] != "computed":
            notes.append(f"{score['label']}: {score['status']} -- {score.get('explanation') or ''}".strip(" -"))
    if jd_match is not None and jd_match.status != "computed":
        notes.append(f"JD Requirement Coverage Matrix: {jd_match.status} -- {jd_match.explanation or ''}".strip(" -"))
    notes.append("Exports other than the JSON analysis report: not yet implemented.")
    return notes


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze(
    file: UploadFile = File(...),
    industry: Optional[str] = Form(None),
    career_path: Optional[str] = Form(None),
    target_role: Optional[str] = Form(None),
    seniority: Optional[str] = Form(None),
    target_company: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    background_notes: Optional[str] = Form(None),
):
    content = await file.read()
    try:
        stored = store_upload(file.filename or "resume", content)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    target = TargetProfile(
        industry=industry,
        career_path=career_path,
        target_role=target_role,
        seniority=seniority,
        target_company=target_company,
        job_description=job_description,
        background_notes=background_notes,
    )

    render_dir = UPLOAD_DIR / stored.file_id / "pages"

    if stored.file_type == "pdf":
        ctx = build_pdf_context(stored.path)
        pages_raw = pdf_renderer.render_pages(stored.path, render_dir)
        pages = [
            PageInfo(page_number=p["page_number"], width=p["width"], height=p["height"], image_path=p["image_path"])
            for p in pages_raw
        ]
        docx_html = None
    else:
        # Render DOCX to HTML first so it can double as the second
        # extraction method for comparison.
        render_result = docx_renderer.render_html(stored.path)
        docx_html = render_result["html"]
        ctx = build_docx_context(stored.path, docx_html=docx_html)
        pages = []

    findings, contact = run_rules(ctx)

    next_id = _make_id_continuation(findings)

    # Phase 8 core: deterministic keyword coverage, always runs (free).
    keyword_coverage, keyword_findings, relevant_keyword_categories = run_keyword_engine(ctx.full_text, target, next_id)
    findings += keyword_findings

    # Phase 7: ownership-verb scan always runs (free); LLM bullet-quality
    # depth added internally when configured -- never raises past this call.
    pm_positioning_data, pm_findings = run_pm_positioning(ctx.full_text, target, next_id)
    findings += pm_findings

    # Recruiter Readability, deterministic half: bullshit/redundancy
    # detectors always run (free) -- never gated on an API key.
    readability_data, readability_findings = run_readability_scan(ctx.full_text, next_id)
    findings += readability_findings

    # Target Role Alignment, deterministic half: role-taxonomy terminology
    # fit against the free-text Target Role field, if it matches a known
    # role -- always free, no API key needed. None if no target role was
    # entered or it didn't match any known role profile.
    role_alignment_data, role_alignment_findings = compute_role_alignment(keyword_coverage, target.target_role, next_id)
    findings += role_alignment_findings

    # Phase 6: career narrative / seniority / summary --
    # fully LLM-gated, degrades cleanly to "not configured" or "llm_error".
    # Also adds qualitative depth on top of Target Role Alignment and
    # Recruiter Readability's deterministic halves above when configured.
    positioning_result: Optional[dict] = None
    positioning_error: Optional[str] = None
    if LLM_ENABLED:
        try:
            positioning_result, positioning_findings = evaluate_positioning(ctx.full_text, target, next_id)
            findings += positioning_findings
        except LLMNotConfiguredError as exc:
            positioning_error = str(exc)
        except LLMCallError as exc:
            positioning_error = str(exc)

    # Phase 8 JD mode: only attempted when a JD was actually pasted.
    jd_match: Optional[JDMatchResult] = None
    if job_description and job_description.strip():
        if LLM_ENABLED:
            try:
                jd_match = build_requirement_coverage_matrix(ctx.full_text, target)
            except (LLMNotConfiguredError, LLMCallError) as exc:
                jd_match = JDMatchResult(status="llm_error", explanation=str(exc))
        else:
            jd_match = JDMatchResult(status="not yet implemented", explanation=_NOT_CONFIGURED_NOTE)

    scores = compute_scores(
        findings=findings,
        comparison=ctx.extraction_comparison,
        contact=contact,
        keyword_coverage=keyword_coverage,
        relevant_keyword_categories=relevant_keyword_categories,
        pm_positioning_data=pm_positioning_data,
        role_alignment_data=role_alignment_data,
        readability_data=readability_data,
        positioning_result=positioning_result,
        positioning_error=positioning_error,
        llm_model=LLM_MODEL,
    )
    must_fix, strongly_recommended, optional_polish = _priority_lists(findings)

    document = DocumentInfo(
        file_id=stored.file_id,
        original_filename=stored.original_filename,
        file_type=stored.file_type,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        page_count=len(pages) if pages else 1,
        pages=pages,
        docx_html=docx_html,
    )

    overlays_raw = build_overlays(findings, pages)
    overlays = {str(k): v for k, v in overlays_raw.items()}

    result = AnalysisResult(
        document=document,
        target_profile=target,
        parsing=ctx.extraction_comparison,
        contact_info=contact,
        findings=findings,
        scores=scores,
        must_fix=must_fix,
        strongly_recommended=strongly_recommended,
        optional_polish=optional_polish,
        not_yet_implemented=_not_implemented_notes(scores, jd_match),
        overlays=overlays,
        keyword_coverage=keyword_coverage,
        jd_match=jd_match,
    )

    _ANALYSIS_CACHE[stored.file_id] = result
    return result


@app.get("/api/pages/{file_id}/{name}")
def get_page_image(file_id: str, name: str):
    if not _SAFE_FILE_ID_RE.match(file_id) or not _SAFE_IMAGE_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid file_id or image name.")
    path = UPLOAD_DIR / file_id / "pages" / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Page image not found.")
    return FileResponse(path)


@app.get("/api/export/{file_id}/json")
def export_json(file_id: str):
    result = _ANALYSIS_CACHE.get(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No cached analysis for this file_id. Re-run /api/analyze.")
    payload = json_export.to_json_report(result)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="analysis-{file_id}.json"'},
    )


_STUB_EXPORTS = {
    "annotated-pdf": export_stubs.annotated_pdf_export,
    "rewrite": export_stubs.rewrite_export,
    "change-log": export_stubs.change_log_export,
    "ats-safe": export_stubs.ats_safe_version_export,
    "human-optimized": export_stubs.human_optimized_version_export,
    "target-job-specific": export_stubs.target_job_specific_version_export,
}


@app.get("/api/export/{file_id}/{kind}")
def export_stub(file_id: str, kind: str):
    if kind not in _STUB_EXPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown export kind '{kind}'.")
    result = _ANALYSIS_CACHE.get(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No cached analysis for this file_id. Re-run /api/analyze.")
    try:
        _STUB_EXPORTS[kind](result)
    except NotImplementedError as exc:
        return JSONResponse(status_code=501, content={"detail": str(exc)})
