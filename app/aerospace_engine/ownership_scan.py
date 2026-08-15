"""
Deterministic half of Layer 7 (Program Management Specialization): scans
resume lines for weak-participation vs. ownership-language verbs at the
start of each line/bullet, using the expanded verb bank in
app/knowledge_base/keywords/ownership_verbs.json.

Works with NO API key -- this always contributes at least a partial
Program Management Positioning score; app/aerospace_engine/engine.py adds
LLM-powered bullet-quality depth on top of this when configured.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.knowledge_base.loader import ownership_verbs, weak_participation_verbs

_BULLET_PREFIX_RE = re.compile(r"^[\-•●▪\*–—]\s*")
_LEADING_VERB_RE = re.compile(r"^([A-Za-z][A-Za-z\-]*)\b")


@dataclass
class VerbHit:
    line: str
    verb: str


@dataclass
class OwnershipScanResult:
    ownership_hits: list[VerbHit] = field(default_factory=list)
    weak_hits: list[VerbHit] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.ownership_hits) + len(self.weak_hits)

    @property
    def ownership_ratio(self) -> float | None:
        if self.total == 0:
            return None
        return len(self.ownership_hits) / self.total


def scan_ownership_language(full_text: str) -> OwnershipScanResult:
    ownership_set = {v.lower() for v in ownership_verbs()}
    weak_set = {v.lower() for v in weak_participation_verbs()}
    # Sort multi-word phrases longest-first so "responsible for" is checked
    # before a shorter accidental prefix match.
    weak_phrases = sorted(weak_set, key=len, reverse=True)

    result = OwnershipScanResult()

    for raw_line in full_text.splitlines():
        line = _BULLET_PREFIX_RE.sub("", raw_line.strip())
        if not line:
            continue
        lowered = line.lower()

        weak_match = next((p for p in weak_phrases if lowered.startswith(p)), None)
        if weak_match:
            result.weak_hits.append(VerbHit(line=line, verb=weak_match))
            continue

        verb_match = _LEADING_VERB_RE.match(lowered)
        if verb_match and verb_match.group(1) in ownership_set:
            result.ownership_hits.append(VerbHit(line=line, verb=verb_match.group(1)))

    return result
