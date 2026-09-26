# SkillBridge roadmap

## Milestone 0 — Product foundation

- Define users and roles
- Define the student-first MVP
- Define the evidence-based data model
- Define safety and privacy boundaries
- Prepare user-research questions

## Milestone 1 — Student workflow prototype

- Student profile form
- Skills and project evidence entry
- Opportunity description input
- Structured requirement extraction
- Deterministic match score
- Evidence and gap explanation
- Skill-gap action plan

## Milestone 2 — Evaluation dataset

- Create a labeled set of opportunity descriptions
- Manually mark requirements and important skills
- Measure extraction precision and recall
- Compare scoring rules
- Record human corrections

## Milestone 3 — Document and GitHub integrations

- CV upload with consent
- GitHub profile import
- Source links and project evidence
- Privacy controls and deletion requests

## Milestone 4 — Career-office dashboard

- Organization account
- Approved opportunity publishing
- Cohort skill trends
- Human review queue
- Aggregate, privacy-safe analytics

## Milestone 5 — Recruiter workflow

- Verified-skill search
- Candidate comparison
- Consent-based shortlists
- Export and audit history

## Milestone 6 — Pilot and deployment

- Test with 10–20 students
- Test with one career office or mentor group
- Deploy a read-only demo
- Measure explanation usefulness and time saved
- Publish a case study with real, anonymized results

## Future technical work

- Semantic embeddings with pgvector
- Document retrieval and grounded explanations
- Model/provider comparison
- CI evaluation gates
- Model monitoring and drift detection

## Safety gate

Do not add automatic ranking, rejection, admissions decisions, or unconsented data collection. Any future feature that makes a high-impact decision without human review requires a separate ethics and privacy review.
