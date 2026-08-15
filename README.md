# ATS Resume Intelligence

A deterministic, evidence-driven resume parsing and ATS-compatibility analysis tool, purpose-built for aerospace/defense program-management career positioning. Not a generic "paste your resume into a chatbot" tool -- a real parsing pipeline (multiple independent extraction engines, cross-compared) feeding a real, source-cited rule engine, a large domain keyword database, and (optionally) LLM-powered career-positioning judgment -- behind a local GUI that overlays findings directly on the rendered document.

**Status.** Phases 1-5 (parsing, ATS structural rules, GUI) and Phase 8's keyword coverage are fully implemented and free (no API key needed). Phases 6-7 and JD matching add LLM-powered depth on top when `ANTHROPIC_API_KEY` is configured -- see "Phase status" and "Enabling LLM-powered scoring" below. Phase 9 (live external research/citations) and most of Phase 10 (exports beyond JSON) remain scaffolded stubs.

## Quickstart

```bash
py -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m pytest
venv\Scripts\python -m uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 in a browser, drag in a `.pdf` or `.docx` resume, and (optionally) fill in target-role fields before clicking **Analyze Resume**.

## Enabling LLM-powered scoring (optional)

Without any setup, the app fully works: Phases 1-5, deterministic Aerospace Keyword Coverage (255+ terms, 457+ matchable forms across 6 domain categories), and a deterministic partial Program Management Positioning score (ownership-vs-weak-participation verb scan) all run for free.

To additionally enable **Target Role Alignment, the LLM-scored half of Program Management Positioning, Recruiter Readability, Executive/Seniority Signal, Overall Resume Strength, and the JD Requirement Coverage Matrix**:

1. `copy .env.example .env`
2. Add your own `ANTHROPIC_API_KEY` to `.env` (never commit this file -- it's gitignored).
3. Restart `uvicorn`.

Each analysis with a key configured makes a small number of real Anthropic API calls (normal per-token usage charges apply). If the key is missing or a call fails, the affected score cleanly reports `status: "not yet implemented"` or `"llm_error"` with an explanation -- it never fakes a number, and it never breaks the rest of the analysis.

## Phase status

| Phase | What it covers | Status |
|---|---|---|
| 1 | PDF/DOCX ingestion | ✅ Implemented |
| 2 | Multi-method extraction + reading-order comparison | ✅ Implemented (PyMuPDF + pdfplumber + pdfminer.six for PDF; python-docx + mammoth-HTML for DOCX) |
| 3 | Document viewer | ✅ Implemented (server-rendered PDF page PNGs; mammoth HTML for DOCX) |
| 4 | Highlight/annotation engine | ✅ Implemented for findings with known page geometry (not every finding has a natural bounding box -- see below) |
| 5 | ATS structural rule engine | ✅ Implemented: columns, tables, text boxes (DOCX), hidden/white text (DOCX), header/footer-only contact info, uncommon fonts, missing section headings, contact-field completeness |
| 6 | Career narrative / seniority / summary / readability | ✅ Implemented, **LLM-powered** -- requires `ANTHROPIC_API_KEY` (`app/career_engine/`) |
| 7 | PM Positioning (ownership language + bullet strength) | ✅ Implemented -- deterministic ownership-verb scan always runs free; LLM adds per-bullet Action/Scope/Context/Result depth when configured (`app/aerospace_engine/`) |
| 8 | Keyword/semantic matching | ✅ Implemented -- deterministic database (255+ terms) always runs free; optional LLM semantic-enrichment pass for near-misses (`app/keyword_engine/`) |
| 8 | JD Requirement Coverage Matrix | ✅ Implemented, **LLM-powered** -- only runs when a job description is pasted and a key is configured (`app/jd_matching/`) |
| 9 | External research / live-sourced ATS citations | 🚧 Scaffolded, not implemented (`app/research/`) -- all current knowledge-base citations are honestly labeled Level E (internal heuristic, including the keyword database and LLM outputs) |
| 10 | Exports & version comparison | Partial: JSON analysis report ✅. Annotated PDF, rewrite, ATS-safe/human-optimized/target-job-specific versions, and version comparison are 🚧 stubs (`app/exports/stubs.py`) |

## Score checklists

Every computed score carries a `checks: [{name, passed, detail, source}]` list, shown in the GUI as an expandable checklist under each score row. Two different meanings, both labeled as such in each score's `explanation`:

- **Parsing Reliability, Structural Compatibility, Keyword Coverage**: the score number *is* the percentage of named checks that passed -- the checklist fully explains the number, not just illustrates it.
- **The four LLM-backed scores**: the number is the model's own holistic 0-100 rating; the checklist shows corroborating verdicts alongside it (e.g. "seniority calibration verdict"), not a formula that produced the number.

## Source confidence

Every finding and score check carries a `confidence` level (A-E, see `app/models.py::SourceConfidence`). **Everything in this build is currently Level E** -- deterministic rules and the keyword database are "internal heuristic, not yet backed by a fetched citation"; LLM-derived findings are labeled `LLM judgment (model: ...)`, explicitly distinct from a deterministic rule. Level A/B/C claims require `app/research/` (Phase 9, still a stub) to actually fetch and record a real source with a URL and access date.

## Architecture

```
app/
  ingestion/            Phase 1: upload validation, storage, hashing
  parsers/              Phase 1-2: 3 independent PDF extractors + DOCX parser + comparison
  document_rendering/   Phase 3: PDF page->PNG, DOCX->HTML (mammoth)
  ats_engine/           Phase 5: the deterministic structural rule engine
  formatting_engine/    Mostly stub -- see module docstring
  career_engine/        Phase 6, LLM-powered (app/career_engine/engine.py)
  aerospace_engine/     Phase 7: ownership_scan.py (deterministic) + engine.py (LLM bullet quality)
  keyword_engine/       Phase 8 core: matcher.py (deterministic + optional LLM enrichment)
  jd_matching/          Phase 8 JD mode, LLM-powered (engine.py)
  llm/                  Anthropic API wrapper (client.py) + tool-call schemas (schemas.py)
  config.py             .env loading, LLM_ENABLED / LLM_MODEL
  research/             Stub -- Phase 9
  knowledge_base/       JSON-backed rule/term seed data, incl. keywords/ (255+ term database)
  scoring/              Builds every score's checklist from data already computed elsewhere
  annotation/           Phase 4: Finding -> overlay geometry
  exports/              JSON report (implemented) + stubs for everything else
  models.py             Pydantic schema shared by backend + GUI
  main.py               FastAPI app -- orchestrates all engines, degrades LLM failures per-score
static/                 Vanilla HTML/CSS/JS GUI (no build step, no CDN dependency)
tests/                  pytest suite: deterministic tests + LLM tests via monkeypatched call_tool
data/uploads/           gitignored -- runtime-only, never committed
.env.example            Copy to .env and add your own ANTHROPIC_API_KEY (never commit .env)
```

## Known limitations (not bugs)

- PDF "header/footer" detection is a **position heuristic** (top/bottom ~10% of the page), not a structural fact -- PDFs have no formal header/footer container the way DOCX does.
- Text-box and hidden/white-text detection currently only run on DOCX (the underlying XML gives a clean signal; PDF text boxes have no reliable equivalent signal yet).
- Name extraction is a best-effort first-line heuristic, explicitly flagged as low-confidence.
- The analysis cache (for exports) is in-memory only -- restarting the server clears it.
- Short abbreviations (e.g. "TO" for Task order) are matched **case-sensitively** in the keyword database specifically to avoid false-positiving against common lowercase English words -- full terms/synonyms stay case-insensitive. See `app/keyword_engine/matcher.py::_forms_to_check`.
- No GitHub remote has been created for this repo yet -- that's a deliberate separate step, done only when explicitly requested.

## Tests

```bash
venv\Scripts\python -m pytest -v
```

31 tests, all free (no network calls, no API key needed). Fixtures are generated (not hand-written) by `tests/fixtures/generate_fixtures.py` -- every name/email/employer in them is fictional. `tests/test_llm_modules.py` verifies the LLM-backed modules' plumbing (Finding construction, graceful degradation) by monkeypatching `app.llm.client.call_tool` with canned responses -- it never makes a real API call.
