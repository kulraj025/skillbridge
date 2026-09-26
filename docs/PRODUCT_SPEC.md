# SkillBridge product specification

Rewritten for the opportunity-aggregator scope. Supersedes the earlier
evidence-only three-role spec, which had no ingestion layer and could not answer
"where did this opportunity come from".

## 1. Product statement

SkillBridge continuously collects legally accessible Korean opportunity
listings, normalizes them into one schema, and matches them against a student
profile — showing the score, the factors behind it, and the original posting.

The hard part is reliable, permitted, explainable ingestion. Matching is
downstream of it.

## 2. Problem statement

Students in Korea search for opportunities across Alba, Albamoon, Karrot,
university career portals, lab pages, and company sites. Listings are scattered,
often written only in Korean, and must be manually filtered against a student's
actual skills, major, language level, location, availability, and goals.

The work is repetitive and the requirements are hard to verify. A student
cannot tell, from a Korean listing, whether they meet a requirement, which
requirement is preferred rather than mandatory, or whether they may legally work
in Korea.

## 3. Product goals

### Student goals

- See relevant opportunities without searching five platforms manually
- Understand each listing's requirements in their own language
- Know why a listing matched and what is missing
- Know what the source actually said about international-student eligibility
- Reach the original posting in one click
- Track saves, applications, and deadlines

### Institutional goals (deferred)

Career offices and employers may later need visibility into cohort skill trends
and structured opportunity publishing. This is not in the MVP.

## 4. Non-goals

- Bypassing CAPTCHAs, authentication, paywalls, rate limits, or robots policies
- Scraping a source without documented permission
- Inferring visa or work eligibility
- Submitting applications on a student's behalf
- Presenting SkillBridge as the employer
- Promising a job or a placement outcome
- Automatic rejection of students or candidates
- Advice on Korean immigration or labour law

## 5. Core user flow

```text
Student creates profile (skills, major, TOPIK, locations, availability)
  ↓
SkillBridge syncs sources on each source's own interval
  ↓
Normalization + Korean extraction + dedupe + expiry
  ↓
Weighted explainable matching against the profile
  ↓
Personalized feed: score, factors, gaps, eligibility notice, source link
  ↓
Student saves, applies on the original site, and tracks status
  ↓
Alerts notify on new matches
```

## 6. Matching requirements

Three stages, documented in [`MATCHING_DESIGN.md`](MATCHING_DESIGN.md):

1. Hard eligibility filters, with excluded items disclosed rather than dropped
2. Rule-based weighted scoring producing per-factor detail
3. Optional semantic recall for recall only, added after evaluation

Non-negotiable properties:

- Every score decomposes into factors a student can inspect
- Unevaluable factors are reported as unknown, never imputed as zero
- A bare score is not a valid API response
- The score is labelled as an estimate, not a probability of getting the job

## 7. Explainability requirements

```text
SkillBridge match: 87%

Why this opportunity?
  ✓ Your Python skill matches a required skill
  ✓ Your AI/Computer Science major is relevant
  ✓ Location is within your preferred area
  ⚠ Korean: posting prefers TOPIK 4, your profile states TOPIK 3

Not assessed: experience

This is an estimate based on the information in the posting, not a hiring
decision. Visa and work authorization are not assessed by SkillBridge.

[Source: Example University Career Center · synchronized 12 min ago]
[View original posting]
```

The student must be able to correct an extracted field, and corrections are
recorded as student-asserted overrides.

## 8. Trust and eligibility requirements

A product requirement, not an implementation detail.

| Source states | Rendered as |
| --- | --- |
| `외국인 가능` | "International applicants: stated as accepted by the employer." |
| `외국인 visa 필요` | "Employer states a visa is required. Check your authorization before applying." |
| Nothing | "International-student eligibility: not specified by the source." |

Never rendered: "You are legally allowed to work in Korea."

Every opportunity must show its source, its real synchronization age, and a link
to the original posting. Aggregated data must not be presented as if it came
from a single official feed.

## 9. Source access policy

Full policy in [`SOURCE_ADAPTERS.md`](SOURCE_ADAPTERS.md). Each source declares
one access mode — `official_api`, `official_feed`, `permitted_endpoint`,
`partner_feed`, `link_only`, or `blocked` — with the evidence recorded.

`link_only` is a first-class outcome, not a failure. It yields a search link
scoped to the student's profile, which still replaces several manual searches.

## 10. Success measures

MVP:

- Source sync success rate and freshness distribution
- Duplicate rate across sources
- Extraction precision and recall on a labeled set
- Required vs preferred classification accuracy
- Top-10 recommendation recall for known profiles
- Student-rated usefulness of explanations
- Time to find a relevant opportunity, versus manual search
- Save rate and alert usefulness

No placement claims. The pilot measures discovery efficiency, not hiring
outcomes.

## 11. Privacy requirements

Collected: account email, profile fields the student chose to enter, saved
items, application notes and status.

Not collected: personal data about job posters or employers, CV contents unless
the student uploads them, location history, third-party profile data without
explicit consent.

Students can export and delete their data. Opportunity rows are retained after
expiry for aggregate analytics with no personal data attached.

## 12. Roles

`student` and `admin` only in the MVP. Career-office and recruiter surfaces are
deferred, and the enum stays extensible so adding them needs no migration.

No role receives automatic hiring authority, in this release or any future one.
