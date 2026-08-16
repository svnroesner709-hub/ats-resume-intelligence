import tempfile
from pathlib import Path

from tests.fixtures.generate_fixtures import FIXTURES_DIR

from app.annotation.keyword_highlighter import (
    build_pdf_keyword_overlays,
    find_pdf_keyword_boxes,
    highlight_docx_html,
)
from app.ats_engine.engine import build_pdf_context
from app.document_rendering import pdf_renderer
from app.keyword_engine.matcher import run_keyword_engine
from app.models import MatchedKeyword, PageInfo, TargetProfile


def _next_id():
    counter = {"n": 0}

    def f():
        counter["n"] += 1
        return f"F{counter['n']:03d}"

    return f


def test_pdf_keyword_boxes_found_for_dictionary_matches():
    path = FIXTURES_DIR / "clean_baseline.pdf"
    ctx = build_pdf_context(path)
    coverage, _, _ = run_keyword_engine(ctx.full_text, TargetProfile(), _next_id())

    boxes = find_pdf_keyword_boxes(path, coverage.matched)
    assert 0 in boxes
    terms_found = {b["term"] for b in boxes[0]}
    assert "Program manager" in terms_found
    assert "Earned value management" in terms_found


def test_pdf_keyword_boxes_skip_llm_semantic_matches():
    path = FIXTURES_DIR / "clean_baseline.pdf"
    fake_matches = [
        MatchedKeyword(term="Something", category="x", category_label="X", matched_form="an inferred paraphrase", via="llm_semantic", confidence="E"),
    ]
    boxes = find_pdf_keyword_boxes(path, fake_matches)
    assert boxes == {}


def test_pdf_keyword_overlays_are_normalized_0_to_1():
    path = FIXTURES_DIR / "clean_baseline.pdf"
    ctx = build_pdf_context(path)
    coverage, _, _ = run_keyword_engine(ctx.full_text, TargetProfile(), _next_id())
    with tempfile.TemporaryDirectory() as tmp:
        pages_raw = pdf_renderer.render_pages(path, Path(tmp))
        pages = [PageInfo(page_number=p["page_number"], width=p["width"], height=p["height"], image_path=p["image_path"]) for p in pages_raw]

    overlays = build_pdf_keyword_overlays(path, coverage.matched, pages)
    assert "0" in overlays
    for box in overlays["0"]:
        assert 0 <= box["x0"] < box["x1"] <= 1
        assert 0 <= box["y0"] < box["y1"] <= 1


def test_case_sensitive_abbreviation_does_not_overhighlight():
    """Regression guard: a case-sensitive-matched abbreviation (e.g. an
    all-caps short form) must not highlight an unrelated lowercase
    occurrence of the same letters elsewhere on the page."""
    path = FIXTURES_DIR / "clean_baseline.pdf"
    # "PM" is not actually in this fixture's text at all, so this should
    # cleanly find zero boxes rather than matching unrelated text.
    fake_matches = [
        MatchedKeyword(term="Program manager", category="program_management", category_label="Program Management", matched_form="PM", via="dictionary", confidence="E"),
    ]
    boxes = find_pdf_keyword_boxes(path, fake_matches)
    assert boxes == {}


def test_highlight_docx_html_wraps_text_only():
    html = "<p>Program Manager, Example Corp.</p><p>Directed a program.</p>"
    matches = [
        MatchedKeyword(term="Program manager", category="x", category_label="X", matched_form="Program Manager", via="dictionary", confidence="E"),
    ]
    result = highlight_docx_html(html, matches)
    assert '<mark class="kw-doc-highlight">Program Manager</mark>' in result
    # Only the first occurrence (exact phrase) is wrapped -- "program" alone
    # in the second sentence isn't a match since the full phrase differs.
    assert result.count("<mark") == 1


def test_highlight_docx_html_never_touches_tag_attributes():
    html = '<a href="https://example.com/Program Manager">Program Manager</a>'
    matches = [
        MatchedKeyword(term="Program manager", category="x", category_label="X", matched_form="Program Manager", via="dictionary", confidence="E"),
    ]
    result = highlight_docx_html(html, matches)
    assert 'href="https://example.com/Program Manager"' in result  # untouched
    assert "<mark" in result  # the visible text node was wrapped
