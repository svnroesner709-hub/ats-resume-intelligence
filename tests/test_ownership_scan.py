from app.aerospace_engine.ownership_scan import scan_ownership_language


def test_ownership_verb_detected_at_line_start():
    text = "- Directed a cross-functional team of 12 engineers.\n- Led the recovery of a delayed subsystem."
    result = scan_ownership_language(text)
    assert len(result.ownership_hits) == 2
    assert len(result.weak_hits) == 0
    assert result.ownership_ratio == 1.0


def test_weak_verb_detected_at_line_start():
    text = "- Helped the team with testing.\n- Assisted with supplier coordination."
    result = scan_ownership_language(text)
    assert len(result.weak_hits) == 2
    assert len(result.ownership_hits) == 0
    assert result.ownership_ratio == 0.0


def test_mixed_verbs_ratio():
    text = "- Directed the program.\n- Helped with reporting.\n- Owned the budget."
    result = scan_ownership_language(text)
    assert len(result.ownership_hits) == 2
    assert len(result.weak_hits) == 1
    assert abs(result.ownership_ratio - (2 / 3)) < 1e-9


def test_no_bullets_returns_none_ratio():
    result = scan_ownership_language("")
    assert result.ownership_ratio is None
    assert result.total == 0


def test_multi_word_weak_phrase_matched_over_shorter_prefix():
    # "responsible for" should match as the weak phrase, not be missed
    # because a shorter, unrelated prefix happens to match first.
    text = "- Responsible for coordinating supplier reviews."
    result = scan_ownership_language(text)
    assert len(result.weak_hits) == 1
    assert result.weak_hits[0].verb == "responsible for"
