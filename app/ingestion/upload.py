"""
Phase 1: Ingestion.

Accepts a PDF or DOCX upload, validates it, stores the original file
untouched (never overwritten -- spec: "Never overwrite the user's original
file"), and computes a content hash for dedup/traceability.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


class UnsupportedFileType(Exception):
    pass


class FileTooLarge(Exception):
    pass


@dataclass
class StoredFile:
    file_id: str
    original_filename: str
    file_type: str  # "pdf" | "docx"
    path: Path
    sha256: str
    size_bytes: int


def store_upload(filename: str, content: bytes) -> StoredFile:
    """Validate and persist an uploaded resume. Raises UnsupportedFileType
    or FileTooLarge on invalid input -- callers should surface these as
    user-facing 4xx errors, not silently coerce the file."""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileType(
            f"'{suffix or '(no extension)'}' is not supported. Upload a .pdf or .docx file."
        )
    if len(content) == 0:
        raise UnsupportedFileType("Uploaded file is empty.")
    if len(content) > MAX_SIZE_BYTES:
        raise FileTooLarge(
            f"File is {len(content) / 1_000_000:.1f} MB, which exceeds the "
            f"{MAX_SIZE_BYTES / 1_000_000:.0f} MB limit."
        )

    file_id = uuid.uuid4().hex[:16]
    file_type = "pdf" if suffix == ".pdf" else "docx"
    dest = UPLOAD_DIR / f"{file_id}{suffix}"
    dest.write_bytes(content)

    sha256 = hashlib.sha256(content).hexdigest()

    return StoredFile(
        file_id=file_id,
        original_filename=filename,
        file_type=file_type,
        path=dest,
        sha256=sha256,
        size_bytes=len(content),
    )
