import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixtures.generate_fixtures import FIXTURES_DIR, generate_all


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    required = [
        "clean_baseline.pdf",
        "two_column.pdf",
        "image_only.pdf",
        "table_resume.docx",
        "header_footer_contact.docx",
        "hidden_text.docx",
    ]
    if not all((FIXTURES_DIR / name).exists() for name in required):
        generate_all()
