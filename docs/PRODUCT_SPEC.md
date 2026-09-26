# SkillBridge product specification

## 1. Product statement

SkillBridge is an explainable AI system that converts a student's profile and an opportunity description into a transparent match, evidence list, and skill-gap plan.

## 2. Problem statement

Students often have relevant experience but cannot express it in the language employers use. Career offices and recruiters need consistent evidence, but they should not lose the ability to make human decisions.

## 3. Product goals

### Student goals

- Understand what an opportunity requires
- See which existing skills match those requirements
- Identify the most important gaps
- Choose a practical next step
- Improve a CV, project portfolio, or application

### Career-office goals

- Publish opportunities consistently
- Review student evidence efficiently
- Identify cohort skill gaps
- Track participation and outcomes

### Recruiter goals

- Search for verified skills
- Compare candidates using explainable evidence
- Keep final decisions human-reviewed

## 4. Non-goals for the MVP

- Automatic rejection or ranking
- Automatic job applications
- Scraping private LinkedIn or job-board data
- Salary prediction
- Immigration or visa advice
- Replacing the career office or recruiter
- Generating unsupported claims about a student

## 5. Core user flow

```text
Student creates profile
→ Adds skills and project evidence
→ Pastes an opportunity description
→ System extracts requirements
→ System matches requirements to evidence
→ Student reviews the explanation
→ Student saves the opportunity
→ System creates a skill-gap plan
→ Student or career office reviews the result
```

## 6. Matching requirements

The first matching engine should expose:

- Required skills
- Preferred skills
- Responsibilities
- Minimum qualifications
- Seniority or education requirements
- Missing evidence
- Contradictions or ambiguous requirements

The first implementation can use structured extraction plus deterministic scoring. A semantic model may be added after the evaluation dataset exists.

## 7. Explainability requirements

Every match should show:

```text
Overall match: 78%

Evidence:
- Built a PHP/MySQL web application
- Used JavaScript in a deployed portfolio
- Led a student organization

Gaps:
- No React project evidence
- No SQL evidence in the current profile
- No internship experience listed

Confidence:
- High for technical keywords
- Medium for responsibility descriptions
```

The student must be able to correct extracted skills or add missing evidence.

## 8. Roles and permissions

| Role | Permissions |
|---|---|
| Student | Manage own profile, evidence, opportunities, and plans |
| Career office | Manage organization opportunities and view cohort-level analytics |
| Recruiter | Create opportunities and view candidate profiles allowed by consent |
| Mentor | Share opportunities and review student-requested guidance |
| Admin | Manage security, audit, and policy settings |

No role receives automatic hiring authority.

## 9. MVP success measures

- Profile completion rate
- Time to understand an opportunity description
- Student-rated usefulness of explanations
- Precision of extracted requirements on a labeled test set
- Number of gaps converted into a learning or project action
- Career-office time saved per review
- Correction rate for extracted skills

Do not claim job-placement guarantees.

## 10. Privacy requirements

- Collect only data needed for the matching workflow
- Show what is stored and why
- Allow students to export or delete their data
- Do not store sensitive identity documents
- Separate career-office analytics from individual student views
- Record who viewed or exported candidate data
- Obtain consent before reusing CV or project content
