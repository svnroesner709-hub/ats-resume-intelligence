from tests.fixtures.generate_fixtures import FIXTURES_DIR

from app.parsers import docx_parser, pdf_pdfminer, pdf_pdfplumber, pdf_pymupdf
from app.parsers.extraction_compare import compare_extractions
from app.models import ExtractionMethodResult


def test_clean_baseline_pymupdf_extracts_expected_text():
    result = pdf_pymupdf.extract(FIXTURES_DIR / "clean_baseline.pdf")
    assert "Jane A. Doe" in result.full_text
    assert "jane.doe@example.com" in result.full_text
    assert "PROFESSIONAL EXPERIENCE" in result.full_text
    assert result.pages[0].has_text is True


def test_clean_baseline_three_methods_agree_closely():
    pymupdf_result = pdf_pymupdf.extract(FIXTURES_DIR / "clean_baseline.pdf")
    plumber_result = pdf_pdfplumber.extract(FIXTURES_DIR / "clean_baseline.pdf")
    miner_result = pdf_pdfminer.extract(FIXTURES_DIR / "clean_baseline.pdf")

    methods = [
        ExtractionMethodResult(method="pymupdf", text=pymupdf_result.full_text, char_count=len(pymupdf_result.full_text), ok=True),
        ExtractionMethodResult(method="pdfplumber", text=plumber_result.full_text, char_count=len(plumber_result.full_text), ok=plumber_result.error is None),
        ExtractionMethodResult(method="pdfminer", text=miner_result.full_text, char_count=len(miner_result.full_text), ok=miner_result.error is None),
    ]
    comparison = compare_extractions(methods)
    assert comparison.agreement_ratio >= 0.85
    assert not any("failed entirely" in d for d in comparison.divergences)


def test_image_only_pdf_has_no_text_layer():
    result = pdf_pymupdf.extract(FIXTURES_DIR / "image_only.pdf")
    assert result.pages[0].has_text is False
    assert result.pages[0].has_images is True
    assert result.full_text.strip() == ""


def test_docx_table_extraction():
    result = docx_parser.extract(FIXTURES_DIR / "table_resume.docx")
    assert result.error is None
    assert len(result.tables) == 1
    assert result.tables[0].n_rows == 3
    assert result.tables[0].n_cols == 2


def test_docx_header_footer_extraction():
    result = docx_parser.extract(FIXTURES_DIR / "header_footer_contact.docx")
    assert any("alex.nguyen@example.com" in h for h in result.header_text)
    assert "alex.nguyen@example.com" not in result.full_text


def test_docx_hidden_and_white_text_detected():
    result = docx_parser.extract(FIXTURES_DIR / "hidden_text.docx")
    assert len(result.hidden_text_runs) >= 1
    assert len(result.white_text_runs) >= 1
