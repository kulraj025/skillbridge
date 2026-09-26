# SkillBridge roadmap

Rewrite for the opportunity-aggregator scope. Every stage states what is
demonstrable when it is done, and what is explicitly not built yet.

Deferred work is written down rather than quietly dropped, so the reasoning
survives.

## Stage 0 — Foundations (done)

Product definition, data model, matching rationale, and a runnable student-flow
prototype with an explainable deterministic matcher.

Carried forward: `matcher.py` word-boundary matching, the 3D bridge scene and its
17 tests, the save/API error diagnostics, and the CI gate.

## Stage 1 — Source access verification

**This gates everything downstream.**

For each target source, determine and record the current access position: terms
of service, `robots.txt`, any public API, any feed, any partner or affiliate
program. Record the finding — including "no documented access" — in
`registry.yaml` with the URL checked and the date.

Deliverable: a registry where every entry has a mode and evidence, and an honest
statement of how many sources can be enabled at which mode.

If the answer is "one feed and everything else link-only", the MVP proceeds
link-only. That is a valid outcome, not a failure, and it is recorded as one.

## Stage 2 — Ingestion pipeline

- PostgreSQL schema and migrations
- Repository layer over the new schema
- Adapter protocol plus the `link_only` adapter
- `ingest.py` as sole persistence owner
- Upsert on `(source_id, source_job_id)`, `last_seen_at` refresh
- `sync_logs` written per run

Demonstrable: a sync run against a permitted feed populates the database with
correct provenance, and a second run updates rather than duplicates.

## Stage 3 — Normalization and validation

- `RawOpportunity` → `Opportunity`
- Validation rules from `OPPORTUNITY_SCHEMA.md`
- Dedupe and canonical grouping
- Expiry detection by deadline and by repeated absence

Demonstrable: the same listing from three sources appears once, listing all
three, with the canonical one shown.

## Stage 4 — Korean processing

- Language detection and text cleaning
- Translation behind a provider interface, cached by content hash
- Rule-based extraction: skills, required vs preferred, experience, language,
  location, salary, hours, deadline, eligibility
- Korean↔English alias gazetteer

Demonstrable: a Korean listing becomes a fully structured opportunity with the
original text preserved, and the `우대`/`필수` distinction is correct.

## Stage 5 — Search and filters

- `GET /api/opportunities` with the full filter set
- Cursor pagination
- `hidden_by_filters` disclosure
- Scoped `link_only` search links from the profile

Demonstrable: a student filters to Busan software internships with Python, and
sees why anything was hidden.

## Stage 6 — Student profile and matching

- Profile CRUD
- `MatchWeights` with the sum-to-one validation
- Hard filters, then weighted scoring with per-factor detail
- `None` for unevaluable factors, with weight redistribution
- Explanation payload with `factors`, `unknown_factors`, `caveats`

Demonstrable: every score is decomposed into factors a student can inspect and
dispute, and nothing claims legal work eligibility.

## Stage 7 — Saves, applications, alerts

- Saved opportunities with notes
- Application Kanban
- Alerts from structured filters
- Notifications, deduplicated per opportunity

Demonstrable: a student saves, tracks, and is notified — with the original
posting always one click away.

## Stage 8 — Evaluation

- 100+ hand-labeled real listings
- Extraction precision and recall per field
- Required vs preferred accuracy
- Top-10 recall for known profiles
- Explanation agreement with labels

Published numbers, including the poor ones. Without this, matching quality is a
claim rather than a measurement, and Stage 9 has no basis.

## Stage 9 — Semantic recall

Only after Stage 8 shows the gazetteer is the limiting factor.

- Multilingual embeddings, `embeddings` table
- pgvector similarity search
- Recall-only: never overwrites the Stage 6 score
- Threshold validated against the labeled set before it affects anything

## Stage 10 — Admin and operations

- Source health from `sync_logs`
- New/updated/expired/duplicate counts, failures, duration
- Alerting on source failure

Internal tool. Not part of the student product surface.

## Stage 11 — Pilot and deployment

- Deploy to a real environment
- Recruit pilot students from the university community
- Measure time-to-relevant-opportunity, save rate, alert usefulness
- Measure whether the explanations are read, not just rendered
- Publish a case study with real, anonymized results

## Explicitly deferred

- Authentication beyond a single local user
- Career-office and recruiter surfaces
- CV parsing and document ingestion
- Email or push notification delivery
- Any endpoint that infers work eligibility
- Any source without documented access
