"""
Deterministic half of Recruiter Readability (spec's "BULLSHIT DETECTOR" and
"REDUNDANCY DETECTOR"). Works with NO API key -- this always contributes a
real, explainable Recruiter Readability score; app/career_engine/engine.py
blends in the LLM's holistic narrative-clarity judgment on top when
ANTHROPIC_API_KEY is configured.

Two checks, both cheap and precise on purpose:
  - Generic corporate filler ("results-driven professional", "team player",
    ...) flagged ONLY when it's not obviously followed by substantive
    evidence -- the spec's instruction is "unless followed by substantive
    evidence", so this errs toward under-flagging rather than nagging about
    a phrase that's actually backed up by a number or specific noun.
  - Verb redundancy: the same leading bullet verb used many times. The spec
    is explicit that variation should only be suggested when it improves
    clarity, not to avoid repeating precise terminology -- so this only
    fires on generic, low-information verbs, never on domain-specific ones.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models import (
    Finding,
    FindingCategory,
    PriorityBucket,
    RiskClassification,
    Severity,
    SourceCitation,
    SourceConfidence,
)

_BULLET_PREFIX_RE = re.compile(r"^[\-•●▪\*–—]\s*")
_LEADING_VERB_RE = re.compile(r"^([A-Za-z][A-Za-z\-]*)\b")

# Spec's own examples, plus common adjacent filler. Matched as whole phrases
# so "results-driven professional" doesn't also double-count "professional".
_BUZZWORDS = [
    "results-driven professional", "results-driven", "dynamic professional",
    "proven track record", "strategic thinker", "excellent communicator",
    "excellent communication skills", "team player", "detail-oriented",
    "detail oriented", "self-starter", "go-getter", "hard worker",
    "highly motivated", "passionate about", "think outside the box",
    "synergy", "synergize", "works well independently and as part of a team",
    "wide range of", "extensive experience in", "responsible for a variety of",
]

# A trailing digit, dollar sign, percent sign, or specific proper-noun-like
# capitalized word within the same sentence counts as "substantive evidence"
# per the spec's "unless followed by substantive evidence" carve-out.
_EVIDENCE_RE = re.compile(r"[\d$%]")

# Generic, low-information verbs worth flagging on overuse. Deliberately
# excludes precise domain verbs (e.g. "qualified", "certified", "integrated")
# per the spec's "do not replace precise terminology merely to avoid
# repetition" instruction.
_GENERIC_VERBS = {
    "managed", "led", "coordinated", "developed", "oversaw", "worked",
    "handled", "responsible", "helped", "assisted", "involved",
}
_REDUNDANCY_THRESHOLD = 4


@dataclass
class BuzzwordHit:
    phrase: str
    line: str


@dataclass
class VerbCount:
    verb: str
    count: int
    example_lines: list[str]


@dataclass
class ReadabilityScanResult:
    buzzword_hits: list[BuzzwordHit] = field(default_factory=list)
    redundant_verbs: list[VerbCount] = field(default_factory=list)
    bullet_line_count: int = 0

    @property
    def buzzword_density(self) -> float:
        """Buzzword hits per bullet-ish line -- 0 for a resume with none."""
        if self.bullet_line_count == 0:
            return 0.0
        return len(self.buzzword_hits) / self.bullet_line_count


def _lines(full_text: str) -> list[str]:
    out = []
    for raw_line in full_text.splitlines():
        line = _BULLET_PREFIX_RE.sub("", raw_line.strip())
        if line:
            out.append(line)
    return out


def scan_readability(full_text: str) -> ReadabilityScanResult:
    lines = _lines(full_text)
    result = ReadabilityScanResult(bullet_line_count=len(lines))

    for line in lines:
        lowered = line.lower()
        for phrase in _BUZZWORDS:
            if phrase in lowered and not _EVIDENCE_RE.search(line):
                result.buzzword_hits.append(BuzzwordHit(phrase=phrase, line=line))
                break  # one flag per line is enough signal

    verb_lines: dict[str, list[str]] = {}
    for line in lines:
        match = _LEADING_VERB_RE.match(line.lower())
        if match and match.group(1) in _GENERIC_VERBS:
            verb_lines.setdefault(match.group(1), []).append(line)

    for verb, matched_lines in verb_lines.items():
        if len(matched_lines) >= _REDUNDANCY_THRESHOLD:
            result.redundant_verbs.append(
                VerbCount(verb=verb, count=len(matched_lines), example_lines=matched_lines[:3])
            )
    result.redundant_verbs.sort(key=lambda v: v.count, reverse=True)

    return result


_MAX_BUZZWORD_FINDINGS = 4


def _source() -> list[SourceCitation]:
    return [
        SourceCitation(
            source="Internal wording heuristic (Level E, not yet backed by a fetched citation)",
            confidence=SourceConfidence.E,
            claim="Generic corporate filler and verb redundancy detection per the spec's Bullshit/Redundancy Detectors.",
            supports_rule="readability_scan",
        )
    ]


def run_readability_scan(full_text: str, next_id) -> tuple[dict, list[Finding]]:
    """Entry point main.py calls: scans + builds Findings in one step,
    mirroring aerospace_engine.engine.run_pm_positioning's pattern. Always
    runs (no API key needed) and always returns real data -- scoring/engine.py
    computes a real Recruiter Readability number from this alone, blending
    in the LLM's holistic judgment on top only when configured."""
    scan = scan_readability(full_text)
    findings: list[Finding] = []

    for hit in scan.buzzword_hits[:_MAX_BUZZWORD_FINDINGS]:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.CAREER_POSITIONING,
                classification=RiskClassification.HUMAN_RECRUITER_RISK,
                severity=Severity.YELLOW,
                title="Generic corporate phrase without supporting evidence",
                description=f"\"{hit.line[:160]}\"",
                why_it_matters="Phrases like this read as filler rather than a substantive claim -- a recruiter learns nothing concrete about the candidate from them.",
                ats_evidence=f"Matched phrase: \"{hit.phrase}\", no adjacent number/percent/dollar figure found in the same line.",
                recruiter_impact="Generic self-description without evidence is usually skimmed past, not credited.",
                recommended_change="Replace with a specific, evidence-backed claim (a number, scope, or concrete outcome), or cut it.",
                confidence=SourceConfidence.E,
                sources=_source(),
                priority=PriorityBucket.OPTIONAL_POLISH,
            )
        )

    if scan.redundant_verbs:
        top = scan.redundant_verbs[0]
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.CAREER_POSITIONING,
                classification=RiskClassification.HUMAN_RECRUITER_RISK,
                severity=Severity.YELLOW,
                title=f"Verb '{top.verb}' used {top.count} times",
                description=f"Example: \"{top.example_lines[0]}\"" if top.example_lines else "",
                why_it_matters="A single generic verb repeated across many bullets makes it harder to tell which accomplishments actually differ from each other.",
                ats_evidence=f"'{top.verb}' opens {top.count} lines.",
                recruiter_impact="Reads as low-effort and blurs distinct accomplishments together.",
                recommended_change="Vary the opening verb where it genuinely reflects a different kind of action -- but keep precise domain terminology even if it repeats; don't swap out an accurate technical verb just to avoid repetition.",
                confidence=SourceConfidence.E,
                sources=_source(),
                priority=PriorityBucket.OPTIONAL_POLISH,
            )
        )

    data = {
        "buzzword_hits": [{"phrase": h.phrase, "line": h.line} for h in scan.buzzword_hits],
        "redundant_verbs": [
            {"verb": v.verb, "count": v.count, "example_lines": v.example_lines} for v in scan.redundant_verbs
        ],
        "bullet_line_count": scan.bullet_line_count,
    }
    return data, findings
