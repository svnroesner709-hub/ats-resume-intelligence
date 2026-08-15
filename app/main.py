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
from app.ats_engine.engine import build_docx_context, build_pdf_context, run_rules
from app.document_rendering import docx_renderer, pdf_renderer
from app.exports import json_export, stubs as export_stubs
from app.ingestion.upload import FileTooLarge, UnsupportedFileType, store_upload
from app.models import (
    AnalysisResult,
    DocumentInfo,
    PageInfo,
    PriorityBucket,
    Scores,
    TargetProfile,
)
from app.scoring.engine import compute_scores

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


def _priority_lists(findings) -> tuple[list[str], list[str], list[str]]:
    must_fix = [f.id for f in findings if f.priority == PriorityBucket.MUST_FIX]
    strongly = [f.id for f in findings if f.priority == PriorityBucket.STRONGLY_RECOMMENDED]
    optional = [f.id for f in findings if f.priority == PriorityBucket.OPTIONAL_POLISH]
    return must_fix, strongly, optional


def _not_implemented_notes(scores: Scores) -> list[str]:
    notes = []
    for score in scores.model_dump().values():
        if score["status"] != "computed":
            notes.append(f"{score['label']}: not yet implemented.")
    notes.append("Job-description matching (Requirement Coverage Matrix): not yet implemented.")
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
    scores = compute_scores(findings, ctx.extraction_comparison)
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
        not_yet_implemented=_not_implemented_notes(scores),
        overlays=overlays,
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
