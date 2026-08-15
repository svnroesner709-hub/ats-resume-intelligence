"""
Layer 3: Contact Information Screening.

Regex-based extraction is deliberately conservative -- this flags what it
can find with reasonable confidence and says so plainly when a field
(especially name) is a best-effort guess rather than a certain read.
"""
from __future__ import annotations

import re

from app.models import ContactInfo

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9\-_/%]+", re.I)
GENERIC_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?[A-Za-z0-9\-]+\.[A-Za-z]{2,}(?:/[^\s]*)?")


def extract_contact_info(body_text: str, header_texts: list[str], footer_texts: list[str]) -> ContactInfo:
    header_footer_text = "\n".join(header_texts + footer_texts)
    combined = body_text + "\n" + header_footer_text

    email_match = EMAIL_RE.search(combined)
    phone_match = PHONE_RE.search(combined)
    linkedin_match = LINKEDIN_RE.search(combined)

    website = None
    for candidate in GENERIC_URL_RE.finditer(combined):
        value = candidate.group(0)
        if "linkedin.com" in value.lower():
            continue
        if email_match and value.lower() in email_match.group(0).lower():
            continue
        website = value
        break

    # Best-effort name guess: first non-empty line of the body text that
    # isn't itself an email/phone/URL and is short enough to plausibly be
    # a name (avoids grabbing a summary sentence).
    name = None
    for line in body_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if EMAIL_RE.search(stripped) or PHONE_RE.search(stripped):
            continue
        word_count = len(stripped.split())
        if 1 <= word_count <= 5 and len(stripped) <= 60:
            name = stripped
        break  # only ever consider the very first non-empty line

    found_only_in_header_footer = False
    if email_match or phone_match:
        in_body = bool(EMAIL_RE.search(body_text) or PHONE_RE.search(body_text))
        in_header_footer = bool(EMAIL_RE.search(header_footer_text) or PHONE_RE.search(header_footer_text))
        found_only_in_header_footer = in_header_footer and not in_body

    return ContactInfo(
        name=name,
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0) if phone_match else None,
        linkedin=linkedin_match.group(0) if linkedin_match else None,
        website=website,
        found_in_header_or_footer=found_only_in_header_footer,
    )
