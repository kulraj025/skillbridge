# SkillBridge data model

PostgreSQL. Supersedes the earlier evidence-only model, which did not account
for multi-source ingestion.

Design rules that outrank convenience:

1. **Provenance is mandatory.** Every opportunity row can be traced to a source
   record, a fetch timestamp, and the original URL.
2. **Original text is immutable.** Translations and extractions live in separate
   columns. We never overwrite what an employer wrote.
3. **AI output is always attributable.** Extracted fields record the extractor
   version and a confidence value.
4. **Eligibility is never inferred.** Work-authorization fields store only what
   the source explicitly stated, plus who stated it.
5. **Soft deletion.** `expired_at` hides a row from feeds; it does not erase
   history.

## Entity relationships

```text
users 1 ──── 1 student_profiles
users 1 ──── * student_skills * ──── 1 skills
users 1 ──── * saved_opportunities
users 1 ──── * applications
users 1 ──── * alerts
users 1 ──── * notifications

opportunity_sources 1 ──── * opportunities
companies 1 ──── * opportunities
institutions 1 ──── * opportunities
opportunities 1 ──── * opportunity_skills * ──── 1 skills
opportunities 1 ──── * opportunities_canonical   (duplicate grouping)
opportunities 1 ──── 0..1 embeddings
opportunity_sources 1 ──── * sync_logs
```

## Tables

### users

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` PK | |
| `email` | `citext` unique | |
| `role` | `enum` | `student`, `admin` |
| `display_name` | `text` | |
| `locale` | `text` default `ko` | UI language |
| `created_at` | `timestamptz` | |
| `password_hash` | `text` | Omit entirely if the MVP stays single-user/local |

`role` is intentionally two-valued for the MVP. Career-office and recruiter
roles are deferred (§25 stages 9+); keeping the enum extensible avoids a future
migration.

### student_profiles

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK | unique |
| `university` | `text` | |
| `major` | `text` | |
| `semester` | `smallint` | e.g. 6 |
| `graduation_year` | `smallint` | |
| `topik_level` | `smallint` | 0–6. `null` = not stated |
| `english_level` | `text` | CEFR-ish free text, normalized |
| `other_languages` | `jsonb` | `[{language, level}]` |
| `preferred_job_types` | `jsonb` | enum array |
| `internship_preference` | `text` | |
| `part_time_availability` | `jsonb` | weekdays/hours |
| `preferred_locations` | `jsonb` | `[{name, lat, lon}]` |
| `transport_radius_km` | `int` | |
| `career_interests` | `jsonb` | |
| `work_eligibility_note` | `text` | **Student-supplied only. Never inferred.** |
| `experience` | `jsonb` | |
| `portfolio_urls` | `jsonb` | GitHub/LinkedIn/portfolio |
| `preferred_salary` | `numeric` | nullable |
| `remote_preference` | `text` | `remote`, `onsite`, `hybrid`, `any` |
| `consent_version` | `text` | |
| `created_at`, `updated_at` | `timestamptz` | |

`work_eligibility_note` is the student's own statement about their visa status.
SkillBridge never derives eligibility from a profile or a job description.

### skills

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `serial` PK | |
| `name` | `text` | canonical, e.g. "Python" |
| `normalized_name` | `text` unique | lowercase, punctuation-stripped |
| `category` | `text` | `language`, `framework`, `tool`, `soft`, `domain` |
| `aliases` | `jsonb` | `["py", "파이썬"]` — drives multilingual matching |

`aliases` is what lets "파이썬" and "Python" resolve to one skill. This is the
single highest-leverage field for Korean listings.

### student_skills

| Column | Type | Notes |
| --- | --- | --- |
| `profile_id` | `uuid` FK | |
| `skill_id` | `int` FK | |
| `proficiency` | `text` | `beginner`..`advanced` |
| `years` | `numeric` | |
| `is_primary` | `bool` | drives query expansion |
| `evidence` | `jsonb` | projects, coursework |

Composite PK `(profile_id, skill_id)`.

### opportunity_sources

Registry mirror. Synced from `registry.yaml` at boot so the DB reflects the
policy that is actually in force.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `serial` PK | |
| `name` | `text` unique | |
| `display_name` | `text` | |
| `mode` | `enum` | `official_api`, `official_feed`, `permitted_endpoint`, `partner_feed`, `link_only`, `blocked` |
| `category` | `text` | university, company, aggregator, government |
| `home_url` | `text` | |
| `search_url_template` | `text` | required when `mode = link_only` |
| `interval_minutes` | `int` | null for `link_only` |
| `rate_limit_per_minute` | `int` | |
| `evidence` | `jsonb` | `{type, url, checked_on, note}` |
| `enabled` | `bool` | |
| `last_sync_at` | `timestamptz` | denormalized for the admin view |

### companies

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `serial` PK | |
| `name` | `text` | |
| `normalized_name` | `text` | for dedupe |
| `website` | `text` | |
| `logo_url` | `text` | only if the source permits reuse |

### institutions

Same shape as `companies`, for universities and labs. Kept separate because a
university career center and a commercial employer have different posting
conventions and different trust expectations.

### opportunities

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` PK | |
| `source_id` | `int` FK | |
| `source_job_id` | `text` | source-native id |
| `title` | `text` | |
| `organization` | `text` | denormalized display value |
| `company_id` | `int` FK | nullable |
| `institution_id` | `int` FK | nullable |
| `description_original` | `text` | **immutable** |
| `original_language` | `text` | ISO-639-1, e.g. `ko` |
| `description_en` | `text` | machine translation, labelled as such |
| `location_text` | `text` | as written |
| `city` | `text` | normalized, e.g. `Busan` |
| `lat`, `lon` | `numeric` | only when the source supplies them |
| `salary_min`, `salary_max`, `salary_unit` | `numeric`,`text` | unit: `hour`, `month`, `year` |
| `salary_original_text` | `text` | e.g. "시급 12,000원" |
| `job_type` | `enum` | `part_time`, `internship`, `research`, `project`, `entry_level` |
| `category` | `text` | cafe, retail, software, research, marketing, … |
| `remote_type` | `text` | `remote`, `onsite`, `hybrid`, `unknown` |
| `working_hours` | `jsonb` | `{days, start, end, weekly}` |
| `required_skills` | `jsonb` | extracted, with confidence |
| `preferred_skills` | `jsonb` | extracted |
| `language_requirements` | `jsonb` | `[{language, min_level, explicit}]` |
| `education_requirements` | `jsonb` | |
| `experience_requirements` | `jsonb` | |
| `international_students_accepted` | `bool` | nullable |
| `eligibility_statement` | `text` | verbatim from source |
| `eligibility_source` | `text` | who stated it |
| `posted_at` | `timestamptz` | nullable |
| `deadline` | `timestamptz` | nullable |
| `original_url` | `text` | **required** |
| `canonical_id` | `uuid` FK self | duplicate group leader |
| `content_hash` | `text` | change detection |
| `extraction_version` | `text` | |
| `last_seen_at` | `timestamptz` | refreshes on every sighting |
| `miss_count` | `int` default 0 | consecutive absences |
| `status` | `enum` | `active`, `expired`, `withdrawn` |
| `expired_at` | `timestamptz` | |
| `created_at`, `updated_at` | `timestamptz` | |

Key constraints:

```sql
-- The same source listing must not be stored twice.
CREATE UNIQUE INDEX uq_opportunity_source_job
  ON opportunities (source_id, source_job_id)
  WHERE source_job_id IS NOT NULL AND status <> 'withdrawn';

-- A student must always be able to reach the original posting.
ALTER TABLE opportunities
  ADD CONSTRAINT ck_opportunity_original_url CHECK (original_url IS NOT NULL);

-- We never assert eligibility the source did not state.
ALTER TABLE opportunities
  ADD CONSTRAINT ck_eligibility_attribution CHECK (
    international_students_accepted IS NULL
    OR eligibility_statement IS NOT NULL
  );

CREATE INDEX ix_opportunities_feed
  ON opportunities (status, posted_at DESC)
  WHERE status = 'active';
```

### opportunity_skills

| Column | Type | Notes |
| --- | --- | --- |
| `opportunity_id` | `uuid` FK | |
| `skill_id` | `int` FK | |
| `requirement` | `enum` | `required`, `preferred` |
| `confidence` | `numeric` | extractor confidence |
| `evidence_span` | `text` | source substring that produced it |

`evidence_span` is what makes an extraction auditable: a student can be shown the
exact words behind a claim.

### saved_opportunities

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | `uuid` FK | |
| `opportunity_id` | `uuid` FK | |
| `notes` | `text` | |
| `created_at` | `timestamptz` | |

PK `(user_id, opportunity_id)`.

### applications

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` PK | |
| `user_id`, `opportunity_id` | `uuid` FK | |
| `status` | `enum` | `interested`, `applied`, `interview`, `offer`, `rejected`, `withdrawn` |
| `applied_at` | `timestamptz` | |
| `interview_at` | `timestamptz` | |
| `resume_url` | `text` | link the student controls |
| `cover_letter` | `text` | |
| `notes` | `text` | |
| `contact_name`, `contact_email` | `text` | student-entered, optional |

SkillBridge does not submit applications. It tracks what the student did
elsewhere, which also keeps it out of scope for handling employer PII.

### alerts

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK | |
| `name` | `text` | |
| `filters` | `jsonb` | the structured query |
| `min_match_score` | `numeric` | |
| `posted_within_hours` | `int` | |
| `is_active` | `bool` | |
| `last_triggered_at` | `timestamptz` | |

`filters` is stored structured, never as free text, so it can be re-evaluated
against new rows without re-parsing.

### notifications

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK | |
| `alert_id` | `uuid` FK | |
| `opportunity_id` | `uuid` FK | |
| `kind` | `text` | `new_match`, `deadline` |
| `read_at` | `timestamptz` | |
| `created_at` | `timestamptz` | |

Unique on `(alert_id, opportunity_id, kind)` so one listing notifies once.

### embeddings

| Column | Type | Notes |
| --- | --- | --- |
| `opportunity_id` | `uuid` FK | |
| `model` | `text` | e.g. `int multilingual-e5-base` |
| `dimension` | `int` | |
| `content_hash` | `text` | skip re-embedding unchanged rows |
| `vector` | `vector(n)` | pgvector |
| `created_at` | `timestamptz` | |

Deferred to Stage 8. The table exists in the schema so adding embeddings later
needs no migration of `opportunities`.

### sync_logs

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `bigserial` PK | |
| `source_id` | `int` FK | |
| `started_at`, `finished_at` | `timestamptz` | |
| `status` | `enum` | `success`, `partial`, `failed`, `skipped` |
| `fetched_count` | `int` | |
| `new_count`, `updated_count` | `int` | |
| `expired_count`, `duplicate_count` | `int` | |
| `enrichment_failure_count` | `int` | |
| `duration_ms` | `int` | |
| `error` | `text` | |
| `mode` | `enum` | mode used, for the audit trail |

## Indexes worth having early

```sql
CREATE INDEX ix_opportunities_city      ON opportunities (city) WHERE status = 'active';
CREATE INDEX ix_opportunities_type     ON opportunities (job_type) WHERE status = 'active';
CREATE INDEX ix_opportunities_posted   ON opportunities (posted_at DESC) WHERE status = 'active';
CREATE INDEX ix_opps_requirements      ON opportunities USING gin (required_skills jsonb_path_ops);
CREATE INDEX ix_opps_language          ON opportunities USING gin (language_requirements jsonb_path_ops);
CREATE INDEX ix_alerts_user            ON alerts (user_id) WHERE is_active;
```

Full-text search over `description_original` and `title` should use
`to_tsvector('simple', ...)` at first: the Korean tokenizers are heavy and the
matching engine, not ad-hoc search, is the main entry point.

## Privacy

Collected: account email, profile fields the student chose to enter, saved items,
application notes. Nothing else.

Not collected: no scraped personal data about posters, no CV contents unless the
student uploads them, no location history, no third-party profile scraping
without explicit consent.

Retention: application rows are kept until the student deletes them. Opportunity
rows are retained after expiry for aggregate analytics, with no personal data
attached.
