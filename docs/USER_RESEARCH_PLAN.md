# SkillBridge user research plan

The project should be validated before it becomes a large platform. The research goal is not to ask students what features they want; it is to understand the decisions and evidence they actually need.

## Research questions

### Students

- How do you currently find internships and job descriptions?
- Which parts of an opportunity description are confusing?
- How do you decide which project experience to include?
- What evidence do you wish you had?
- What information would you not want an AI system to collect?

### Career offices

- How do you currently review student profiles?
- How do you publish and approve opportunities?
- Which student skills are difficult to assess?
- What information is useful at cohort level?
- What decisions must remain human?

### Recruiters or employers

- Which skills are difficult to verify?
- What evidence is useful when reviewing a student?
- How do you currently compare early-career candidates?
- What would make an AI match unacceptable?

## First interview round

Recruit:

- 5 students
- 2 career-office or student-support staff
- 2 recruiters, alumni, or mentors

Use the same question structure and record notes with consent.

## Prototype test

Test a low-fidelity workflow:

```text
Paste a job description
→ View extracted requirements
→ View match and evidence
→ Correct one extracted skill
→ Create one skill-gap action
```

Do not ask whether users like the design. Ask whether they trust the explanation, where they are confused, and what evidence is missing.

## Success signals

- Users can explain what the match score means
- Users correct at least one extracted or missing item
- Users identify a next action they would actually take
- Career-office staff can distinguish verified evidence from student claims
- Users know what the system will not decide automatically

## Failure signals

- Users treat the score as a hiring decision
- Explanations cannot be traced to evidence
- Users do not trust the source or extraction
- The product requires more personal data than the task needs
- Career offices cannot see any practical value beyond a chat interface

## Research output

Record findings in `docs/USER_RESEARCH.md` after the first round. Use the findings to update the requirement schema and the first demo dataset.
