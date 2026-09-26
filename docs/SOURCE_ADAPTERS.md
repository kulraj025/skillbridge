# Source adapters and access policy

This document is the most important one in the repository. It defines how
SkillBridge is allowed to obtain opportunity data.

## 1. The governing rule

> Automated access to a source is permitted **only** when that permission is
> documented and current. Absent documentation, SkillBridge does not scrape.

This is not a limitation to work around. It is the constraint that keeps the
project deployable, the data legally usable, and the repository defensible.

Specifically, SkillBridge will **not**:

- bypass or solve CAPTCHAs
- bypass authentication, paywalls, or access controls
- circumvent rate limits
- ignore `robots.txt` or documented access policies
- impersonate a browser or a user to defeat controls
- copy protected content beyond permitted use
- collect personal data about posters or employers

## 2. Access modes

Every source declares exactly one mode. The mode determines what the adapter is
allowed to do.

| Mode | Permitted? | Adapter behaviour |
| --- | --- | --- |
| `official_api` | Yes | Call the documented API. Respect documented limits. |
| `official_feed` | Yes | Parse RSS/Atom or a documented export. |
| `permitted_endpoint` | Yes | Call an endpoint documented as public. Record the evidence. |
| `partner_feed` | Yes | Consume an agreed feed. Requires a written agreement on file. |
| `link_only` | No scraping | No fetching. Provide a deep search link and manual add. |
| `blocked` | Prohibited | No adapter. Reason recorded. CI fails if one appears. |

`link_only` is a **first-class adapter**, not a failure. Most consumer platforms
will land here. A `link_only` source is still valuable: it gives the student a
pre-filled search URL scoped to their profile, so one tap replaces several
manual searches. That is a real part of the product's value proposition.

## 3. Source registry

Access policy is data, not code, so it is reviewable and diffable.

```yaml
# backend/app/sources/registry.yaml
sources:
  - name: example_university_career
    display_name: Example University Career Center
    mode: official_feed
    category: university
    language: [en, ko]
    home_url: https://career.example.ac.kr
    feed_url: https://career.example.ac.kr/feed.rss
    rate_limit_per_minute: 10
    interval_minutes: 30
    attribution_required: true
    evidence:
      type: published_feed
      url: https://career.example.ac.kr/terms
      checked_on: 2026-09-26
      note: "RSS link published in the site's own terms page."

  - name: example_company_careers
    display_name: Example Tech Careers
    mode: permitted_endpoint
    category: company
    interval_minutes: 60
    evidence:
      type: documented_public_endpoint
      url: https://careers.example.com/public-api-docs
      checked_on: 2026-09-26

  - name: example_consumer_platform
    display_name: Example Consumer Jobs Platform
    mode: link_only
    category: aggregator
    home_url: https://jobs.example.co.kr
    search_url_template: "https://jobs.example.co.kr/search?q={query}&city={city}"
    interval_minutes: null
    evidence:
      type: no_documented_programmatic_access
      checked_on: 2026-09-26
      note: >
        No public API or feed found; automated access not documented.
        We surface a search link only.
```

`evidence` is mandatory for every non-`blocked` mode. A source without evidence
cannot be enabled.

## 4. Adapter interface

```python
# backend/app/sources/base.py
from typing import Protocol

class OpportunitySource(Protocol):
    """Every adapter implements this. Adapters never touch the database."""

    name: str
    mode: str

    def fetch_opportunities(self) -> list[RawOpportunity]: ...
    def normalize_opportunity(self, raw: RawOpportunity) -> Opportunity: ...
    def validate_opportunity(self, opportunity: Opportunity) -> list[str]:
        """Return a list of problems. Empty means valid."""
```

Responsibilities are split on purpose:

- `fetch_opportunities` — network. Only permitted for non-`link_only` modes.
- `normalize_opportunity` — source shape → internal shape. Pure, so it is unit
  testable with recorded fixtures and needs no network.
- `validate_opportunity` — returns problems rather than raising, so a bad record
  is quarantined and counted instead of crashing a whole sync.

### The `link_only` adapter

```python
class LinkOnlySource:
    """No fetching. Generates a scoped search link for the student."""

    mode = "link_only"

    def fetch_opportunities(self) -> list[RawOpportunity]:
        return []  # deliberately empty

    def search_link(self, profile: StudentProfile) -> str:
        query = " ".join(profile.top_skills[:3])
        return self.registry["search_url_template"].format(
            query=quote(query), city=quote(profile.preferred_locations[0])
        )
```

## 5. Adding a source

1. Create `backend/app/sources/<name>/` with `adapter.py` and `fixtures/`.
2. Record the source in `registry.yaml` with `mode` and `evidence`.
3. Add fixtures captured from permitted access. Normalization tests run offline
   against fixtures, so tests never touch the network.
4. Run `pytest tests/sources/<name>`.
5. If `mode: link_only`, skip the adapter and register only the search template.

A CI check fails the build if an adapter exists for a source whose registry
`mode` is `blocked`, and if a non-`link_only` source has no `evidence` block.

## 6. Honesty requirements

- The admin dashboard shows each source's real mode and last sync time.
- The student UI labels every opportunity with its source and sync age.
- If a source is rate-limited or degraded, say so. Do not silently drop it.
- Never present aggregated data as if it came from a single official feed.
- Recordings that replay third-party content must be handled under the terms
  that permit them; where unclear, the source stays `link_only`.

## 7. Open question blocking implementation

**Which sources can actually be enabled, and at which mode?**

This cannot be answered from inside the codebase. It needs a deliberate check of
each target source's current terms, `robots.txt`, and any partner or affiliate
program, with the finding recorded in `registry.yaml`.

Until that is done, the honest MVP is: framework plus `link_only` sources plus
whatever documented feeds are confirmed. A `link_only`-only MVP still delivers
the aggregation and matching value, and it is truthful. Inventing scrapers to
fill the registry would deliver a demo that cannot legally run, which §26
explicitly rules out.
