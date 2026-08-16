"""
Core data schema for the ATS Resume Intelligence pipeline.

Every analysis engine (implemented or stubbed) reads/writes these models.
The GUI renders from this structured model rather than mixing analysis
logic into UI code (see CLAUDE.md-equivalent operating charter, "ANALYSIS
OUTPUT FORMAT" / "DEVELOPMENT ARCHITECTURE" sections of the project spec
in the README).

IMPORTANT: fields here are the contract between backend and frontend.
Scores/fields for not-yet-implemented engines (Phases 6-10) MUST be left
as None with an explicit "not yet implemented" status rather than a
fabricated value. See scoring/engine.py.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Severity / classification enums (spec: "Each significant warning must be
# classified as one of ..." / GUI color-coding rules)
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Visual/GUI severity. RED is reserved for confirmed parsing/extraction
    breakage or a critical structural failure -- never for wording taste."""
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    INFO = "info"  # used for "No Meaningful Risk" / positive confirmations


class RiskClassification(str, Enum):
    CONFIRMED_ATS_RISK = "Confirmed ATS Risk"
    PROBABLE_ATS_RISK = "Probable ATS Risk"
    POSSIBLE_ATS_RISK = "Possible ATS Risk"
    HUMAN_RECRUITER_RISK = "Human Recruiter Risk"
    POSITIONING_OPPORTUNITY = "Positioning Opportunity"
    STYLISTIC_PREFERENCE = "Stylistic Preference"
    NO_MEANINGFUL_RISK = "No Meaningful Risk"


class SourceConfidence(str, Enum):
    """Evidence confidence model from the spec. Never present E as equivalent
    to A."""
    A = "A"  # Official ATS/platform documentation or an empirical parsing test actually run
    B = "B"  # Major recruiting orgs, credible career centers, established research
    C = "C"  # Large aggregated corpus of current job postings
    D = "D"  # Public resume examples / recruiter opinion
    E = "E"  # Internal heuristic / model judgment, no external corroboration


class FindingCategory(str, Enum):
    PARSING = "parsing"
    STRUCTURE = "structure"
    CONTACT_INFO = "contact_info"
    SECTION_ARCHITECTURE = "section_architecture"
    TYPOGRAPHY = "typography"
    MICRO_FORMATTING = "micro_formatting"
    CAREER_POSITIONING = "career_positioning"          # stub engine
    AEROSPACE_RELEVANCE = "aerospace_relevance"         # stub engine
    PROGRAM_MANAGEMENT = "program_management"           # stub engine
    KEYWORD_MATCH = "keyword_match"                     # stub engine
    ACCOMPLISHMENT_STRENGTH = "accomplishment_strength"  # stub engine


class PriorityBucket(str, Enum):
    MUST_FIX = "must_fix"
    STRONGLY_RECOMMENDED = "strongly_recommended"
    OPTIONAL_POLISH = "optional_polish"
    NO_ACTION = "no_action"


# ---------------------------------------------------------------------------
# Geometry / location
# ---------------------------------------------------------------------------

class BBox(BaseModel):
    """Bounding box in PDF page coordinates (points, origin top-left) or, for
    DOCX, a synthetic box computed by the HTML renderer for overlay purposes."""
    page: int = 0
    x0: float
    y0: float
    x1: float
    y1: float


class SourceCitation(BaseModel):
    source: str
    url: Optional[str] = None
    date_accessed: Optional[str] = None
    claim: Optional[str] = None
    confidence: SourceConfidence = SourceConfidence.E
    supports_rule: Optional[str] = None


# ---------------------------------------------------------------------------
# Finding — the atomic unit of analysis output
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    id: str
    category: FindingCategory
    classification: RiskClassification
    severity: Severity
    title: str
    description: str
    why_it_matters: str
    ats_evidence: str
    recruiter_impact: Optional[str] = None
    recommended_change: Optional[str] = None
    suggested_rewrite: Optional[list[str]] = None
    confidence: SourceConfidence = SourceConfidence.E
    sources: list[SourceCitation] = Field(default_factory=list)
    location: Optional[BBox] = None
    priority: PriorityBucket = PriorityBucket.OPTIONAL_POLISH


# ---------------------------------------------------------------------------
# Document / parsing layer
# ---------------------------------------------------------------------------

class ExtractionMethodResult(BaseModel):
    method: str
    text: str
    char_count: int
    ok: bool
    error: Optional[str] = None


class ExtractionComparison(BaseModel):
    methods: list[ExtractionMethodResult]
    agreement_ratio: float  # 0-1 similarity across methods
    divergences: list[str] = Field(default_factory=list)


class PageInfo(BaseModel):
    page_number: int
    width: float
    height: float
    image_path: str  # relative path served by the GUI


class DocumentInfo(BaseModel):
    file_id: str
    original_filename: str
    file_type: str  # "pdf" | "docx"
    sha256: str
    size_bytes: int
    page_count: int
    pages: list[PageInfo] = Field(default_factory=list)
    docx_html: Optional[str] = None  # rendered DOCX body (mammoth output)


class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    found_in_header_or_footer: bool = False


class TargetProfile(BaseModel):
    """User-supplied targeting inputs (spec's INPUT fields)."""
    industry: Optional[str] = None
    career_path: Optional[str] = None
    target_role: Optional[str] = None
    seniority: Optional[str] = None
    target_company: Optional[str] = None
    job_description: Optional[str] = None
    background_notes: Optional[str] = None


class ScoreCheck(BaseModel):
    """One named, evidence-backed check that fed a ScoreValue's number.
    Every check is derived from data already computed elsewhere (findings,
    extraction comparison, keyword matches, ...) -- never a parallel
    re-implementation that could drift from the actual rule/finding logic."""
    name: str
    passed: bool
    detail: str
    source: Optional[SourceCitation] = None


class ScoreValue(BaseModel):
    value: Optional[int] = None  # 0-100, None if not computed
    label: str
    status: str = "computed"  # "computed" | "not yet implemented" | "llm_error"
    explanation: Optional[str] = None
    checks: list[ScoreCheck] = Field(default_factory=list)


class Scores(BaseModel):
    ats_parsing_reliability: ScoreValue
    ats_structural_compatibility: ScoreValue
    target_role_alignment: ScoreValue
    aerospace_keyword_coverage: ScoreValue
    program_management_positioning: ScoreValue
    recruiter_readability: ScoreValue
    executive_seniority_signal: ScoreValue
    overall_resume_strength: ScoreValue


# ---------------------------------------------------------------------------
# Keyword coverage (Phase 8 core, deterministic + optional LLM enrichment)
# ---------------------------------------------------------------------------

class MatchedKeyword(BaseModel):
    term: str
    category: str
    category_label: str
    matched_form: str  # the exact term/abbreviation/synonym/quote that matched
    via: str  # "dictionary" | "llm_semantic"
    confidence: SourceConfidence = SourceConfidence.E
    # Populated only for terms verified against the 2026-08 real-job-posting
    # sweep (Level C); empty for the Level E baseline database.
    sources: list[SourceCitation] = Field(default_factory=list)


class CategoryCoverage(BaseModel):
    category: str
    label: str
    total_terms: int
    matched_terms: int
    coverage_ratio: float


class KeywordCoverageResult(BaseModel):
    matched: list[MatchedKeyword] = Field(default_factory=list)
    notable_missing: list[str] = Field(default_factory=list)  # high-value terms not found in any category
    categories: list[CategoryCoverage] = Field(default_factory=list)
    llm_enrichment_ran: bool = False


# ---------------------------------------------------------------------------
# JD Requirement Coverage Matrix (Phase 8 JD mode, LLM-powered)
# ---------------------------------------------------------------------------

class JDRequirementRow(BaseModel):
    requirement: str
    jd_importance: str  # "required" | "preferred" | "nice_to_have"
    resume_coverage: str  # "strong_match" | "partial_match" | "missing" | "probably_irrelevant"
    evidence: Optional[str] = None
    recommendation: Optional[str] = None


class JDMatchResult(BaseModel):
    requirements: list[JDRequirementRow] = Field(default_factory=list)
    overall_fit_note: str = ""
    status: str = "computed"  # "computed" | "not yet implemented" | "llm_error"
    explanation: Optional[str] = None


class AnalysisResult(BaseModel):
    document: DocumentInfo
    target_profile: TargetProfile
    parsing: ExtractionComparison
    contact_info: ContactInfo
    findings: list[Finding]
    scores: Scores
    must_fix: list[str]
    strongly_recommended: list[str]
    optional_polish: list[str]
    not_yet_implemented: list[str] = Field(default_factory=list)
    # page_number (as str, JSON dict keys must be strings) -> list of
    # normalized overlay boxes; see app/annotation/mapper.py
    overlays: dict[str, list[dict]] = Field(default_factory=dict)
    keyword_coverage: Optional[KeywordCoverageResult] = None
    jd_match: Optional[JDMatchResult] = None
