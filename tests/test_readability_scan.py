from app.career_engine.readability_scan import run_readability_scan, scan_readability


def _next_id():
    counter = {"n": 0}

    def f():
        counter["n"] += 1
        return f"F{counter['n']:03d}"

    return f


def test_buzzword_without_evidence_is_flagged():
    text = "- Results-driven professional with a proven track record."
    result = scan_readability(text)
    assert len(result.buzzword_hits) == 1
    assert result.buzzword_hits[0].phrase == "results-driven professional"


def test_buzzword_with_adjacent_number_is_not_flagged():
    """Spec: flag generic phrases 'unless followed by substantive evidence'."""
    text = "- Team player who delivered $4M in cost savings."
    result = scan_readability(text)
    assert result.buzzword_hits == []


def test_redundant_generic_verb_flagged_at_threshold():
    text = "\n".join([f"- Managed task {i}." for i in range(4)])
    result = scan_readability(text)
    assert len(result.redundant_verbs) == 1
    assert result.redundant_verbs[0].verb == "managed"
    assert result.redundant_verbs[0].count == 4


def test_precise_domain_verb_never_flagged_even_if_repeated():
    """Spec: don't suggest variation for precise terminology, only generic verbs."""
    text = "\n".join([f"- Qualified component {i} to spec." for i in range(6)])
    result = scan_readability(text)
    assert result.redundant_verbs == []


def test_run_readability_scan_builds_findings_and_dict():
    text = "- Results-driven professional.\n" + "\n".join(f"- Managed thing {i}." for i in range(4))
    data, findings = run_readability_scan(text, _next_id())
    assert data["buzzword_hits"]
    assert data["redundant_verbs"]
    assert len(findings) == 2  # one buzzword finding + one redundancy finding
    assert all(f.category.value == "career_positioning" for f in findings)


def test_clean_text_produces_no_findings():
    text = "- Directed a $4M propulsion recovery effort.\n- Led the qualification test campaign."
    data, findings = run_readability_scan(text, _next_id())
    assert data["buzzword_hits"] == []
    assert data["redundant_verbs"] == []
    assert findings == []
