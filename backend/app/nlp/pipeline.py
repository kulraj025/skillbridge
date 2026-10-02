"""Extraction pipeline orchestrator.

Runs every stage over a description and returns one structured result. The
important property is failure isolation: each stage is guarded independently,
so a bug in salary parsing cannot cost a student their skills, and the failure
is recorded as a warning rather than swallowed.

Stages are ordered cheapest-and-most-reliable first. Language detection gates
the Korean stages, but nothing downstream depends on the stages having
succeeded, only on their result being available.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from app.nlp.clean import normalize_text
from app.nlp.detect import detect_language
from app.nlp.eligibility import (
    DISPLAY_UNSPECIFIED,
    extract_eligibility,
    extract_language_requirements,
)
from app.nlp.fields import (
    extract_deadline,
    extract_education,
    extract_experience,
    extract_salary,
    extract_working_hours,
)
from app.nlp.gazetteer import find_skills
from app.nlp.segments import (
    DUTY,
    PREFERRED,
    REQUIRED,
    UNSTATED,
    segment_text,
)

EXTRACTION_VERSION = "korean-rules-1"


class SkillHit:
    """One skill found in a listing, with the words that produced it."""

    __slots__ = ("name", "requirement", "evidence", "explicit", "clause")

    def __init__(
        self,
        name: str,
        requirement: str,
        evidence: str,
        explicit: bool = True,
        clause: str = "",
    ):
        self.name = name
        self.requirement = requirement
        self.evidence = evidence
        self.explicit = explicit
        self.clause = clause

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "requirement": self.requirement,
            "evidence": self.evidence,
            "explicit": self.explicit,
            "clause": self.clause,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "SkillHit({0!r}, {1!r})".format(self.name, self.requirement)


class ExtractedListing:
    """Everything the pipeline could determine about a listing."""

    def __init__(self) -> None:
        self.original_language: str = "und"
        self.required_skills: List[SkillHit] = []
        self.preferred_skills: List[SkillHit] = []
        self.unstated_skills: List[SkillHit] = []
        self.responsibilities: List[SkillHit] = []
        self.language_requirements: List[Dict[str, Any]] = []
        self.experience: Dict[str, Any] = {"years": None, "text": None, "fresh_graduate_ok": False}
        self.education: Dict[str, Any] = {"level": None, "text": None}
        self.salary: Dict[str, Any] = {}
        self.working_hours: Dict[str, Any] = {}
        self.deadline: Optional[str] = None
        self.eligibility: Dict[str, Any] = {}
        self.warnings: List[str] = []
        self.extraction_version: str = EXTRACTION_VERSION

    def skill_names(self, requirement: str) -> List[str]:
        mapping = {
            REQUIRED: self.required_skills,
            PREFERRED: self.preferred_skills,
            UNSTATED: self.unstated_skills,
            DUTY: self.responsibilities,
        }
        return [hit.name for hit in mapping.get(requirement, [])]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_language": self.original_language,
            "required_skills": [hit.to_dict() for hit in self.required_skills],
            "preferred_skills": [hit.to_dict() for hit in self.preferred_skills],
            "unstated_skills": [hit.to_dict() for hit in self.unstated_skills],
            "responsibilities": [hit.to_dict() for hit in self.responsibilities],
            "language_requirements": self.language_requirements,
            "experience": self.experience,
            "education": self.education,
            "salary": self.salary,
            "working_hours": self.working_hours,
            "deadline": self.deadline,
            "eligibility": self.eligibility,
            "warnings": self.warnings,
            "extraction_version": self.extraction_version,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "ExtractedListing(lang={0!r}, required={1}, preferred={2}, warnings={3})".format(
            self.original_language,
            len(self.required_skills),
            len(self.preferred_skills),
            len(self.warnings),
        )


def _guard(
    result: ExtractedListing,
    stage: str,
    call: Callable[[], Any],
    default: Any,
):
    """Run one stage, recording a warning instead of failing the pipeline."""

    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - deliberate: a stage must not kill the run
        result.warnings.append("{0} extraction failed: {1}".format(stage, exc))
        return default


def _collect_skills(segments, requirement: str, require_explicit: bool = False) -> List[SkillHit]:
    hits: List[SkillHit] = []
    seen = set()
    for segment in segments:
        if segment.is_header or segment.kind != requirement:
            continue
        if require_explicit and not segment.explicit:
            continue
        for found in find_skills(segment.text):
            if found["name"] in seen:
                continue
            seen.add(found["name"])
            hits.append(
                SkillHit(
                    name=found["name"],
                    requirement=requirement,
                    evidence=found["evidence"],
                    explicit=segment.explicit,
                    clause=segment.text,
                )
            )
    return hits


def extract_listing(
    description: str,
    posted_at: Optional[datetime] = None,
    today: Optional[date] = None,
) -> ExtractedListing:
    """Extract every structured field the pipeline can determine.

    Never raises. ``description`` is preserved by the caller; this function
    works on a normalised copy and never returns a rewritten description, so
    the employer's original wording stays available for display.
    """

    result = ExtractedListing()

    cleaned = _guard(result, "normalise", lambda: normalize_text(description), "")
    if not cleaned:
        result.warnings.append("description was empty after normalisation")
        return result

    result.original_language = _guard(
        result, "language detection", lambda: detect_language(cleaned), "und"
    )

    segments = _guard(result, "segmentation", lambda: segment_text(cleaned), [])

    result.required_skills = _guard(
        result, "required skills", lambda: _collect_skills(segments, REQUIRED), []
    )
    result.preferred_skills = _guard(
        result, "preferred skills", lambda: _collect_skills(segments, PREFERRED), []
    )
    result.unstated_skills = _guard(
        result, "unstated skills", lambda: _collect_skills(segments, UNSTATED), []
    )
    result.responsibilities = _guard(
        result, "responsibilities", lambda: _collect_skills(segments, DUTY), []
    )

    result.language_requirements = _guard(
        result, "language requirements", lambda: extract_language_requirements(segments), []
    )
    result.experience = _guard(
        result,
        "experience",
        lambda: extract_experience(cleaned),
        {"years": None, "text": None, "fresh_graduate_ok": False},
    )
    result.education = _guard(
        result, "education", lambda: extract_education(cleaned), {"level": None, "text": None}
    )
    result.salary = _guard(
        result,
        "salary",
        lambda: extract_salary(cleaned),
        {"value": None, "min": None, "max": None, "unit": None, "text": None},
    )
    result.working_hours = _guard(result, "working hours", lambda: extract_working_hours(cleaned), {})
    result.eligibility = _guard(
        result,
        "eligibility",
        lambda: extract_eligibility(cleaned),
        {
            "international_students_accepted": None,
            "statement": None,
            "source": None,
            "display": DISPLAY_UNSPECIFIED,
            "visa_required_stated": False,
        },
    )

    deadline = _guard(
        result,
        "deadline",
        lambda: extract_deadline(cleaned, posted_at=posted_at, today=today),
        {"value": None, "text": None, "inferred_year": False},
    )
    result.deadline = deadline.get("value") if isinstance(deadline, dict) else None

    return result
