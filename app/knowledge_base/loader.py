"""Small helpers for loading the JSON-backed knowledge base files."""
from __future__ import annotations

import functools
import json
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent


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
