"""Small helpers for loading the JSON-backed knowledge base files."""
from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent

KEYWORD_CATEGORY_FILES = [
    "keywords/aerospace_defense.json",
    "keywords/program_management.json",
    "keywords/manufacturing_quality.json",
    "keywords/systems_engineering_certification.json",
    "keywords/government_contracting.json",
    "keywords/tools_systems.json",
]


@functools.lru_cache(maxsize=None)
def load_json(relative_path: str) -> dict:
    path = KB_ROOT / relative_path
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_fonts() -> set[str]:
    data = load_json("fonts_and_formatting/safe_fonts.json")
    return {f.lower() for f in data["families"]}


def section_heading_variants() -> dict[str, list[str]]:
    data = load_json("ats_rules/section_headings.json")
    return data["sections"]


def structural_rule_meta(rule_id: str) -> dict:
    data = load_json("ats_rules/structural_rules.json")
    return data["rules"].get(rule_id, {"why_it_matters": "", "confidence": "E"})


@dataclass
class TermSource:
    company: str
    role_title: str
    url: str
    date_accessed: str


@dataclass
class KeywordTerm:
    term: str
    abbreviations: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    # Per-term override. None means "inherit the category file's
    # source_confidence" (Level E, internal heuristic). Terms actually
    # observed in the 2026-08 real-job-posting sweep carry "C" here plus
    # real sources -- see knowledge_base/job_descriptions/.
    source_confidence: str | None = None
    sources: list[TermSource] = field(default_factory=list)

    @property
    def all_forms(self) -> list[str]:
        return [self.term] + self.abbreviations + self.synonyms


@dataclass
class KeywordCategory:
    key: str
    label: str
    terms: list[KeywordTerm]
    default_confidence: str = "E"


BULK_ACRONYM_FILE = "keywords/acronyms_bulk.txt"


def _load_bulk_acronyms() -> dict[str, list[KeywordTerm]]:
    """Parses the plain-text bulk acronym library (category|ACRONYM|Expansion
    per line) into KeywordTerm objects, keyed by category. Kept as a flat
    text file rather than JSON specifically so it's fast to bulk-extend --
    see the file's own header comment."""
    path = KB_ROOT / BULK_ACRONYM_FILE
    by_category: dict[str, list[KeywordTerm]] = {}
    if not path.exists():
        return by_category

    with open(path, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 3:
                continue  # tolerate malformed lines rather than crash the app on a typo
            category_key, acronym, expansion = (p.strip() for p in parts)
            by_category.setdefault(category_key, []).append(
                KeywordTerm(term=expansion, abbreviations=[acronym], synonyms=[])
            )
    return by_category


@functools.lru_cache(maxsize=None)
def keyword_database() -> tuple[KeywordCategory, ...]:
    """The full aerospace/defense/PM/manufacturing/certification/government-
    contracting/tools keyword database (app/knowledge_base/keywords/*.json
    plus the bulk acronym text file), used by app/keyword_engine/matcher.py.
    Returns a tuple (not a list) so the lru_cache-returned value can't be
    accidentally mutated by callers."""
    bulk_by_category = _load_bulk_acronyms()
    categories = []
    for rel_path in KEYWORD_CATEGORY_FILES:
        data = load_json(rel_path)
        default_confidence = data.get("source_confidence", "E")
        terms = [
            KeywordTerm(
                term=t["term"],
                abbreviations=t.get("abbreviations", []),
                synonyms=t.get("synonyms", []),
                source_confidence=t.get("source_confidence"),
                sources=[TermSource(**s) for s in t.get("sources", [])],
            )
            for t in data["terms"]
        ]
        existing_names = {t.term.lower() for t in terms}
        for bulk_term in bulk_by_category.get(data["category"], []):
            if bulk_term.term.lower() not in existing_names:
                terms.append(bulk_term)
                existing_names.add(bulk_term.term.lower())
        categories.append(
            KeywordCategory(key=data["category"], label=data["label"], terms=terms, default_confidence=default_confidence)
        )
    return tuple(categories)


def ownership_verbs() -> list[str]:
    data = load_json("keywords/ownership_verbs.json")
    return data["ownership_verbs"]


def weak_participation_verbs() -> list[str]:
    data = load_json("keywords/ownership_verbs.json")
    return data["weak_participation_verbs"]


@dataclass
class RoleProfile:
    key: str
    label: str
    aliases: list[str]
    category_weights: dict[str, float]
    signature_terms: list[str]


@functools.lru_cache(maxsize=None)
def role_taxonomy() -> tuple[RoleProfile, ...]:
    """The role taxonomy used by app/career_engine/role_alignment.py for
    deterministic Target Role Alignment. See
    app/knowledge_base/role_taxonomy/roles.json for the data and its
    module-level docstring for the matching approach."""
    data = load_json("role_taxonomy/roles.json")
    return tuple(
        RoleProfile(
            key=r["key"],
            label=r["label"],
            aliases=r["aliases"],
            category_weights=r["category_weights"],
            signature_terms=r["signature_terms"],
        )
        for r in data["roles"]
    )
