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


def test_jd_sweep_terms_carry_level_c_sourcing():
    """Terms confirmed against the 2026-08-15 real-job-posting sweep
    (scripts/apply_jd_sweep.py) should report Level C with real sources,
    not the Level E database default."""
    text = "Managed AS9100 quality systems and maintained the Integrated Master Schedule (IMS) for the program."
    target = TargetProfile()
    coverage, _, _ = run_keyword_engine(text, target, _next_id())

    as9100 = next(m for m in coverage.matched if m.term == "AS9100")
    assert as9100.confidence == "C"
    assert len(as9100.sources) >= 1
    assert as9100.sources[0].url.startswith("http")

    ims = next(m for m in coverage.matched if m.term == "Integrated master schedule")
    assert ims.confidence == "C"


def test_bulk_acronym_library_terms_are_matched():
    """Regression test: FEA and BoE were reported missing entirely from the
    database -- both come from the plain-text bulk acronym library
    (app/knowledge_base/keywords/acronyms_bulk.txt), not the JSON files."""
    text = "Performed FEA on the bracket assembly and developed a BoE for the propulsion upgrade."
    target = TargetProfile()
    coverage, _, _ = run_keyword_engine(text, target, _next_id())

    matched_terms = {m.term for m in coverage.matched}
    assert "Finite Element Analysis" in matched_terms
    assert "Basis of Estimate" in matched_terms


def test_bulk_acronym_library_is_substantial():
    from app.knowledge_base.loader import keyword_database

    total_terms = sum(len(c.terms) for c in keyword_database())
    assert total_terms >= 350, "expected the bulk acronym library to meaningfully expand database size"
