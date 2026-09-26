"""FastAPI entry point for the SkillBridge student prototype."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .matcher import match_profile_to_opportunity
from .models import MatchCreate, OpportunityCreate, ProfileCreate
from .repository import (
    create_match,
    create_opportunity,
    create_profile,
    get_opportunity,
    get_profile,
    list_matches,
    list_opportunities,
    list_profiles,
)

app = FastAPI(
    title="SkillBridge API",
    version="0.1.0",
    description="Explainable skill and opportunity matching for students.",
)

init_db()


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "skillbridge", "version": "0.1.0"}


@app.get("/api/profiles")
def profiles() -> List[Dict[str, Any]]:
    return list_profiles()


@app.post("/api/profiles", status_code=status.HTTP_201_CREATED)
def profiles_create(payload: ProfileCreate) -> Dict[str, Any]:
    return create_profile(
        name=payload.name.strip(),
        major=payload.major.strip(),
        graduation_year=payload.graduation_year,
        skills=[item.strip() for item in payload.skills if item.strip()],
        projects=[item.strip() for item in payload.projects if item.strip()],
    )


@app.get("/api/profiles/{profile_id}")
def profile_detail(profile_id: str) -> Dict[str, Any]:
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": profile, "matches": list_matches(profile_id)}


@app.get("/api/opportunities")
def opportunities() -> List[Dict[str, Any]]:
    return list_opportunities()


@app.post("/api/opportunities", status_code=status.HTTP_201_CREATED)
def opportunities_create(payload: OpportunityCreate) -> Dict[str, Any]:
    return create_opportunity(
        title=payload.title.strip(),
        organization=payload.organization.strip(),
        description=payload.description.strip(),
        required_skills=[item.strip() for item in payload.required_skills if item.strip()],
        preferred_skills=[item.strip() for item in payload.preferred_skills if item.strip()],
        source_url=payload.source_url.strip(),
    )


@app.post("/api/matches", status_code=status.HTTP_201_CREATED)
def matches_create(payload: MatchCreate) -> Dict[str, Any]:
    profile = get_profile(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    opportunity = get_opportunity(payload.opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    result = match_profile_to_opportunity(profile, opportunity)
    return create_match(payload.profile_id, payload.opportunity_id, result)


@app.post("/api/demo", status_code=status.HTTP_201_CREATED)
def demo() -> Dict[str, Any]:
    profile = create_profile(
        name="Demo student",
        major="Artificial Intelligence",
        graduation_year=2027,
        skills=["Python", "JavaScript", "SQL", "Communication", "Teamwork"],
        projects=[
            "Built a Python script that cleaned survey data and stored results in a SQL database",
            "Created a JavaScript portfolio deployed with GitHub Pages",
            "Led a student organization and presented results to a large campus audience",
        ],
    )
    opportunity = create_opportunity(
        title="Junior AI Application Developer",
        organization="Sample technology company",
        description=(
            "We are looking for a junior developer to build Python services, work with SQL databases, "
            "and communicate with a product team. Experience with REST APIs and Git is helpful."
        ),
        required_skills=["Python", "SQL", "Git"],
        preferred_skills=["Communication", "Teamwork"],
        source_url="https://example.com/sample-opportunity",
    )
    return {"profile": profile, "opportunity": opportunity}


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
