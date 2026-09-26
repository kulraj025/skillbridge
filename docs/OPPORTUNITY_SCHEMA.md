# Opportunity schema

The normalized shape every source must produce, plus the Korean processing
pipeline that fills it.

## 1. `RawOpportunity`

What an adapter returns straight from a source, before interpretation. Keeps the
source-native values intact so nothing is lost during normalization.

```python
@dataclass
class RawOpportunity:
    source_name: str
    source_job_id: str | None
    title: str
    organization: str | None
    description: str            # verbatim, never modified
    original_url: str           # required
    location_text: str | None
    salary_text: str | None
    working_hours_text: str | None
    posted_at: datetime | None
    deadline: datetime | None
    raw_payload: dict            # full source record, for debugging and re-normalization
```

`raw_payload` is kept so re-running a normalizer after a parser fix does not
require re-fetching. That directly serves the "reliable ingestion" goal.

## 2. `Opportunity`

The internal contract. Mirrors the `opportunities` table.

```python
@dataclass
class Opportunity:
    source_name: str
    source_job_id: str | None
    title: str
    organization: str
    original_url: str

    description_original: str
    original_language: str          # ISO-639-1
    description_en: str | None      # machine translation, always labelled

    location_text: str | None
    city: str | None
    lat: float | None
    lon: float | None

    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_unit: str | None         # hour | month | year
    salary_original_text: str | None

    job_type: str
    category: str | None
    remote_type: str                # remote | onsite | hybrid | unknown

    working_hours: dict | None      # {days, start, end, weekly}

    required_skills: list[ExtractedSkill]
    preferred_skills: list[ExtractedSkill]
    language_requirements: list[LanguageRequirement]
    education_requirements: dict | None
    experience_requirements: dict | None

    international_students_accepted: bool | None   # None = not stated
    eligibility_statement: str | None             # verbatim
    eligibility_source: str | None                 # who said it

    posted_at: datetime | None
    deadline: datetime | None

    extraction_version: str
```

```python
@dataclass
class ExtractedSkill:
    skill_id: int
    name: str
    requirement: str        # required | preferred
    confidence: float
    evidence_span: str      # the exact source words

@dataclass
class LanguageRequirement:
    language: str
    min_level: str | None   # TOPIK 1-6, CEFR A1-C2, or free text
    explicit: bool          # False = inferred from surrounding text
```

`explicit=False` matters. An inferred language requirement must be rendered
differently from one the employer wrote, or the student will treat a guess as a
stated condition.

## 3. Korean processing pipeline

```text
description_original (ko)
   ↓  language detection              → original_language
   ↓  normalise text (NBSP, spacing)  → clean text
   ↓  translate (optional, cached)    → description_en
   ↓  requirement extraction          → required_skills / preferred_skills
   ↓  skill extraction (ko + en)      → skills resolved via aliases
   ↓  language requirement extraction → language_requirements
   ↓  experience extraction           → experience_requirements
   ↓  location extraction             → location_text → city
   ↓  salary extraction               → salary_original_text → min/max/unit
   ↓  working-hours extraction        → working_hours
   ↓  deadline extraction             → deadline
   ↓  eligibility extraction          → eligibility_statement (verbatim only)
   ↓
Opportunity
```

**Original text is never overwritten.** Translation is additive and labelled.
Every extracted value carries `confidence` and `evidence_span`.

### Stages 1–3 are deterministic

- **Language detection.** Short-description heuristics plus a stopword probe for
  Hangul ratio. No model needed; `langdetect` is sufficient and is fast.
- **Normalisation.** Korean listings are full of NBSP (`\u00a0`), inconsistent
  spacing, and full-width characters. This stage alone measurably improves every
  later stage.
- **Translation.** `deep-translator` or a hosted provider behind an interface, so
  the provider is swappable (§18). Cached by `content_hash` to avoid repeat cost.
  Cost control matters: without caching, a re-sync of an unchanged listing
  re-pays for translation.

### Stages 4–10 are rule-based first

Korean job ads follow strong conventions, so regex plus a gazetteer beats a model
on precision and stays inspectable:

| Signal | Example | Extraction |
| --- | --- | --- |
| `우대`, `면접 우대` | "컴퓨터공학 전공자 **우대**" | preferred, not required |
| `필수`, `요구사항` | "**필수** 요건" | section header |
| `경력` | "3년 이상 경력" | experience, 3 years |
| `학력` | "4년제 졸업" | education |
| ` TOPIK`, `한국어` | "TOPIK 4급 이상" | language, level 4 |
| `영어` | "영어 가능자" | English required |
| `외국인` | "외국인 가능" | eligibility, stated |
| `시급`, `만원` | "시급 12,000원" | salary, hourly 12000 |
| `주`, `시간` | "주 20시간" | hours, 20/week |
| `접수기간`, `마감` | "접수기간: 10월 10일까지" | deadline |

The required/preferred distinction is the highest-value signal and the easiest
to get wrong. `우대` means *preferred*, so treating it as required would
mis-score the opportunity. The existing `matcher.py` word-boundary logic is the
right foundation to extend for this.

### Skill aliasing is the core of Korean matching

A Korean listing says `파이썬`, `Python`, or `Py` for the same skill. Matching
happens only after alias resolution:

```python
"python": ["python", "py", "파이썬", "파이선"]
"machine learning": ["machine learning", "ml", "기계학습", "머신러닝"]
"react": ["react", "리액트", "리엑트"]
```

A curated gazetteer plus PostgreSQL full-text is enough for the MVP. Embeddings
handle the long tail later, and only if measurement shows the gazetteer is the
bottleneck.

## 4. Extraction must degrade, not fail

If translation or extraction fails:

- the opportunity is still persisted and shown
- `extraction_version` records what ran
- the failure is counted in `sync_logs.enrichment_failure_count`
- the UI shows the original text and omits the missing derived fields

A parser bug must never cost a student a listing. This is the single most
important reliability property of the pipeline.

## 5. Validation

`validate_opportunity` returns problems rather than raising:

- missing `original_url` → reject. A row a student cannot apply from is useless.
- missing `title` → reject.
- `description_original` empty but other fields present → warn, keep.
- `salary_min > salary_max` → swap and warn.
- `deadline` in the past → set `status = 'expired'`.
- unparseable date → null plus a warning, never a crash.
- `international_students_accepted = true` with no `eligibility_statement` →
  reject, per the attribution constraint in `DATA_MODEL.md`.
