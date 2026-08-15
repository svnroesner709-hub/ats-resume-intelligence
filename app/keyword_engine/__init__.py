"""
STUB -- Phase 8, spec Layer 9 ("Keyword and Semantic Matching").

Will own: exact/abbreviation/expanded/semantic-equivalent keyword matching
between resume content and a target role's typical terminology (or a
supplied job description, in which case jd_matching.py takes over the
matrix construction). Deliberately more than simple keyword counting --
needs semantic-equivalence judgment, so it's LLM-assisted, not a pure
rule engine, and is deferred past this MVP.
"""
from __future__ import annotations

from app.models import TargetProfile


def match_keywords(full_text: str, target: TargetProfile) -> dict:
    raise NotImplementedError(
        "keyword_engine.match_keywords is not yet implemented. "
        "Aerospace Keyword Coverage / Target Role Alignment scores are "
        "reported as status='not yet implemented' until this exists."
    )
