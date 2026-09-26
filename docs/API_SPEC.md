# API specification

REST over JSON. Prefix `/api`. Versioned by major path segment when the student
contract changes (`/api/v1`); internal endpoints are unversioned.

## Conventions

- Timestamps are ISO-8601 UTC, `Z`-suffixed.
- All list endpoints are cursor-paginated with `limit` (default 20, max 100).
- Errors use FastAPI's shape: `{"detail": ...}`, extended with a stable `code`.
- `match_score` is always accompanied by `explanation`. A bare score is not a
  valid response.
- Every opportunity payload includes `source` and `last_seen_at`.

```json
{ "detail": "Profile not found", "code": "profile_not_found" }
```

## Profile

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/profile` | Current profile |
| `PUT` | `/api/profile` | Create or replace profile |
| `PATCH` | `/api/profile` | Partial update |
| `GET` | `/api/profile/skills` | Profile skills with proficiency |
| `PUT` | `/api/profile/skills` | Replace skill list |
| `DELETE` | `/api/profile` | Delete account and stored data |

`PUT /api/profile` accepts `work_eligibility_note` as free text only. There is no
endpoint that infers it.

## Opportunities

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/opportunities` | Filtered, paginated feed |
| `GET` | `/api/opportunities/{id}` | Full detail |
| `GET` | `/api/opportunities/{id}/matches` | Score and explanation |
| `POST` | `/api/opportunities/{id}/corrections` | Student corrects an extraction |
| `GET` | `/api/opportunities/{id}/sources` | All sources for a duplicate group |

`GET /api/opportunities` query parameters:

| Parameter | Example | Notes |
| --- | --- | --- |
| `q` | `python intern` | Keyword, Korean or English |
| `city` | `Busan` | |
| `radius_km` | `15` | Requires `lat`/`lng` or a geocoded city |
| `job_type` | `internship` | Repeatable |
| `category` | `software` | Repeatable |
| `skills` | `Python,SQL` | Resolved through aliases |
| `min_match` | `0.7` | Requires a profile |
| `topik_min` | `3` | |
| `international_only` | `true` | Only where the source stated acceptance |
| `salary_min` | `12000` | |
| `work_type` | `onsite` | |
| `posted_within_hours` | `24` | |
| `has_deadline` | `true` | |
| `source` | `example_university_career` | |
| `include_expired` | `false` | Default false |
| `sort` | `match` \| `recent` \| `deadline` | |

```json
GET /api/opportunities?city=Busan&job_type=internship&skills=Python&min_match=0.6&limit=20
```

Response:

```json
{
  "items": [
    {
      "id": "…",
      "title": "AI Research Intern",
      "organization": "ABC AI Lab",
      "city": "Busan",
      "job_type": "internship",
      "original_url": "https://…",
      "source": { "name": "…", "display_name": "…", "mode": "official_feed" },
      "last_seen_at": "2026-09-26T08:00:00Z",
      "posted_at": "2026-09-26T06:00:00Z",
      "deadline": "2026-10-10T00:00:00Z",
      "original_language": "ko",
      "match": {
        "score": 0.92,
        "label": "SkillBridge match: 92%",
        "explanation": { "factors": [], "unknown_factors": [], "caveats": [] }
      },
      "eligibility": {
        "international_students_accepted": null,
        "statement": null,
        "display": "International-student eligibility: not specified by the source."
      }
    }
  ],
  "next_cursor": "…",
  "hidden_by_filters": { "count": 12, "reasons": { "expired": 4, "city": 8 } }
}
```

`hidden_by_filters` is deliberate. Silent truncation reads as "there is nothing
else", which is a different and wrong claim.

## Recommendations

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/recommendations` | Ranked personalized feed |
| `GET` | `/api/recommendations/explain/{opportunity_id}` | Factor detail only |
| `POST` | `/api/recommendations/refresh` | Recompute after a profile change |

Query: `limit`, `min_score`, `job_type`, `include_explain`. Requires a profile;
otherwise `400 profile_required`.

## Search

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/search` | Structured filter search |
| `POST` | `/api/search/natural` | Natural language to structured filters |

The natural-language endpoint returns the structured interpretation **alongside**
the results, so a student can see and correct what was understood:

```json
POST /api/search/natural
{ "query": "AI internships in Busan for an international student with Python" }

{
  "interpreted_filters": {
    "job_type": ["internship"],
    "category": ["research", "software"],
    "city": "Busan",
    "skills": ["Python"],
    "international_only": true,
    "unparsed": []
  },
  "results": { "…": "…" },
  "confidence": 0.78,
  "note": "Filters were inferred from your sentence. Edit them before relying on the results."
}
```

`unparsed` must be populated when part of the query was not understood. Silently
ignoring the unparsed remainder would return confidently wrong results.

## Saved

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/saved` | Saved list |
| `POST` | `/api/opportunities/{id}/save` | Save |
| `DELETE` | `/api/opportunities/{id}/save` | Remove |
| `PATCH` | `/api/saved/{id}` | Notes |

## Applications

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/applications` | Board grouped by status |
| `POST` | `/api/applications` | Create |
| `PUT` | `/api/applications/{id}` | Update status, dates, notes |
| `DELETE` | `/api/applications/{id}` | Remove |

Status transitions are validated: `interested → applied → interview → offer |
rejected`. A `GET /api/applications/board` variant returns column-keyed groups for
the Kanban view.

## Alerts

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/alerts` | List |
| `POST` | `/api/alerts` | Create from structured filters |
| `PATCH` | `/api/alerts/{id}` | Update |
| `DELETE` | `/api/alerts/{id}` | Disable |
| `GET` | `/api/notifications` | Unread |
| `POST` | `/api/notifications/{id}/read` | Mark read |

## Sources and sync

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/sources` | Registry with mode and health |
| `GET` | `/api/sources/{name}/link` | Scoped `link_only` search URL |
| `GET` | `/api/sync/status` | Per-source last sync and counts |

`GET /api/sources` returns `mode` and `evidence` for every source. The student can
always see where data came from and how it was obtained. `GET /api/sync/status`
is authenticated as admin.

## Corrections

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/opportunities/{id}/corrections` | Fix an extracted field |

```json
{
  "field": "required_skills",
  "action": "add",
  "value": "Docker",
  "reason": "The posting says experience with Docker is required."
}
```

Stored as a human correction, which is both a product feature and the labelled
data that evaluation needs. Corrections do not silently rewrite the source of
truth; they are recorded as student-asserted overrides.

## Health

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness, version, DB reachability |
| `GET` | `/api/health/ready` | Readiness, including DB and worker |

`/api/health` already exists in the current build and stays compatible.

## Not in the MVP

Authentication beyond a single local user, admin write endpoints, notification
delivery over email or push, CV parsing, and any endpoint that would let a
third party submit an application on a student's behalf.
