from tests.fixtures.generate_fixtures import FIXTURES_DIR

from app.ats_engine.engine import build_docx_context, build_pdf_context, run_rules
from app.document_rendering import docx_renderer
from app.models import Severity


def _finding_titles(findings):
    return [f.title for f in findings]


def test_clean_baseline_has_no_red_or_orange_findings():
    ctx = build_pdf_context(FIXTURES_DIR / "clean_baseline.pdf")
    findings, contact = run_rules(ctx)

    bad = [f for f in findings if f.severity in (Severity.RED, Severity.ORANGE)]
    assert bad == [], f"Unexpected RED/ORANGE findings on the clean baseline: {[(f.title, f.severity) for f in bad]}"
    assert contact.email == "jane.doe@example.com"
    assert contact.phone is not None
    assert contact.found_in_header_or_footer is False


def test_two_column_pdf_flags_multi_column():
    ctx = build_pdf_context(FIXTURES_DIR / "two_column.pdf")
    findings, _ = run_rules(ctx)
    titles = _finding_titles(findings)
    assert any("multi-column" in t.lower() or "multi column" in t.lower() for t in titles)


def test_image_only_pdf_flags_missing_text_layer():
    ctx = build_pdf_context(FIXTURES_DIR / "image_only.pdf")
    findings, _ = run_rules(ctx)
    titles = _finding_titles(findings)
    assert any("no extractable text layer" in t.lower() for t in titles)
    red_findings = [f for f in findings if f.severity == Severity.RED]
    assert red_findings, "Image-only page should produce at least one RED finding."


def test_docx_table_flags_table_finding():
    path = FIXTURES_DIR / "table_resume.docx"
    render = docx_renderer.render_html(path)
    ctx = build_docx_context(path, docx_html=render["html"])
    findings, _ = run_rules(ctx)
    titles = _finding_titles(findings)
    assert any("table detected" in t.lower() for t in titles)


def test_docx_header_footer_only_contact_flagged():
    path = FIXTURES_DIR / "header_footer_contact.docx"
    render = docx_renderer.render_html(path)
    ctx = build_docx_context(path, docx_html=render["html"])
    findings, contact = run_rules(ctx)
    assert contact.found_in_header_or_footer is True
    titles = _finding_titles(findings)
    assert any("header/footer" in t.lower() for t in titles)


def test_docx_hidden_text_flagged_as_red():
    path = FIXTURES_DIR / "hidden_text.docx"
    render = docx_renderer.render_html(path)
    ctx = build_docx_context(path, docx_html=render["html"])
    findings, _ = run_rules(ctx)
    hidden_findings = [f for f in findings if "hidden" in f.title.lower() or "white-on-white" in f.title.lower()]
    assert hidden_findings, "Expected a finding about hidden/white text."
    assert all(f.severity == Severity.RED for f in hidden_findings)
