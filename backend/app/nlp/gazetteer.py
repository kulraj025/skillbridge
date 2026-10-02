"""Skill aliases across Korean and English.

A Korean listing writes the same skill as ``파이썬``, ``Python``, or ``Py``.
Matching only happens after alias resolution, so all three collapse to one
canonical skill. This is the highest-leverage table in the pipeline for Korean
listings, and the cheapest place to add coverage.

Two rules govern the alias lists:

1. Ambiguous short English words are never bare aliases. ``go``, ``r``, and
   ``c`` would match ordinary prose ("go", "R", "C++"). They use explicit forms
   such as ``go언어`` or ``c언어`` instead, so a C++ posting is not read as
   listing the C skill.
2. Distinct tools stay distinct. ``git`` and ``github`` are separate entries.
   Matching is boundary-aware, so ``git`` will not match ``github``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.matcher import find_term

# canonical skill -> aliases, English and Korean
SKILL_ALIASES: Dict[str, Tuple[str, ...]] = {
    # --- languages -------------------------------------------------------
    "python": ("python", "py", "파이썬", "파이선"),
    "java": ("java", "자바"),
    "javascript": ("javascript", "js", "자바스크립트"),
    "typescript": ("typescript", "ts", "타입스크립트"),
    "c++": ("c++", "cpp", "cplusplus", "시플러스플러스"),
    "c#": ("c#", "csharp", "시샵"),
    "c": ("c언어", "c language", "ansi c"),
    "sql": ("sql", "에스큐엘", "구조화질의언어"),
    "r": ("r언어", "r language"),
    "go": ("go언어", "golang", "고랭"),
    "rust": ("rust", "러스트"),
    "php": ("php", "피에이치피"),
    "kotlin": ("kotlin", "코틀린"),
    "swift": ("swift", "스위프트"),
    "scala": ("scala", "스칼라"),
    "dart": ("dart", "다트"),
    # --- frontend --------------------------------------------------------
    "react": ("react", "reactjs", "리액트", "리엑트"),
    "vue": ("vue", "vuejs", "뷰", "브이유"),
    "angular": ("angular", "앵귤러"),
    "svelte": ("svelte", "스벨트"),
    "html": ("html", "에이치티엠엘"),
    "css": ("css", "시에스에스"),
    "next.js": ("next.js", "nextjs", "넥스트제이"),
    "tailwind css": ("tailwind", "테일윈드"),
    "figma": ("figma", "피그마"),
    # --- backend ---------------------------------------------------------
    "node.js": ("node.js", "nodejs", "노드", "노드제이"),
    "django": ("django", "장고"),
    "flask": ("flask", "플라스크"),
    "fastapi": ("fastapi", "파스트에이피아이"),
    "spring": ("spring", "spring boot", "스프링", "스프링부트"),
    "express": ("express", "익스프레스"),
    "rest api": ("rest api", "restful", "restful api", "레스트 api"),
    "graphql": ("graphql", "그래프ql"),
    # --- data and ml -----------------------------------------------------
    "artificial intelligence": ("artificial intelligence", "ai", "인공지능"),
    "machine learning": ("machine learning", "ml", "기계학습", "머신러닝"),
    "deep learning": ("deep learning", "딥러닝", "심층학습"),
    "data analysis": ("data analysis", "데이터 분석", "데이터분석"),
    "data science": ("data science", "데이터 사이언스", "데이터과학"),
    "natural language processing": (
        "natural language processing",
        "nlp",
        "자연어처리",
        "자연 언어 처리",
    ),
    "computer vision": ("computer vision", "컴퓨터 비전", "컴퓨터비전"),
    "large language model": (
        "large language model",
        "llm",
        "대규모 언어 모델",
        "대규모언어모델",
    ),
    "statistics": ("statistics", "통계", "통계학", "통계분석"),
    "pandas": ("pandas", "판다스"),
    "numpy": ("numpy", "넘파이"),
    "pytorch": ("pytorch", "파이토치"),
    "tensorflow": ("tensorflow", "텐서플로", "텐서플로우"),
    "spark": ("spark", "스파크"),
    "hadoop": ("hadoop", "하둡"),
    "excel": ("excel", "엑셀"),
    "powerpoint": ("powerpoint", "ppt", "파워포인트"),
    # --- infrastructure --------------------------------------------------
    "docker": ("docker", "도커"),
    "kubernetes": ("kubernetes", "k8s", "쿠버네티스"),
    "git": ("git", "깃", "버전 관리", "버전관리"),
    "github": ("github", "깃허브"),
    "aws": ("aws", "아마존 웹 서비스", "클라우드 컴퓨팅"),
    "linux": ("linux", "리눅스"),
    "ci/cd": ("ci/cd", "cicd", "지속적 통합", "持续集成"),
    "database": ("database", "db", "데이터베이스"),
    # --- soft skills -----------------------------------------------------
    "communication": ("communication", "의사소통", "커뮤니케이션", "소통"),
    "teamwork": ("teamwork", "팀워크", "협업", "팀워크 능력"),
    "leadership": ("leadership", "리더십", "리딩"),
    "project management": ("project management", "프로젝트 관리", "프로젝트운영"),
    "presentation": ("presentation", "발표", "프레젠테이션"),
    "problem solving": ("problem solving", "문제 해결", "문제해결"),
}


def canonical_skills() -> List[str]:
    """All canonical skill names, sorted for stable output."""

    return sorted(SKILL_ALIASES)


def aliases_for(skill: str) -> Tuple[str, ...]:
    """Aliases for one canonical skill, or an empty tuple if unknown."""

    return SKILL_ALIASES.get(str(skill or "").strip().lower(), ())


def resolve(term: str) -> Optional[str]:
    """Map any alias to its canonical skill name.

    Longest alias wins, so ``go언어`` is not shadowed by a shorter alias that
    happens to be a prefix.
    """

    key = " ".join(str(term or "").lower().split())
    if not key:
        return None

    best: Optional[str] = None
    best_length = 0
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            if key == alias and len(alias) > best_length:
                best = canonical
                best_length = len(alias)
    return best


def find_skills(text: str, restrict_to: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    """Return every known skill present in ``text``, with its evidence phrase.

    The ``evidence`` field is the exact substring that produced the hit, so a
    student disputing an extracted skill can see the words behind the claim.
    """

    source = text or ""
    if not source.strip():
        return []

    allowed = None
    if restrict_to is not None:
        allowed = {str(name).strip().lower() for name in restrict_to}

    hits: List[Dict[str, Any]] = []
    seen: Dict[str, int] = {}

    for canonical, aliases in SKILL_ALIASES.items():
        if allowed is not None and canonical not in allowed:
            continue
        for alias in aliases:
            found = find_term(source, alias)
            if not found:
                continue
            position = seen.get(canonical)
            if position is None or found["start"] < position:
                seen[canonical] = found["start"]
                hits.append(
                    {
                        "name": canonical,
                        "alias": alias,
                        "evidence": found["phrase"],
                        "start": found["start"],
                    }
                )
            break

    hits.sort(key=lambda hit: (hit["start"], hit["name"]))
    return hits


def find_skill_names(text: str) -> List[str]:
    """Canonical skill names present in ``text``."""

    return [hit["name"] for hit in find_skills(text)]
