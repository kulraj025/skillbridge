# SkillBridge system architecture

Status: design approved for implementation. Updated for the opportunity-aggregator scope.

## 1. Purpose

SkillBridge ingests opportunity listings from legally accessible Korean sources,
normalizes them into one schema, and matches them against a student profile with
a score the student can inspect and challenge.

The hard part is not the matching. It is **reliable, permitted, explainable
ingestion**. Everything else is downstream of it.

## 2. Layered architecture

```text
┌──────────────────────────────────────────────────────────────┐
│ 1. Sources                                                    │
│    Official APIs · official feeds · permitted endpoints ·     │
│    partner feeds · link-only references                       │
└───────────────────────────┬──────────────────────────────────┘
                            │  fetch_opportunities()
┌───────────────────────────▼──────────────────────────────────┐
│ 2. Source adapter layer        backend/app/sources/<name>/   │
│    Access-policy gate → fetch → raw record                   │
└───────────────────────────┬──────────────────────────────────┘
                            │  normalize_opportunity()
┌───────────────────────────▼──────────────────────────────────┐
│ 3. Normalization + enrichment                                │
│    language detect → clean → requirement/skill extraction →  │
│    experience, language, location, salary, hours, deadline   │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│ 4. Persistence                                                │
│    dedupe → upsert (source, source_job_id) → opportunities   │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
┌───────────────▼──────────────┐  ┌────────────▼───────────────┐
│ 5a. Search + filters        │  │ 5b. Matching engine        │
│    SQL + optional pgvector   │  │ rules → optional semantic  │
│    structured filters       │  │ weighted, explainable      │
└───────────────┬──────────────┘  └────────────┬───────────────┘
                └──────────────┬───────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│ 6. Presentation                                               │
│    feed · filters · match explanation · original source link  │
│    saves · applications · alerts                             │
└──────────────────────────────────────────────────────────────┘
```

## 3. Ingestion pipeline

Each source runs through an identical pipeline so behaviour is comparable and testable.

```text
fetch_opportunities()
  → raw record (source-native shape)
  → normalize_opportunity()
  → RawOpportunity (stable internal shape)
  → enrich()  [language detect, extraction, translation]
  → Opportunity (persisted shape)
  → validate_opportunity()
  → dedupe against existing rows
  → upsert + refresh last_seen_at
```

Rules:

- **A source never writes to the database directly.** Adapters return records; one
  ingestion service owns persistence. This keeps dedupe, expiry, and provenance
  logic in exactly one place.
- **Original text is always preserved.** `description_original` and
  `original_language` are immutable. Any translation is stored separately and
  labelled. We never overwrite what the employer wrote.
- **Extraction is optional, never destructive.** If the NLP pipeline fails, the
  opportunity is still stored and shown with raw text. A parsing failure must not
  lose a listing.
- **Every write records provenance** (source, source_job_id, fetched_at,
  content_hash) so any row can be traced back to its origin.

## 4. Freshness model

Do not claim "real-time" unless a source genuinely supports it.

| Mode | Meaning | UI wording |
| --- | --- | --- |
| `push` | Source sends a webhook | "Just posted" |
| `realtime` | API supports change feed | "Updated X minutes ago" |
| `interval` | Polled every N minutes | "Synchronized 12 min ago" |
| `manual` | Student adds a link themselves | "Added by you" |

Every opportunity exposes `last_seen_at` and the source's configured interval.
The UI renders the real interval, never an invented one.

### Expiry

An opportunity becomes `expired` when either:

- it is absent from a source fetch after `miss_threshold` consecutive syncs, or
- `deadline` has passed, or
- the source marks it closed.

Expired rows are **not** recommended and are excluded from feeds and search by
default. They are retained for history and analytics, never deleted, so
"posted 3 months ago, closed" remains answerable.

## 5. Technology decisions

| Concern | MVP | Why | Later |
| --- | --- | --- | --- |
| API | FastAPI (Python) | Already built; async I/O fits ingestion | unchanged |
| Database | PostgreSQL | Required for `jsonb`, full-text, constraints | unchanged |
| Vector search | pgvector | Same database, no extra service | scale out if needed |
| Jobs | Redis + RQ **or** APScheduler | RQ is far lighter than Celery for this load | Celery if fan-out grows |
| Frontend | React + Vite + TS + Tailwind | Matches §19; current prototype UI is throwaway | unchanged |
| NLP | rule-based first | Deterministic, explainable, no model download | embeddings added behind a flag |

### On the job queue

Celery is specified in §19. For MVP sync intervals of 5–60 minutes with a handful
of sources, Celery + Redis is operational overhead without benefit. Recommend
**RQ** (or APScheduler if Redis is unwanted) and revisit when sync concurrency
or per-opportunity AI work actually needs fan-out. This is a deliberate
deviation from §19 and should be confirmed before implementation.

### On embeddings

`sentence-transformers` multilingual models are ~500MB and need a download.
Embeddings are therefore **Stage 8, not MVP** (§25). The rule-based matcher
already produces the weighted score and the explanation, so the product is
demonstrable without any model. The semantic stage adds recall, and the
interface is designed so it can be added without touching the score contract.

## 6. Trust and eligibility boundary

This is a product requirement, not an implementation detail (§23).

- SkillBridge **never** asserts that a student may legally work in Korea.
- Visa/work-eligibility is displayed only when the employer or source stated it,
  attributed to them: *"International applicants: stated as accepted by the
  employer."*
- When unstated: *"Eligibility: not specified by the source."*
- Match scores are labelled as estimates: *"SkillBridge match: 87%"*, never
  "87% chance of getting the job".
- The application always happens on the original platform. SkillBridge is never
  the employer and never proxies an application.

## 7. Observability

- `sync_logs` records per-source run: status, counts (new/updated/expired/
  duplicate), duration, error.
- Enrichment failures are recorded per opportunity, not just per run, so a
  partially-degraded pipeline is visible.
- An admin view shows source health from `sync_logs`. It is an internal
  operational tool and is not part of the student product surface.

## 8. Deployment

Single `docker compose up` for local development: `api`, `web`, `postgres`,
`redis`. Cloud deployment is deferred until ingestion is proven; the constraint
is that the same containers move to ECS/Cloud Run/GKE without code changes,
which is why config is environment-driven and no service writes to local disk.
