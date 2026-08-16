from app.career_engine.role_alignment import compute_role_alignment, match_role_profile
from app.keyword_engine.matcher import run_keyword_engine
from app.models import TargetProfile


def _next_id():
    counter = {"n": 0}

    def f():
        counter["n"] += 1
        return f"F{counter['n']:03d}"

    return f


def test_alias_matching_handles_seniority_prefix():
    profile = match_role_profile("Senior Technical Program Manager")
    assert profile is not None
    assert profile.key == "technical_program_manager"


def test_alias_matching_handles_abbreviation():
    profile = match_role_profile("TPM")
    assert profile is not None
    assert profile.key == "technical_program_manager"


def test_no_target_role_returns_none():
    assert match_role_profile("") is None
    assert match_role_profile(None) is None


def test_unrecognized_target_role_returns_none():
    assert match_role_profile("Underwater Basket Weaving Coordinator") is None


def test_strong_match_scores_higher_than_weak_match():
    target = TargetProfile(target_role="Quality Engineer")
    strong_text = "AS9100 Material Review Board Nonconformance report Root cause corrective action Failure modes and effects analysis Supplier quality First article inspection"
    weak_text = "Coordinated some meetings about quality topics occasionally."

    coverage_strong, _, _ = run_keyword_engine(strong_text, target, _next_id())
    coverage_weak, _, _ = run_keyword_engine(weak_text, target, _next_id())

    result_strong, _ = compute_role_alignment(coverage_strong, "Quality Engineer", _next_id())
    result_weak, findings_weak = compute_role_alignment(coverage_weak, "Quality Engineer", _next_id())

    assert result_strong["score"] > result_weak["score"]
    assert result_strong["matched_role_label"] == "Quality Engineer"
    assert findings_weak  # weak match should surface a tailoring-gap finding


def test_no_target_role_produces_no_result_or_findings():
    target = TargetProfile()
    coverage, _, _ = run_keyword_engine("Some resume text.", target, _next_id())
    result, findings = compute_role_alignment(coverage, None, _next_id())
    assert result is None
    assert findings == []
