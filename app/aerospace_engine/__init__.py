"""
STUB -- Phase 7, spec Layers 6 ("Aerospace/Defense Specialization"), 7
("Program Management Specialization"), 8 ("Accomplishment Strength").

Responsibilities this module will own once implemented:
  - Recognize aerospace/defense/PM terminology genuinely supported by the
    candidate's experience (see knowledge_base/aerospace_terms/seed_glossary.json
    and knowledge_base/program_management/seed_phrases.json -- both seeded
    but not exhaustive).
  - Flag ownership language (led/directed/delivered) vs. weak participation
    language (helped/supported/assisted) per bullet.
  - Score each bullet's Action + Scope + Technical Context + Result
    structure (Layer 8) and flag where a metric/variable is missing --
    prompting the user for the real number rather than inventing one.

Depends on real LLM-driven judgment of bullet semantics, not deterministic
rules -- intentionally deferred past this MVP. See README phase status.
"""
from __future__ import annotations

from app.models import TargetProfile


def evaluate_aerospace_pm_content(full_text: str, target: TargetProfile) -> dict:
    raise NotImplementedError(
        "aerospace_engine.evaluate_aerospace_pm_content is not yet implemented. "
        "Program Management Positioning / Aerospace Keyword Coverage scores "
        "are reported as status='not yet implemented' until this exists."
    )
