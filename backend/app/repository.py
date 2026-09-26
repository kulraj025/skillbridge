"""Persistence operations for the SkillBridge prototype."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .db import get_connection


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid4())


def _decode_profile(row) -> Dict[str, Any]:
    result = dict(row)
    result["skills"] = json.loads(result.pop("skills_json") or "[]")
    result["projects"] = json.loads(result.pop("projects_json") or "[]")
    return result


def _decode_opportunity(row) -> Dict[str, Any]:
    result = dict(row)
    result["required_skills"] = json.loads(result.pop("required_skills_json") or "[]")
    result["preferred_skills"] = json.loads(result.pop("preferred_skills_json") or "[]")
    return result


def _decode_match(row) -> Dict[str, Any]:
    result = dict(row)
    result["matched_required"] = json.loads(result.pop("matched_required_json") or "[]")
    result["missing_required"] = json.loads(result.pop("missing_required_json") or "[]")
    result["matched_preferred"] = json.loads(result.pop("matched_preferred_json") or "[]")
    result["evidence"] = json.loads(result.pop("evidence_json") or "[]")
    result["explanation"] = json.loads(result.pop("explanation_json") or "{}")
    return result


def create_profile(
    name: str,
    major: str,
    graduation_year: Optional[int],
    skills: List[str],
    projects: List[str],
) -> Dict[str, Any]:
    profile = {
        "id": new_id(),
        "name": name,
        "major": major,
        "graduation_year": graduation_year,
        "skills_json": json.dumps(skills),
        "projects_json": json.dumps(projects),
        "created_at": utc_now(),
    }
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO profiles (id, name, major, graduation_year, skills_json, projects_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile["id"], profile["name"], profile["major"], profile["graduation_year"],
                profile["skills_json"], profile["projects_json"], profile["created_at"],
            ),
        )
    return _decode_profile(profile)


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return _decode_profile(row) if row else None


def list_profiles() -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
    return [_decode_profile(row) for row in rows]


def create_opportunity(
    title: str,
    organization: str,
    description: str,
    required_skills: List[str],
    preferred_skills: List[str],
    source_url: str,
) -> Dict[str, Any]:
    opportunity = {
        "id": new_id(),
        "title": title,
        "organization": organization,
        "description": description,
        "required_skills_json": json.dumps(required_skills),
        "preferred_skills_json": json.dumps(preferred_skills),
        "source_url": source_url,
        "created_at": utc_now(),
    }
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO opportunities
            (id, title, organization, description, required_skills_json, preferred_skills_json, source_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity["id"], opportunity["title"], opportunity["organization"],
                opportunity["description"], opportunity["required_skills_json"],
                opportunity["preferred_skills_json"], opportunity["source_url"], opportunity["created_at"],
            ),
        )
    return _decode_opportunity(opportunity)


def get_opportunity(opportunity_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    return _decode_opportunity(row) if row else None


def list_opportunities() -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM opportunities ORDER BY created_at DESC").fetchall()
    return [_decode_opportunity(row) for row in rows]


def create_match(
    profile_id: str,
    opportunity_id: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    match = {
        "id": new_id(),
        "profile_id": profile_id,
        "opportunity_id": opportunity_id,
        "score": result["score"],
        "matched_required_json": json.dumps(result["matched_required"]),
        "missing_required_json": json.dumps(result["missing_required"]),
        "matched_preferred_json": json.dumps(result["matched_preferred"]),
        "evidence_json": json.dumps(result["evidence"]),
        "explanation_json": json.dumps({"text": result["explanation"], "extracted_requirements": result["extracted_requirements"]}),
        "created_at": utc_now(),
    }
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO matches
            (id, profile_id, opportunity_id, score, matched_required_json, missing_required_json,
             matched_preferred_json, evidence_json, explanation_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match["id"], match["profile_id"], match["opportunity_id"], match["score"],
                match["matched_required_json"], match["missing_required_json"],
                match["matched_preferred_json"], match["evidence_json"], match["explanation_json"],
                match["created_at"],
            ),
        )
    return _decode_match(match)


def list_matches(profile_id: str) -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM matches WHERE profile_id = ? ORDER BY created_at DESC", (profile_id,)
        ).fetchall()
    return [_decode_match(row) for row in rows]
