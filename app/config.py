"""
App-wide configuration, loaded from a local .env (see .env.example).

LLM_ENABLED is the single flag every LLM-backed module checks before
attempting a call -- when False, those modules must return a clean
"not configured" result rather than raising, so Phases 1-5 always work
with zero setup.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
LLM_MODEL = os.environ.get("LLM_MODEL", "").strip() or "claude-sonnet-5"
LLM_ENABLED = bool(ANTHROPIC_API_KEY)
