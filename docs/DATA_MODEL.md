# SkillBridge data model

The model is designed around evidence and reviewability. AI-generated fields should store the model, version, and confidence so a user can understand how a result was produced.

## Entities

### User

- `id`
- `role`: `student`, `career_office`, `recruiter`, `mentor`, `admin`
- `display_name`
- `created_at`

### StudentProfile

- `id`
- `user_id`
- `university`
- `major`
- `graduation_year`
- `preferred_languages`
- `availability`
- `consent_version`
- `created_at`
- `updated_at`

### Skill

- `id`
- `name`
- `normalized_name`
- `category`
- `created_at`

### Evidence

- `id`
- `profile_id`
- `skill_id`
- `type`: `project`, `coursework`, `certificate`, `volunteering`, `employment`, `other`
- `title`
- `description`
- `source_url`
- `source_type`
- `verification_status`: `student_asserted`, `organization_reviewed`, `verified`
- `consent_status`
- `created_at`

### Opportunity

- `id`
- `organization_id`
- `title`
- `description`
- `source_url`
- `location`
- `employment_type`
- `deadline`
- `status`
- `created_at`

### Requirement

- `id`
- `opportunity_id`
- `text`
- `type`: `required_skill`, `preferred_skill`, `responsibility`, `qualification`, `other`
- `importance`
- `source_span`
- `extraction_confidence`
- `created_at`

### Match

- `id`
- `profile_id`
- `opportunity_id`
- `run_id`
- `score`
- `status`: `suggested`, `reviewed`, `confirmed`, `rejected_by_human`
- `explanation_json`
- `created_at`

### SkillGap

- `id`
- `match_id`
- `requirement_id`
- `current_evidence`
- `target_evidence`
- `priority`
- `recommended_action`
- `status`

### Review

- `id`
- `match_id`
- `reviewer_id`
- `decision`
- `note`
- `created_at`

### AuditEvent

- `id`
- `actor_id`
- `action`
- `entity_type`
- `entity_id`
- `metadata_json`
- `created_at`

## Important relationships

```text
User 1 ── 1 StudentProfile
StudentProfile 1 ── many Evidence
Evidence many ── many Skills
Opportunity 1 ── many Requirement
StudentProfile 1 ── many Match
Opportunity 1 ── many Match
Match 1 ── many SkillGap
Match 1 ── many Review
```

## Design rules

- Never store an AI explanation without the evidence and requirement references it used.
- Keep source URLs and source spans where possible.
- Separate student-asserted evidence from organization-verified evidence.
- Use aggregate cohort views for institutions; do not expose private student data by default.
- Make deletion and consent status explicit.
