"""
Anthropic tool-call JSON schemas for every LLM-backed analysis call. Kept
in one place so the input_schema contracts are easy to audit against what
career_engine/aerospace_engine/jd_matching/keyword_engine actually consume.
"""
from __future__ import annotations

POSITIONING_ANALYSIS_SCHEMA = {
    "name": "report_positioning_analysis",
    "description": "Report a structured career-positioning analysis of a resume against a target role.",
    "input_schema": {
        "type": "object",
        "properties": {
            "narrative_sentence": {
                "type": "string",
                "description": "One sentence answering 'what does this person do?' based only on the resume text.",
            },
            "implied_role": {
                "type": "string",
                "description": "The role this resume most reads as, e.g. Program Manager, Technical Program Manager, Engineering Program Manager, Manufacturing Program Manager, Materials & Processes Engineer, Systems Engineer, Aerospace Generalist, etc.",
            },
            "role_alignment_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "role_alignment_rationale": {"type": "string"},
            "seniority_calibration": {
                "type": "string",
                "enum": ["undersells", "matches", "oversells", "unclear"],
            },
            "seniority_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "seniority_rationale": {"type": "string"},
            "summary_present": {"type": "boolean"},
            "summary_evaluation": {
                "type": "string",
                "description": "If a summary is present: judge it on differentiation/specificity, not mere existence. If absent: state plainly whether this candidate's career history would benefit from one -- never a reflexive 'add a summary'.",
            },
            "summary_differentiation_score": {
                "type": ["integer", "null"],
                "description": "0-100 if a summary is present, null if absent.",
            },
            "years_experience_note": {
                "type": "string",
                "description": "Whether/where total years-of-experience framing helps or hurts this resume's positioning, including any age-bias tradeoff worth flagging.",
            },
            "recruiter_readability_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "recruiter_readability_rationale": {"type": "string"},
            "flags": {
                "type": "array",
                "description": "2-4 concrete positioning issues worth surfacing as findings. Do not pad this list if fewer are genuinely warranted.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "severity": {"type": "string", "enum": ["orange", "yellow"]},
                        "why_it_matters": {"type": "string"},
                        "recommended_change": {"type": "string"},
                    },
                    "required": ["title", "severity", "why_it_matters", "recommended_change"],
                },
            },
        },
        "required": [
            "narrative_sentence", "implied_role", "role_alignment_score", "role_alignment_rationale",
            "seniority_calibration", "seniority_score", "seniority_rationale", "summary_present",
            "summary_evaluation", "years_experience_note", "recruiter_readability_score",
            "recruiter_readability_rationale", "flags",
        ],
    },
}

BULLET_QUALITY_SCHEMA = {
    "name": "report_bullet_quality_analysis",
    "description": "Score the strongest/weakest experience bullets in a resume for Action+Scope+Technical Context+Result quality.",
    "input_schema": {
        "type": "object",
        "properties": {
            "bullets": {
                "type": "array",
                "description": "Up to 8 of the most relevant experience bullets, prioritizing the most senior/recent roles.",
                "items": {
                    "type": "object",
                    "properties": {
                        "bullet_text": {"type": "string", "description": "A short snippet (<=200 chars) identifying which bullet this is."},
                        "ownership_score": {"type": "integer", "minimum": 0, "maximum": 10},
                        "specificity_score": {"type": "integer", "minimum": 0, "maximum": 10},
                        "scope_score": {"type": "integer", "minimum": 0, "maximum": 10},
                        "technical_context_score": {"type": "integer", "minimum": 0, "maximum": 10},
                        "metric_strength_score": {"type": "integer", "minimum": 0, "maximum": 10},
                        "outcome_score": {"type": "integer", "minimum": 0, "maximum": 10},
                        "weakest_dimension": {"type": "string"},
                        "missing_variable": {
                            "type": ["string", "null"],
                            "description": "If a concrete missing fact would materially strengthen this bullet (e.g. 'dollar value', 'team size', 'schedule recovery amount'), name ONE. Null if nothing is missing or the bullet is already strong.",
                        },
                        "rewrite_suggestion": {
                            "type": ["string", "null"],
                            "description": "A concrete improved rewrite using ONLY facts already present in the bullet -- never invent a number, scope, or outcome not stated. Null if you cannot improve it without fabricating something.",
                        },
                    },
                    "required": [
                        "bullet_text", "ownership_score", "specificity_score", "scope_score",
                        "technical_context_score", "metric_strength_score", "outcome_score",
                        "weakest_dimension", "missing_variable", "rewrite_suggestion",
                    ],
                },
            },
            "ownership_language_note": {
                "type": "string",
                "description": "A brief overall note on verb/ownership-language patterns across the resume, complementing (not duplicating) a separate deterministic verb scan.",
            },
        },
        "required": ["bullets", "ownership_language_note"],
    },
}

JD_REQUIREMENT_MATRIX_SCHEMA = {
    "name": "report_jd_requirement_matrix",
    "description": "Build a requirement-coverage matrix comparing a resume against a pasted job description.",
    "input_schema": {
        "type": "object",
        "properties": {
            "requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "requirement": {"type": "string", "description": "Short paraphrase of one JD requirement/qualification."},
                        "jd_importance": {"type": "string", "enum": ["required", "preferred", "nice_to_have"]},
                        "resume_coverage": {
                            "type": "string",
                            "enum": ["strong_match", "partial_match", "missing", "probably_irrelevant"],
                        },
                        "evidence": {
                            "type": ["string", "null"],
                            "description": "Quote or close paraphrase from the resume supporting the match. Null if missing.",
                        },
                        "recommendation": {"type": ["string", "null"]},
                    },
                    "required": ["requirement", "jd_importance", "resume_coverage", "evidence", "recommendation"],
                },
            },
            "overall_fit_note": {"type": "string"},
        },
        "required": ["requirements", "overall_fit_note"],
    },
}

SEMANTIC_KEYWORD_ENRICHMENT_SCHEMA = {
    "name": "report_semantic_keyword_matches",
    "description": "Identify resume passages that are semantically equivalent to specific candidate terms, even when the exact term/abbreviation/synonym doesn't appear verbatim.",
    "input_schema": {
        "type": "object",
        "properties": {
            "matches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "term": {"type": "string", "description": "Must be exactly one of the candidate terms provided in the prompt."},
                        "matched_because": {"type": "string", "description": "The resume quote/paraphrase that semantically implies this term."},
                        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    },
                    "required": ["term", "matched_because", "confidence"],
                },
            },
        },
        "required": ["matches"],
    },
}
