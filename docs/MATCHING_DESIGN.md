# Matching engine design

The existing `backend/app/matcher.py` is the foundation and is kept, not
rewritten. It already does the two things that matter most: word-boundary skill
matching and a returned explanation. This document specifies what to add.

## 1. What exists today

```python
matched_required, missing_required, matched_preferred, evidence, explanation, score
```

Current scoring:

```text
score = 0.65 × required_ratio + 0.25 × preferred_ratio + min(0.10, 0.03 × evidence_count)
```

Known limitation: with no requirements, the ratio defaults to `0.5`, which
inflates scores for vague listings. Fixing that is Step 1 below.

## 2. Three-stage design

```text
Profile + Opportunity
   ↓
Stage 1  Hard eligibility filters      → excluded, with a stated reason
   ↓
Stage 2  Rule-based weighted scoring   → score + per-factor detail
   ↓
Stage 3  Semantic recall (optional)    → related-skill candidates
   ↓
Explanation assembled from Stage 2 detail
```

Stage 3 is additive. It can widen recall by finding related skills; it must never
overwrite Stage 2's score, so removing it degrades quality rather than breaking
correctness.

## 3. Stage 1 — hard filters

Cheap exclusions first, so obviously unsuitable listings never reach scoring.

| Filter | Behaviour |
| --- | --- |
| `status != 'active'` | exclude expired |
| `deadline` passed | exclude |
| `city` outside radius | exclude, show distance |
| `job_type` excluded by preference | exclude |
| availability no overlap | exclude, show the conflict |

Excluded items are not silently dropped. The UI shows "12 hidden by your filters"
with the reasons, so a student can tell a filter from a bug.

**Language is not a hard filter.** A listing wanting TOPIK 4 is a strong negative
signal, not a disqualifier, and a student may still wish to see it. It scores
badly and explains itself.

## 4. Stage 2 — weighted scoring

Weights are configuration, not constants (§4), stored per-cohort so they can be
tuned without a deploy.

| Factor | Default | Detail produced |
| --- | --- | --- |
| Skill compatibility | 35% | matched / missing, with evidence spans |
| Major or field | 20% | match, partial, or unrelated |
| Location | 15% | distance, commute feasibility |
| Language requirement | 10% | required level, student's level, gap |
| Experience | 10% | required years, student's experience |
| Availability | 5% | overlapping hours |
| Job preference | 5% | internship vs part-time intent |

```python
@dataclass(frozen=True)
class MatchWeights:
    skill: float = 0.35
    major: float = 0.20
    location: float = 0.15
    language: float = 0.10
    experience: float = 0.10
    availability: float = 0.05
    preference: float = 0.05

    def validate(self) -> None:
        total = sum(self.__dict__.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")
```

Each factor returns a score in `[0, 1]` **and** the detail that produced it. A
factor that cannot be evaluated returns `None`, and its weight is redistributed
across the evaluable factors. An unevaluable factor must not silently score zero:
"we could not tell" and "you fail this" are different claims, and conflating
them is how a matching system starts lying.

### Skill sub-score

```text
required_matched / required_total        → 70% of the factor
preferred_matched / preferred_total      → 20% of the factor
evidence coverage                       → 10% of the factor
```

With no requirements at all, the factor returns `None`, not `0.5`. Vague listings
therefore stop scoring as mid-fit, and the explanation says the listing states no
specific requirements.

## 5. Stage 3 — semantic recall (Stage 8, off by default)

Uses pgvector over `description_en`, matching the student's skill evidence
against the listing.

Purpose is **recall, not scoring**: find listings whose wording differs from the
gazetteer. A listing saying "데이터 분석" should surface for a data-analysis
profile even if the alias table misses it.

```python
async def semantic_candidates(conn, profile_embedding, k=50) -> list[Opportunity]:
    rows = await conn.fetch(
        """
        SELECT opportunity_id, 1 - (vector <=> $1) AS similarity
        FROM embeddings
        WHERE model = $2
        ORDER BY vector <=> $1
        LIMIT $3
        """,
        profile_embedding, EMBEDDING_MODEL, k,
    )
    return [r["opportunity_id"] for r in rows if r["similarity"] >= 0.72]
```

The threshold is a starting guess and **must be validated against a labeled set**
before it influences anything user-facing. Below the threshold, embeddings are
noise, and a confident-looking wrong match is worse than a miss.

## 6. Explainability contract

This is a product requirement (§5), not a nice-to-have. Every match returns
enough structure to render this:

```json
{
  "score": 0.87,
  "label": "SkillBridge match: 87%",
  "factors": [
    { "factor": "skill", "weight": 0.35, "score": 0.86,
      "matched": ["Python", "SQL"],
      "missing": ["Docker"],
      "evidence": ["Built a Python data pipeline with SQL"] },
    { "factor": "language", "weight": 0.10, "score": 0.5,
      "detail": "TOPIK 3 stated; posting prefers TOPIK 4" }
  ],
  "unknown_factors": ["experience"],
  "caveats": [
    "This is an estimate based on the information in the posting, not a hiring decision.",
    "International applicants: stated as accepted by the employer.",
    "Visa and work authorization are not assessed by SkillBridge."
  ]
}
```

Required properties:

- **Every score is traceable to factors.** No unexplained number reaches the UI.
- **`unknown_factors` is explicit.** A missing factor is visible, not imputed.
- **`caveats` are always present.** They are not dismissible and not conditional.
- **Factors are user-correctable.** A student disputing an extracted skill
  corrects the record, and the correction is stored.

## 7. Language and eligibility, precisely

Required: never assert legal work eligibility.

```text
FOREGINER_OK patterns:  외국인 가능, 외국인 환영, 외국인，扎이 visa
NOT acceptable:         "You are legally allowed to work in Korea."
```

| Source text | Rendered as |
| --- | --- |
| "외국인 가능" | "International applicants: stated as accepted by the employer." |
| "외국인visa 필요" | "Employer states a visa is required. Check your authorization before applying." |
| nothing | "International-student eligibility: not specified by the source." |

TOPIK comparison is a **gap**, never a gate:

```text
required 4, student 3 → "Korean: TOPIK 4 preferred, your profile states TOPIK 3."
required 4, student 2 → stronger warning, still listed
required 4, student unknown → "Your Korean level is not set. Add it for a better match."
```

## 8. Measuring quality

Without measurement, "hybrid matching" is a claim rather than a result.

Build a labeled set first (existing roadmap item): 100+ real listings, hand-labeled
for required skills, preferred skills, and language requirements. Then report:

| Metric | Why |
| --- | --- |
| Extraction precision / recall per field | is the parser trustworthy |
| Required vs preferred accuracy | the easiest rule to get wrong |
| Top-10 recall for a known profile | does the feed surface the right things |
| Explanation agreement with labels | is the reasoning honest |

Publish these numbers, including the bad ones. A matching system whose quality is
unmeasured cannot be improved, and cannot be defended.

## 9. Implementation order

1. Extract `MatchWeights`, add the `validate` sum-to-one check.
2. Return `None` for unevaluable factors; redistribute weight.
3. Return per-factor detail from scoring.
4. Add the explanation payload and caveats.
5. Korean extraction with the `우대`/`필수` distinction.
6. Alias gazetteer.
7. Labeled evaluation set, then the metrics above.
8. pgvector semantic recall, behind a flag, only after 7.
