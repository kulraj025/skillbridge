# Folder structure

Target layout for the aggregator MVP. The current prototype's files are marked,
so the migration path is visible rather than implied.

## Repository

```text
skillbridge/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, middleware, router mounting
│   │   ├── config.py               # env-driven settings (new)
│   │   ├── db.py                   # connection pool, migrations (new)
│   │   ├── models.py               # Pydantic request/response schemas
│   │   ├── repository.py           # persistence only, no HTTP concerns
│   │   ├── matcher.py              # matching engine — kept, extended
│   │   ├── weights.py              # MatchWeights config (new)
│   │   ├── explanations.py         # explanation payload assembly (new)
│   │   ├── routers/
│   │   │   ├── profile.py          # (new)
│   │   │   ├── opportunities.py    # (new)
│   │   │   ├── recommendations.py  # (new)
│   │   │   ├── search.py           # (new)
│   │   │   ├── saved.py            # (new)
│   │   │   ├── applications.py     # (new)
│   │   │   ├── alerts.py           # (new)
│   │   │   ├── sources.py          # (new)
│   │   │   ├── admin.py            # (new)
│   │   │   └── health.py           # (new)
│   │   ├── nlp/
│   │   │   ├── detect.py           # language detection (new)
│   │   │   ├── clean.py            # NBSP, width, spacing normalisation (new)
│   │   │   ├── translate.py        # provider interface + swappable impls (new)
│   │   │   ├── extract.py          # requirement/skill/experience extraction (new)
│   │   │   ├── salary.py           # salary parsing (new)
│   │   │   ├── hours.py            # working hours parsing (new)
│   │   │   ├── deadline.py         # deadline parsing (new)
│   │   │   ├── eligibility.py      # 외국인/TOPIK, verbatim only (new)
│   │   │   └── gazetteer.py        # Korean↔English skill aliases (new)
│   │   ├── sources/
│   │   │   ├── base.py             # OpportunitySource protocol, RawOpportunity
│   │   │   ├── registry.yaml       # access policy — the source of truth
│   │   │   ├── registry.py         # loads + validates registry (new)
│   │   │   ├── link_only.py        # generic search-link adapter
│   │   │   ├── ingest.py           # the single persistence owner
│   │   │   ├── dedupe.py           # canonical grouping
│   │   │   └── <source_name>/
│   │   │       ├── adapter.py
│   │   │       └── fixtures/       # recorded from permitted access
│   │   ├── worker/
│   │   │   ├── scheduler.py        # per-source interval scheduling
│   │   │   └── jobs.py             # sync + enrich tasks
│   │   └── migrations/             # SQL migrations
│   ├── tests/
│   │   ├── test_matcher.py         # kept
│   │   ├── test_nlp/
│   │   ├── test_sources/
│   │   └── test_api/
│   ├── data/                       # local SQLite only; gitignored
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/client.ts           # typed fetch wrapper, error surfaces method+status
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Opportunities.tsx
│   │   │   ├── OpportunityDetail.tsx
│   │   │   ├── Saved.tsx
│   │   │   ├── Applications.tsx
│   │   │   ├── Profile.tsx
│   │   │   ├── Alerts.tsx
│   │   │   └── Sources.tsx
│   │   ├── components/
│   │   │   ├── MatchExplanation.tsx
│   │   │   ├── MatchScoreRing.tsx
│   │   │   ├── EligibilityNotice.tsx
│   │   │   ├── SourceBadge.tsx
│   │   │   ├── FreshnessLabel.tsx
│   │   │   ├── FilterPanel.tsx
│   │   │   └── FilterDisclosure.tsx # "12 hidden by your filters"
│   │   └── styles/
│   ├── tests/
│   │   └── scene.test.js           # kept — 3D math is reusable
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SOURCE_ADAPTERS.md
│   ├── DATA_MODEL.md
│   ├── OPPORTUNITY_SCHEMA.md
│   ├── MATCHING_DESIGN.md
│   ├── API_SPEC.md
│   ├── FOLDER_STRUCTURE.md
│   ├── ROADMAP.md
│   └── RUNNING_LOCALLY.md
├── scripts/
│   ├── check.ps1                   # local gate — kept
│   ├── seed.py                     # labeled evaluation set loader
│   └── verify_sources.py           # CI check: registry policy is coherent
├── docker-compose.yml              # api, web, postgres, redis
└── .github/workflows/ci.yml
```

## Why the backend keeps its current shape

The existing `main.py`, `matcher.py`, `models.py`, and `repository.py` split is
already the right one: HTTP at the edge, matching in the middle, persistence
behind an interface. What changes is that `main.py` shrinks to router mounting
once the endpoints outgrow one file, and `db.py` swaps SQLite for PostgreSQL
behind the same repository interface.

`matcher.py` is extended, not replaced. Its word-boundary skill matching is
correct, tested, and the foundation for alias resolution.

`frontend/three-scene.js` is retained even though the UI moves to React: the
projection and scene-graph math is framework-independent and already has 17
tests. It is wrapped as a component, not rewritten.

## Boundaries worth enforcing

- **Adapters never write to the database.** `ingest.py` owns all persistence, so
  dedupe and provenance logic exists in exactly one place.
- **`repository.py` never imports FastAPI.** Persistence must be testable without
  an app.
- **The NLP layer is pure.** Extraction functions take text and return structures.
  They perform no I/O, so the entire pipeline is unit-testable offline.
- **Translation sits behind an interface.** Swapping providers must not touch
  callers.
- **No source module imports another source module.** Sources are independent, so
  adding one cannot break another.
