"""Korean opportunity description processing.

The pipeline is deliberately deterministic. Korean job ads follow strong
conventions, so rules plus a curated gazetteer beat a model on precision and
stay inspectable, which is what an explainable match score depends on.

Every stage degrades rather than raises. A parser bug must never cost a student
a listing, so a failing stage records a warning and the rest still run.
"""

from app.nlp.clean import normalize_text
from app.nlp.detect import detect_language, hangul_ratio
from app.nlp.eligibility import extract_eligibility, extract_language_requirements
from app.nlp.fields import (
    extract_deadline,
    extract_education,
    extract_experience,
    extract_salary,
    extract_working_hours,
)
from app.nlp.gazetteer import SKILL_ALIASES, find_skills
from app.nlp.pipeline import ExtractedListing, extract_listing
from app.nlp.segments import Segment, segment_text

__all__ = [
    "ExtractedListing",
    "SKILL_ALIASES",
    "Segment",
    "detect_language",
    "extract_deadline",
    "extract_education",
    "extract_eligibility",
    "extract_experience",
    "extract_language_requirements",
    "extract_listing",
    "extract_salary",
    "extract_working_hours",
    "find_skills",
    "hangul_ratio",
    "normalize_text",
    "segment_text",
]
