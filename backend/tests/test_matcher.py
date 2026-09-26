import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.matcher import contains_term, extract_skills, match_profile_to_opportunity


class MatcherTests(unittest.TestCase):
    def test_extracts_known_skills_from_description(self):
        skills = extract_skills("Build Python services with SQL and Git.")
        self.assertIn("python", skills)
        self.assertIn("sql", skills)
        self.assertIn("git", skills)

    def test_skills_match_on_word_boundaries(self):
        self.assertTrue(contains_term("Experience with REST APIs is helpful", "rest api"))
        self.assertTrue(contains_term("We use Git and Docker", "git"))
        self.assertFalse(contains_term("PostgreSQL experience", "sql"))
        self.assertFalse(contains_term("Strong JavaScript skills", "java"))
        self.assertFalse(contains_term("Looking for a developer", "c++"))
        self.assertFalse(contains_term("Built a web app", "c"))

    def test_match_exposes_evidence_and_gaps(self):
        profile = {
            "skills": ["Python", "Communication"],
            "projects": ["Built a Python API and communicated with a team"],
        }
        opportunity = {
            "description": "Looking for Python, SQL, and REST API experience.",
            "required_skills": [],
            "preferred_skills": ["Communication"],
        }

        result = match_profile_to_opportunity(profile, opportunity)

        self.assertIn("python", result["matched_required"])
        self.assertIn("sql", result["missing_required"])
        self.assertIn("python", result["extracted_requirements"])
        self.assertTrue(result["evidence"])
        self.assertGreater(result["score"], 0)


if __name__ == "__main__":
    unittest.main()
