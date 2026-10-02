"""Request models for the SkillBridge API."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    major: str = Field(default="", max_length=120)
    graduation_year: Optional[int] = Field(default=None, ge=1950, le=2100)
    skills: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)


class OpportunityCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    organization: str = Field(..., min_length=1, max_length=140)
    description: str = Field(..., min_length=1, max_length=8000)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    source_url: str = Field(default="", max_length=500)


class MatchCreate(BaseModel):
    profile_id: str = Field(..., min_length=1)
    opportunity_id: str = Field(..., min_length=1)


class ExtractCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=8000)
    posted_at: Optional[datetime] = None
    today: Optional[date] = None
