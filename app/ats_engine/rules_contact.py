"""Layer 3 rules: contact information completeness and placement."""
from __future__ import annotations

from app.ats_engine.context import AnalysisContext
from app.knowledge_base.loader import structural_rule_meta
from app.models import (
    ContactInfo,
    Finding,
    FindingCategory,
    PriorityBucket,
    RiskClassification,
    Severity,
    SourceCitation,
    SourceConfidence,
)


def _citation(rule_id: str) -> list[SourceCitation]:
    meta = structural_rule_meta(rule_id)
    return [
        SourceCitation(
            source="Internal ATS rule heuristic (not yet backed by a fetched citation)",
            confidence=SourceConfidence(meta.get("confidence", "E")),
            claim=meta.get("why_it_matters", ""),
            supports_rule=rule_id,
        )
    ]


def rule_contact_completeness(ctx: AnalysisContext, contact: ContactInfo, next_id) -> list[Finding]:
    findings: list[Finding] = []
    meta = structural_rule_meta("missing_contact_field")

    if not contact.email:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.CONTACT_INFO,
                classification=RiskClassification.CONFIRMED_ATS_RISK,
                severity=Severity.RED,
                title="No email address could be extracted",
                description="No email address was found anywhere in the document text.",
                why_it_matters=meta["why_it_matters"],
                ats_evidence="Email regex found zero matches across the full extracted text.",
                recommended_change="Add a clearly formatted email address near the top of the resume.",
                confidence=SourceConfidence.E,
                sources=_citation("missing_contact_field"),
                priority=PriorityBucket.MUST_FIX,
            )
        )
    if not contact.phone:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.CONTACT_INFO,
                classification=RiskClassification.PROBABLE_ATS_RISK,
                severity=Severity.ORANGE,
                title="No phone number could be extracted",
                description="No phone number was found anywhere in the document text.",
                why_it_matters=meta["why_it_matters"],
                ats_evidence="Phone regex found zero matches across the full extracted text.",
                recommended_change="Add a phone number near the top of the resume, in a standard format.",
                confidence=SourceConfidence.E,
                sources=_citation("missing_contact_field"),
                priority=PriorityBucket.STRONGLY_RECOMMENDED,
            )
        )
    if not contact.name:
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.CONTACT_INFO,
                classification=RiskClassification.POSSIBLE_ATS_RISK,
                severity=Severity.YELLOW,
                title="Could not confidently identify a name on the first line",
                description="The first non-empty line of the document doesn't read like a short name (this is a best-effort heuristic, not a certain read -- worth a manual look).",
                why_it_matters="If the candidate's name isn't clearly the first element, both a human reviewer and simple ATS name-parsing can misread the header.",
                ats_evidence="No 1-5 word, <=60-character first line found before the first email/phone match.",
                recommended_change="Confirm the candidate's full name is the first, standalone line of the document.",
                confidence=SourceConfidence.E,
                sources=[],
                priority=PriorityBucket.OPTIONAL_POLISH,
            )
        )

    if contact.found_in_header_or_footer:
        header_footer_meta = structural_rule_meta("header_footer_contact")
        findings.append(
            Finding(
                id=next_id(),
                category=FindingCategory.CONTACT_INFO,
                classification=RiskClassification.PROBABLE_ATS_RISK,
                severity=Severity.ORANGE,
                title="Contact info found only in a header/footer region",
                description="Email/phone were only detected in what looks like a header or footer area, not in the main document body.",
                why_it_matters=header_footer_meta["why_it_matters"],
                ats_evidence="Email/phone regex matched only within header/footer text, not within the main body text.",
                recommended_change="Duplicate the essential contact info (name, email, phone) into the top of the main document body, not only the header/footer.",
                confidence=SourceConfidence.E,
                sources=_citation("header_footer_contact"),
                priority=PriorityBucket.STRONGLY_RECOMMENDED,
            )
        )

    return findings
