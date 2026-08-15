# ATS Resume Intelligence

A deterministic, evidence-driven resume parsing and ATS-compatibility analysis tool, purpose-built for aerospace/defense program-management career positioning. Not a generic "paste your resume into a chatbot" tool -- a real parsing pipeline (multiple independent extraction engines, cross-compared) feeding a real, source-cited rule engine, behind a local GUI that overlays findings directly on the rendered document.

**Status: foundational MVP.** This build implements Phases 1-5 of the full design (see "Phase status" below) for real. Career positioning, aerospace/PM terminology scoring, keyword/JD matching, and export formats beyond JSON are intentionally scaffolded but not implemented -- see "What's not implemented yet."

## Quickstart

```bash
py -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m pytest
venv\Scripts\python -m uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 in a browser, drag in a `.pdf` or `.docx` resume, and (optionally) fill in target-role fields before clicking **Analyze Resume**.

## Phase status

| Phase | What it covers | Status |
|---|---|---|
| 1 | PDF/DOCX ingestion | ✅ Implemented |
| 2 | Multi-method extraction + reading-order comparison | ✅ Implemented (PyMuPDF + pdfplumber + pdfminer.six for PDF; python-docx + mammoth-HTML for DOCX) |
| 3 | Document viewer | ✅ Implemented (server-rendered PDF page PNGs; mammoth HTML for DOCX) |
| 4 | Highlight/annotation engine | ✅ Implemented for findings with known page geometry (not every finding has a natural bounding box -- see below) |
| 5 | ATS structural rule engine | ✅ Implemented: columns, tables, text boxes (DOCX), hidden/white text (DOCX), header/footer-only contact info, uncommon fonts, missing section headings, contact-field completeness |
| 6 | Career narrative / seniority / summary evaluation | 🚧 Scaffolded, not implemented (`app/career_engine/`) |
| 7 | Aerospace + Program Management specialization, bullet strength | 🚧 Scaffolded, not implemented (`app/aerospace_engine/`) |
| 8 | Keyword/semantic matching, JD Requirement Coverage Matrix | 🚧 Scaffolded, not implemented (`app/keyword_engine/`, `app/jd_matching/`) |
| 9 | External research / live-sourced ATS citations | 🚧 Scaffolded, not implemented (`app/research/`) -- all current knowledge-base citations are honestly labeled Level E (internal heuristic) |
| 10 | Exports & version comparison | Partial: JSON analysis report ✅. Annotated PDF, rewrite, ATS-safe/human-optimized/target-job-specific versions, and version comparison are 🚧 stubs (`app/exports/stubs.py`) |

## Why only two real scores

`ATS Parsing Reliability` and `ATS Structural Compatibility` are the only scores with a `status: "computed"` value. Every other score in the schema (`Target Role Alignment`, `Aerospace Keyword Coverage`, `Program Management Positioning`, `Recruiter Readability`, `Executive/Seniority Signal`, `Overall Resume Strength`) is `null` with `status: "not yet implemented"` -- by design. Faking those with a plausible-looking number would violate the whole point of this tool (evidence over assertion). They light up once Phases 6-9 are built.

## Source confidence

Every structural finding carries a `confidence` level (A-E, see `app/models.py::SourceConfidence`). **All rules currently seeded in `app/knowledge_base/` are honestly labeled Level E** ("internal heuristic," i.e. restated general industry convention, not a citation this build actually fetched). Level A/B/C claims require `app/research/` (Phase 9) to actually run and record a real source with a URL and access date -- that module is a stub. Don't hand-edit a rule's confidence level upward without recording a real source in `app/knowledge_base/ats_rules/structural_rules.json`.

## Architecture

```
app/
  ingestion/            Phase 1: upload validation, storage, hashing
  parsers/               Phase 1-2: 3 independent PDF extractors + DOCX parser + comparison
  document_rendering/    Phase 3: PDF page->PNG, DOCX->HTML (mammoth)
  ats_engine/             Phase 5: the structural rule engine (this is the real analytical core)
  formatting_engine/     Mostly stub -- see module docstring
  career_engine/         Stub -- Phase 6
  aerospace_engine/      Stub -- Phase 7
  keyword_engine/        Stub -- Phase 8
  jd_matching/           Stub -- Phase 8 (JD mode)
  research/              Stub -- Phase 9
  knowledge_base/        JSON-backed rule/term seed data
  scoring/               Computes only the 2 implemented scores; explicit nulls for the rest
  annotation/             Phase 4: Finding -> overlay geometry
  exports/               JSON report (implemented) + stubs for everything else
  models.py              Pydantic schema shared by backend + GUI
  main.py                FastAPI app
static/                 Vanilla HTML/CSS/JS GUI (no build step, no CDN dependency)
tests/                   pytest suite against generated synthetic fixtures (no real resumes ever committed)
data/uploads/            gitignored -- runtime-only, never committed
```

## Known limitations (MVP-scoped, not bugs)

- PDF "header/footer" detection is a **position heuristic** (top/bottom ~10% of the page), not a structural fact -- PDFs have no formal header/footer container the way DOCX does. A resume with its name/contact block sitting very close to the physical top edge can trigger this even if it's just normal content.
- Text-box and hidden/white-text detection currently only run on DOCX (the underlying XML gives a clean signal; PDF text boxes just look like ordinary text blocks at the extraction layer, so there's no reliable PDF-side signal yet).
- Name extraction is a best-effort first-line heuristic, explicitly flagged as low-confidence, not a certain read.
- The analysis cache (for exports) is in-memory only -- restarting the server clears it. Fine for a local single-user tool; would need real persistence before any multi-user use.
- No GitHub remote has been created for this repo yet -- that's a deliberate separate step, done only when explicitly requested.

## Tests

```bash
venv\Scripts\python -m pytest -v
```

Fixtures are generated (not hand-written) by `tests/fixtures/generate_fixtures.py` -- every name/email/employer in them is fictional. They cover: a clean single-column baseline (expected: zero RED/ORANGE findings), a two-column layout, an image-only/scanned PDF, a DOCX with a table, a DOCX with contact info only in the header, and a DOCX with hidden + white-on-white text.
