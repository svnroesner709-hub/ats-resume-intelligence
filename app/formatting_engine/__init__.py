"""
STUB (mostly) -- spec Layer 13 ("Font and Typography Audit") and Layer 14
("Micro-Formatting Audit").

Basic font-recognition checking (uncommon font family flagging) is
implemented pragmatically in app/ats_engine/rules_structure.py::rule_fonts
since it only needed the same PyMuPDF font data already loaded for the
ats_engine's structural pass -- no separate module made sense for that one
check. Everything else in Layers 13/14 (line height, bullet
indentation/density consistency, date-format consistency, widows/orphans,
bold-hierarchy consistency, etc.) is NOT yet implemented and needs
LLM-assisted or much deeper micro-formatting analysis to do well.
"""
from __future__ import annotations


def audit_micro_formatting(full_text: str) -> dict:
    raise NotImplementedError("formatting_engine.audit_micro_formatting is not yet implemented.")
