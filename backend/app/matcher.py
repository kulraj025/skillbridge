"""Transparent, deterministic matching for the first SkillBridge prototype.

The first version intentionally uses explainable rules instead of hiding a
model score. The scoring function is designed to be replaced or extended after
a labeled evaluation dataset exists.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Mapping, Optional

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

SKILL_CATALOG = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "sql",
    "mysql",
    "postgresql",
    "html",
    "css",
    "php",
    "c++",
    "machine learning",
    "deep learning",
    "natural language processing",
    "generative ai",
    "git",
    "github",
    "rest api",
    "fastapi",
    "docker",
    "aws",
    "data analysis",
    "figma",
    "communication",
    "teamwork",
    "leadership",
    "project management",
]


def normalize(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall((value or "").lower()))


def clean_values(values: Iterable[str]) -> List[str]:
    result = []
    seen = set()
    for value in values or []:
        text = " ".join(str(value).lower().split())
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


@lru_cache(maxsize=512)
def _term_pattern(term: str) -> "re.Pattern[str]":
    escaped = re.escape(term)
    if re.search(r"[a-z]$", term):
        escaped = f"{escaped}s?"
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def contains_term(text: str, term: str) -> bool:
    """Match a skill term on word boundaries instead of raw substrings.

    Substring matching produced false positives such as ``c++`` matching any
    word containing the letter ``c``, or ``sql`` matching ``postgresql``.
    """

    normalized_term = " ".join(str(term or "").lower().split())
    if not normalized_term:
        return False
    normalized_text = " ".join(str(text or "").lower().split())
    return bool(_term_pattern(normalized_term).search(normalized_text))


def find_term(text: str, term: str) -> Optional[Dict[str, Any]]:
    """Return the matched phrase and its span, for auditable evidence.

    Offsets refer to the whitespace-normalised lowercase text used for
    matching, not the original string. The matched ``phrase`` is the useful
    part: it is what gets shown to a student as the evidence for a claim.
    """

    normalized_term = " ".join(str(term or "").lower().split())
    if not normalized_term:
        return None
    normalized_text = " ".join(str(text or "").lower().split())
    match = _term_pattern(normalized_term).search(normalized_text)
    if not match:
        return None
    return {
        "term": normalized_term,
        "phrase": match.group(0),
        "start": match.start(),
        "end": match.end(),
        "text": normalized_text,
    }


def extract_skills(description: str) -> List[str]:
    """Extract known skill phrases from an opportunity description."""

    return [skill for skill in SKILL_CATALOG if contains_term(description, skill)]


def find_evidence(projects: Iterable[str], skills: Iterable[str]) -> List[Dict[str, str]]:
    evidence = []
    for project in projects or []:
        matched = [skill for skill in skills if contains_term(project, skill)]
        if matched:
            evidence.append({"project": project, "matched_skills": ", ".join(matched)})
    return evidence


def match_profile_to_opportunity(
    profile: Mapping[str, Any],
    opportunity: Mapping[str, Any],
) -> Dict[str, Any]:
    profile_skills = set(clean_values(profile.get("skills", [])))
    required = clean_values(
        list(opportunity.get("required_skills", []))
        + extract_skills(str(opportunity.get("description", "")))
    )
    preferred = clean_values(opportunity.get("preferred_skills", []))
    projects = clean_values(profile.get("projects", []))

    matched_required = [skill for skill in required if skill in profile_skills or any(contains_term(project, skill) for project in projects)]
    missing_required = [skill for skill in required if skill not in matched_required]
    matched_preferred = [skill for skill in preferred if skill in profile_skills or any(contains_term(project, skill) for project in projects)]
    evidence = find_evidence(projects, matched_required + matched_preferred)

    required_ratio = len(matched_required) / len(required) if required else 0.5
    preferred_ratio = len(matched_preferred) / len(preferred) if preferred else 0.5
    evidence_bonus = min(0.1, 0.03 * len(evidence))
    score = round(min(1.0, 0.65 * required_ratio + 0.25 * preferred_ratio + evidence_bonus), 4)

    reasons = []
    if matched_required:
        reasons.append("Your profile shows evidence for: " + ", ".join(matched_required[:5]) + ".")
    else:
        reasons.append("No required-skill evidence is visible in the current profile.")
    if matched_preferred:
        reasons.append("You also match preferred skills: " + ", ".join(matched_preferred[:5]) + ".")
    if missing_required:
        reasons.append("Missing or unverified requirements: " + ", ".join(missing_required[:6]) + ".")
    if not reasons:
        reasons.append("Add more skills and project evidence to improve this explanation.")

    return {
        "score": score,
        "extracted_requirements": required,
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "evidence": evidence,
        "explanation": " ".join(reasons),
    }
