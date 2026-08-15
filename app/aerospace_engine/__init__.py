"""
Phase 7: Program Management Positioning. Deterministic ownership-verb scan
(app/aerospace_engine/ownership_scan.py) always runs; LLM-powered bullet
quality scoring (app/aerospace_engine/engine.py) adds depth when
ANTHROPIC_API_KEY is configured. See engine.py::run_pm_positioning.
"""
from __future__ import annotations

from app.aerospace_engine.engine import run_pm_positioning  # noqa: F401
