from tests.fixtures.generate_fixtures import FIXTURES_DIR

from app.ats_engine.engine import build_pdf_context
from app.keyword_engine.matcher import run_keyword_engine
from app.models import TargetProfile


def _next_id():
    counter = {"n": 0}

    def f():
        counter["n"] += 1
        return f"F{counter['n']:03d}"

    return f


def test_dictionary_match_finds_full_phrase_terms():
    ctx = build_pdf_context(FIXTURES_DIR / "clean_baseline.pdf")
    target = TargetProfile(industry="Aerospace / Defense", career_path="Program Management")
    coverage, findings, relevant = run_keyword_engine(ctx.full_text, target, _next_id())

    matched_terms = {m.term for m in coverage.matched}
    assert "Program manager" in matched_terms
    assert "Earned value management" in matched_terms
    assert all(m.via == "dictionary" for m in coverage.matched)


def test_short_abbreviation_is_case_sensitive_no_false_positive():
    """Regression test: 'TO' (Task order) must not match the common word
    'to' in ordinary sentences -- caught during manual verification."""
    ctx = build_pdf_context(FIXTURES_DIR / "clean_baseline.pdf")
    target = TargetProfile()
    coverage, findings, relevant = run_keyword_engine(ctx.full_text, target, _next_id())

    matched_terms = {m.term for m in coverage.matched}
    assert "Task order" not in matched_terms, "short abbreviation 'TO' false-positived against ordinary lowercase 'to'"


def test_category_coverage_ratios_are_consistent():
    ctx = build_pdf_context(FIXTURES_DIR / "clean_baseline.pdf")
    target = TargetProfile(industry="Aerospace / Defense", career_path="Program Management")
    coverage, findings, relevant = run_keyword_engine(ctx.full_text, target, _next_id())

    for cat in coverage.categories:
        assert 0 <= cat.matched_terms <= cat.total_terms
        expected_ratio = round(cat.matched_terms / cat.total_terms, 3) if cat.total_terms else 0.0
        assert cat.coverage_ratio == expected_ratio


def test_relevant_categories_include_target_hints():
    target = TargetProfile(industry="Aerospace / Defense", career_path="Program Management")
    ctx = build_pdf_context(FIXTURES_DIR / "clean_baseline.pdf")
    _, _, relevant = run_keyword_engine(ctx.full_text, target, _next_id())
    assert "aerospace_defense" in relevant
    assert "program_management" in relevant


def test_no_target_info_falls_back_to_all_categories():
    target = TargetProfile()
    ctx = build_pdf_context(FIXTURES_DIR / "clean_baseline.pdf")
    _, _, relevant = run_keyword_engine(ctx.full_text, target, _next_id())
    assert len(relevant) == 6  # all category files
