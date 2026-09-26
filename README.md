# SkillBridge

**SkillBridge** is an explainable AI skill and opportunity matching platform for students, career offices, and recruiters.

**Tagline:** _Turn skills into evidence-backed opportunities._

SkillBridge helps a student understand:

- Which skills they have already demonstrated
- Which requirements an opportunity expects
- Why an opportunity is a strong or weak match
- Which gaps should be addressed next
- Which project, course, or training step could close a gap

Career offices and recruiters use the same evidence model to review opportunities and candidates. The system supports human decisions; it does not automatically reject students or applicants.

## The problem

Student abilities are spread across several places:

- CVs and résumés
- GitHub repositories
- Projects
- Coursework
- Leadership and volunteering
- Certifications and workshops

Meanwhile, opportunity descriptions contain many implied and technical requirements. Students often do not know which requirements matter, which skills they already have, or what evidence an employer needs.

Career offices and recruiters also need a repeatable way to review profiles without relying on informal impressions.

## Users and roles

### Student

The primary user. A student can:

- Create a profile
- Add skills and project evidence
- Import a CV or GitHub profile
- Paste an opportunity description
- View an evidence-based match
- Create a skill-gap plan
- Save and track opportunities

### Career office

A potential institutional customer. A career office can:

- Publish approved opportunities
- Review structured student profiles
- View aggregate cohort skill trends
- Monitor student participation and outcomes
- Export human-reviewed shortlists

### Recruiter or employer

A later-stage user. A recruiter can:

- Create an opportunity
- Search for verified skills and project evidence
- Compare candidates using transparent criteria
- Save a human-reviewed shortlist

### Mentor or partner organization

An optional partner that can publish opportunities, events, workshops, or projects.

## MVP principle

Build one core matching engine and three role-based interfaces. Do not build three unrelated products.

### Release 1 — Student workflow

1. Student profile
2. Skills and project evidence
3. Paste a job or opportunity description
4. Requirement extraction
5. Match score with evidence and gaps
6. Skill-gap action plan
7. Saved opportunities

### Release 2 — Career-office workflow

1. Organization account
2. Opportunity publishing
3. Cohort-level analytics
4. Human review queue
5. Privacy-safe exports

### Release 3 — Recruiter workflow

1. Search verified skills
2. Candidate comparison
3. Shortlist and review notes
4. Opportunity performance analytics

## Responsible AI boundary

SkillBridge may assist with:

- Extracting structured information
- Summarizing opportunity descriptions
- Comparing skills with requirements
- Explaining evidence and gaps
- Recommending learning or project steps

SkillBridge must not:

- Automatically reject or rank candidates for hiring
- Make admissions or grading decisions
- Scrape private personal data
- Store passport numbers, national IDs, or grades
- Promise that a student will get a job
- Replace human judgment

Every match must be explainable and open to correction by the student.

## Current repository stage

The first repository milestone is the product and data foundation:

- Product scope
- User roles
- Data model
- API direction
- Research plan
- Implementation roadmap

The working application will be added incrementally after the scope is validated.

## Technology direction

- **Frontend:** Next.js/React for the product UI
- **Backend:** Python FastAPI
- **Database:** PostgreSQL
- **Semantic search:** pgvector in a later milestone
- **Document parsing:** PDF/Markdown ingestion with consent
- **Deployment:** Docker and a managed hosting provider
- **CI/CD:** GitHub Actions
- **Evaluation:** labeled skill/opportunity dataset and human review

The first prototype may use a simpler UI or local mock data, but the domain model should be designed for the production stack.

## Documentation

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/USER_RESEARCH_PLAN.md`](docs/USER_RESEARCH_PLAN.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)

## Development principle

Every feature should answer:

```text
Who is the user?
What decision or task does this support?
What evidence is shown?
What can the human correct or override?
How will quality be measured?
```

## License decision

Choose an appropriate open-source license before publishing code beyond a portfolio repository. This project does not make that legal decision automatically.
