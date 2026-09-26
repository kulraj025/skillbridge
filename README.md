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

**Status:** Release 1 (student workflow) prototype is runnable.

Implemented today:

- Student profile with skills and project evidence
- Opportunity input with an optional required/preferred skill split
- Requirement extraction from the opportunity description
- Match score with matched skills, gaps, project evidence, and a written explanation
- Interactive 3D bridge scene that visualizes the live match result
- Sample data endpoint for a fast demo
- Unit tests, GitHub Actions CI, and a Docker image

Still planned for Release 1:

- Skill-gap action plan
- Saved opportunities and history
- Optional CV or GitHub import
- Labeled evaluation dataset for scoring quality

Releases 2 and 3 (career office and recruiter) are unchanged and still gated on student validation.

## Run it locally

Full instructions are in [`docs/RUNNING_LOCALLY.md`](docs/RUNNING_LOCALLY.md). The short version:

```powershell
cd "C:\Users\ADMIN\Documents\Default Project\skillbridge"
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload
```

Then open `http://127.0.0.1:8000` and click **Load sample data**.

With Docker:

```powershell
docker compose up --build
```

## Matching in this prototype

Matching is deterministic and inspectable. It is intentionally not a black-box model yet:

- A curated skill catalog detects known skill phrases in the description
- Skills match on word boundaries, so `sql` does not match `postgresql`
- Required and preferred skills are scored separately
- Project text is scanned to show which project supports which skill
- The score, the matched list, and the gaps are all returned in the API response

This rule-based version exists so the explanation quality can be evaluated against a labeled dataset before any model is introduced.

## The 3D bridge scene

`frontend/three-scene.js` draws a rotating 3D diagram: your skills on the left,
the role requirements on the right, and a glowing bridge for every requirement
you can back with evidence. Gaps stay visibly open, because "what you cannot
prove yet" is the more useful half of the message.

The scene reflects the **actual** match result. Clicking **Load sample data** or
running a match repopulates it, so the graphic is never decorative fiction.

It is written against Canvas 2D with a hand-rolled perspective projection. The
scene only needs points and lines, so shipping a WebGL library would cost more
than it returns. Rendering work is skipped while the canvas is off screen.

Accessibility and performance behaviour:

- `prefers-reduced-motion: reduce` disables rotation, pulses, and reveals
- Animation stops via `IntersectionObserver` when the canvas scrolls away
- The layout stays readable without JavaScript; reveal styles are scoped to `.js`
- Hover tooltips are duplicated as text in the legend for assistive technology
- Device pixel ratio is capped at 2 to avoid huge buffers on dense displays

The projection and graph-building math is unit tested:

```powershell
node --test frontend/tests/scene.test.js
```

## Technology direction

Prototype today:

- **Backend:** Python FastAPI
- **Storage:** SQLite via the standard library (no external service required)
- **Frontend:** dependency-free HTML, CSS, and JavaScript
- **CI/CD:** GitHub Actions
- **Deployment:** Docker

Production direction:

- **Frontend:** Next.js/React for the product UI
- **Backend:** Python FastAPI
- **Database:** PostgreSQL
- **Semantic search:** pgvector in a later milestone
- **Document parsing:** PDF/Markdown ingestion with consent
- **Evaluation:** labeled skill/opportunity dataset and human review

The prototype uses SQLite and a plain frontend so it can be run and reviewed with one command. The domain model and API shape are designed to migrate to the production stack without a rewrite.

## Documentation

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/USER_RESEARCH_PLAN.md`](docs/USER_RESEARCH_PLAN.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)
- [`docs/RUNNING_LOCALLY.md`](docs/RUNNING_LOCALLY.md)

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service check |
| `POST` | `/api/profiles` | Create a student profile |
| `GET` | `/api/profiles/{id}` | Profile with match history |
| `POST` | `/api/opportunities` | Create an opportunity |
| `GET` | `/api/opportunities` | List opportunities |
| `POST` | `/api/matches` | Create an explainable match |
| `POST` | `/api/demo` | Load sample profile and opportunity |

Interactive API docs are available at `http://127.0.0.1:8000/docs` while the server is running.

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
