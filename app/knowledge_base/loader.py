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
class KeywordTerm:
    term: str
    abbreviations: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)

    @property
    def all_forms(self) -> list[str]:
        return [self.term] + self.abbreviations + self.synonyms


@dataclass
class KeywordCategory:
    key: str
    label: str
    terms: list[KeywordTerm]


@functools.lru_cache(maxsize=None)
def keyword_database() -> tuple[KeywordCategory, ...]:
    """The full aerospace/defense/PM/manufacturing/certification/government-
    contracting/tools keyword database (app/knowledge_base/keywords/*.json),
    used by app/keyword_engine/matcher.py. Returns a tuple (not a list) so
    the lru_cache-returned value can't be accidentally mutated by callers."""
    categories = []
    for rel_path in KEYWORD_CATEGORY_FILES:
        data = load_json(rel_path)
        terms = [
            KeywordTerm(
                term=t["term"],
                abbreviations=t.get("abbreviations", []),
                synonyms=t.get("synonyms", []),
            )
            for t in data["terms"]
        ]
        categories.append(KeywordCategory(key=data["category"], label=data["label"], terms=terms))
    return tuple(categories)


def ownership_verbs() -> list[str]:
    data = load_json("keywords/ownership_verbs.json")
    return data["ownership_verbs"]


def weak_participation_verbs() -> list[str]:
    data = load_json("keywords/ownership_verbs.json")
    return data["weak_participation_verbs"]
