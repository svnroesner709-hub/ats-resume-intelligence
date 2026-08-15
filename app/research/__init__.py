"""
STUB -- Phase 9, spec "EXTERNAL BENCHMARKING AND VALIDATION" and "SOURCE
CONFIDENCE MODEL".

Will own: live WebFetch/WebSearch lookups against reputable ATS/recruiting
guidance sources, recorded as SourceCitation entries (see models.py) with
a real url + date_accessed, replacing the honestly-labeled Level E
placeholders currently seeded in knowledge_base/ats_rules/structural_rules.json.

Hard rule carried over from the spec: never claim a resume was "tested
against Workday" (etc.) unless an actual test was run. This module is
where that distinction (actual test vs. inferred-from-guidance vs.
internal heuristic) gets enforced for real, once built.
"""
from __future__ import annotations


def refresh_source_citations(rule_id: str) -> list[dict]:
    raise NotImplementedError(
        "research.refresh_source_citations is not yet implemented. "
        "All current knowledge_base citations remain Level E (internal heuristic) until this exists."
    )
