# SkillBridge

**SkillBridge** is an explainable opportunity-matching platform for university students in South Korea. It collects listings from legally accessible Korean sources, normalizes them into one schema, and matches them against a student profile — showing the score, the factors behind it, and the original posting.

**Tagline:** _Tell Skill Bridge who you are and what you want. It searches the opportunity ecosystem for you._

## The problem

A student in Korea searching for relevant work does this manually:

```text
Search Alba
→ Search Karrot
→ Search Albamoon
→ Search the university website
→ Translate Korean
→ Check requirements
→ Compare jobs
```

Listings are scattered across several platforms, often written only in Korean, and must be filtered by hand against a student's actual skills, major, language level, location, availability, and goals. A student also cannot reliably tell, from a Korean listing, whether they meet a requirement, whether it is mandatory or preferred, or whether they may legally work in Korea.

## What SkillBridge does

```text
Student Profile
      ↓
  SkillBridge
      ↓
Multiple Opportunity Sources
      ↓
   Normalize
      ↓
    Filter
      ↓
Explainable Matching
      ↓
  Personalized Feed
      ↓
Original Application Link
```

The application always happens on the original platform. SkillBridge is never the employer and never submits anything on a student's behalf.

## Users and roles

### Student

The only user in the MVP. A student can:

- Build a profile with skills, major, TOPIK level, locations, and availability
- See a personalized, scored feed
- Read why each listing matched and what is missing
- Filter, search, and use natural-language search
- Save opportunities, track applications, and set alerts
- Reach the original posting in one click
- Correct any extracted field

### Admin

Operational only: source health, sync history, failure counts. Not a product surface.

Career-office and recruiter surfaces are **deferred**, not abandoned. The role enum stays extensible so adding them needs no migration.

## Responsible AI boundary

SkillBridge **may**:

- Extract structured requirements from listings
- Translate and summarize descriptions
- Compare a profile with requirements
- Explain factors, gaps, and uncertainty
- Surface the original posting and its source

SkillBridge **must not**:

- Bypass CAPTCHAs, authentication, paywalls, rate limits, or robots policies
- Scrape a source without documented permission
- Infer or advise on visa or work eligibility
- Automatically reject or rank students or candidates
- Make admissions or grading decisions
- Submit applications on a student's behalf
- Present a score as a probability of getting a job
- Store passport numbers, national IDs, or grades
- Replace human judgment

Every match must be explainable, must report what it could not assess, and must
be open to correction by the student.

## MVP principle

The core technical challenge is **reliable opportunity ingestion + normalization
+ matching + freshness + source transparency** — not a large AI surface. The
MVP proves that a student can find a relevant opportunity faster than by
searching five platforms, and that every score can be justified.

Staged plan in [`docs/ROADMAP.md`](docs/ROADMAP.md). Stage 1 — verifying what
each source actually permits — gates all ingestion work.

## Current repository stage

**Status:** design complete for the aggregator MVP. The existing prototype is
runnable and its matching engine carries forward.

Implemented and tested today:

- Student profile with skills and project evidence
- Opportunity input with an optional required/preferred skill split
- Requirement extraction from the opportunity description
- Deterministic match score with matched skills, gaps, evidence, and explanation
- Word-boundary skill matching (`sql` no longer matches `postgresql`)
- Interactive 3D bridge scene rendering the live match result
- Sample data endpoint for a fast demo
- Unit tests, GitHub Actions CI, and a Docker image

Next, per the roadmap:

1. Verify what each target source actually permits, and record it
2. PostgreSQL schema and the ingestion pipeline
3. Korean normalization and requirement extraction
4. Search and filters
5. Weighted explainable matching on the real profile shape
6. Saves, applications, and alerts
7. Labeled evaluation set, then semantic recall

The prototype stays runnable while this proceeds. `matcher.py` is extended, not
replaced, and the 3D scene is wrapped as a React component rather than
rewritten.

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

## Track your streak

Progress is measured from real commit history, not from a counter someone can
edit. Regenerate the report at any time:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\update-streak.ps1
python scripts\streak.py --json     # just the numbers
```

A Windows scheduled task named `SkillBridge-StreakUpdater` regenerates
`docs/STREAK.md` every day at 21:00. It only reads history: it never commits
and never pushes, so no token has to live on disk. To remove it:

```powershell
Unregister-ScheduledTask -TaskName SkillBridge-StreakUpdater -Confirm:$false
```

See [`docs/STREAK.md`](docs/STREAK.md) for the current numbers.

## Source access policy

This is the constraint that decides what the platform can actually offer, so it
is stated early. See [`docs/SOURCE_ADAPTERS.md`](docs/SOURCE_ADAPTERS.md).

Automated access is permitted **only** when it is documented and current. Each
source declares one mode, with the evidence recorded in the source registry:

| Mode | Meaning |
| --- | --- |
| `official_api` | Documented API, respecting documented limits |
| `official_feed` | Published RSS/Atom or export |
| `permitted_endpoint` | Endpoint documented as public |
| `partner_feed` | Agreed feed, with the agreement on file |
| `link_only` | No permitted access — offer a scoped search link instead |
| `blocked` | Prohibited — no adapter, and CI fails if one appears |

`link_only` is a **first-class outcome, not a failure**. It produces a deep
search URL scoped to the student's profile, which still replaces several manual
searches. Inventing a scraper to fill the registry would produce a demo that
cannot legally run.

## Matching

Matching is deterministic and inspectable, and stays that way through the MVP:

- A curated skill catalog detects known skill phrases
- Skills match on word boundaries, so `sql` does not match `postgresql`
- Korean aliases resolve `파이썬` and `Python` to one skill
- Required and preferred are scored separately — `우대` means *preferred*
- Weights are configurable and validated to sum to 1.0
- An unevaluable factor is reported as **unknown**, never imputed as zero
- The score, per-factor detail, gaps, and caveats are all returned in the response

The rule-based engine exists so explanation quality can be measured against a
labeled dataset before any model is introduced. Semantic embeddings come at
Stage 9, behind a flag, for recall only — they never overwrite the rule-based
score.

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

Production direction (per [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)):

- **Frontend:** React + Vite + TypeScript + Tailwind
- **Backend:** Python FastAPI, unchanged
- **Database:** PostgreSQL, with `jsonb` and partial indexes
- **Vector search:** pgvector at Stage 9
- **Background sync:** RQ or APScheduler, not Celery, until fan-out requires it
- **NLP:** deterministic extraction first, embeddings behind a flag
- **Evaluation:** labeled listing set and human review

The prototype uses SQLite and a plain frontend so it can be run and reviewed with
one command. The domain model, matching engine, and 3D scene carry forward into
the production stack without a rewrite.

## Documentation

Design and specification:

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/SOURCE_ADAPTERS.md`](docs/SOURCE_ADAPTERS.md)
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md)
- [`docs/OPPORTUNITY_SCHEMA.md`](docs/OPPORTUNITY_SCHEMA.md)
- [`docs/MATCHING_DESIGN.md`](docs/MATCHING_DESIGN.md)
- [`docs/API_SPEC.md`](docs/API_SPEC.md)
- [`docs/FOLDER_STRUCTURE.md`](docs/FOLDER_STRUCTURE.md)
- [`docs/ROADMAP.md`](docs/ROADMAP.md)

Process:

- [`docs/USER_RESEARCH_PLAN.md`](docs/USER_RESEARCH_PLAN.md)
- [`docs/RUNNING_LOCALLY.md`](docs/RUNNING_LOCALLY.md)

Accountability:

- [`docs/STREAK.md`](docs/STREAK.md) — generated from `git log`, not written by hand

## API

Implemented today in the prototype:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service check |
| `POST` | `/api/profiles` | Create a student profile |
| `GET` | `/api/profiles/{id}` | Profile with match history |
| `POST` | `/api/opportunities` | Create an opportunity |
| `GET` | `/api/opportunities` | List opportunities |
| `POST` | `/api/matches` | Create an explainable match |
| `POST` | `/api/demo` | Load sample profile and opportunity |

The target MVP API is specified in [`docs/API_SPEC.md`](docs/API_SPEC.md) and
adds filters, recommendations, natural-language search, saves, applications,
alerts, sources, and corrections.

Interactive API docs are available at `http://127.0.0.1:8000/docs` while the server is running.

## Development principle

Every feature should answer:

```text
Who is the user?
What decision or task does this support?
What evidence is shown?
What can the human correct or override?
How will quality be measured?
Is the data access permitted?
```

## License decision

Choose an appropriate open-source license before publishing code beyond a
portfolio repository. This project does not make that legal decision
automatically.
