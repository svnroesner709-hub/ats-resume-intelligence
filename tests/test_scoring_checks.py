from tests.fixtures.generate_fixtures import FIXTURES_DIR

from app.aerospace_engine.engine import run_pm_positioning
from app.ats_engine.engine import build_pdf_context, run_rules
from app.career_engine.readability_scan import run_readability_scan
from app.career_engine.role_alignment import compute_role_alignment
from app.keyword_engine.matcher import run_keyword_engine
from app.models import TargetProfile
from app.scoring.engine import compute_scores


def _next_id():
    counter = {"n": 0}

    def f():
        counter["n"] += 1
        return f"F{counter['n']:03d}"

    return f


def _run_pipeline(fixture_name: str, target: TargetProfile):
    next_id = _next_id()
    ctx = build_pdf_context(FIXTURES_DIR / fixture_name)
    findings, contact = run_rules(ctx)
    coverage, kw_findings, relevant = run_keyword_engine(ctx.full_text, target, next_id)
    findings += kw_findings
    pm_data, pm_findings = run_pm_positioning(ctx.full_text, target, next_id)
    findings += pm_findings
    readability_data, readability_findings = run_readability_scan(ctx.full_text, next_id)
    findings += readability_findings
    role_alignment_data, role_alignment_findings = compute_role_alignment(coverage, target.target_role, next_id)
    findings += role_alignment_findings
    scores = compute_scores(
        findings=findings, comparison=ctx.extraction_comparison, contact=contact,
        keyword_coverage=coverage, relevant_keyword_categories=relevant,
        pm_positioning_data=pm_data, role_alignment_data=role_alignment_data, readability_data=readability_data,
        positioning_result=None, positioning_error=None,
        llm_model="claude-sonnet-5",
    )
    return scores


def test_clean_baseline_structural_checks_all_pass():
    scores = _run_pipeline("clean_baseline.pdf", TargetProfile())
    structural = scores.ats_structural_compatibility
    assert structural.value == 100
    assert len(structural.checks) == 11
    assert all(c.passed for c in structural.checks)


def test_two_column_structural_check_fails_single_column():
    scores = _run_pipeline("two_column.pdf", TargetProfile())
    structural = scores.ats_structural_compatibility
    column_check = next(c for c in structural.checks if c.name == "Single-column layout")
    assert column_check.passed is False
    assert structural.value < 100


def test_parsing_reliability_score_equals_check_pass_rate():
    scores = _run_pipeline("clean_baseline.pdf", TargetProfile())
    parsing = scores.ats_parsing_reliability
    expected = round(100 * sum(1 for c in parsing.checks if c.passed) / len(parsing.checks))
    assert parsing.value == expected


def test_every_check_carries_a_source_citation():
    scores = _run_pipeline("clean_baseline.pdf", TargetProfile())
    for score in (scores.ats_parsing_reliability, scores.ats_structural_compatibility, scores.aerospace_keyword_coverage):
        for check in score.checks:
            assert check.source is not None
            assert check.source.confidence == "E"
