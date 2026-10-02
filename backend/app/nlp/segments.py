"""Line segmentation and requirement classification.

The most valuable and most easily botched signal in a Korean listing is whether
a requirement is mandatory or preferred. ``우대`` means *preferred*, so reading
it as required inflates the match score and tells a student they are
unqualified for something they were merely encouraged to apply to.

Three further distinctions matter for scoring:

- ``담당 업무`` (duties) are not requirements. "React 개발 업무" describes work
  the intern will do, not a skill they must already have.
- A clause with no requirement marker at all is ``unstated``. The listing
  mentions a skill but does not say whether it is required. That is reported as
  its own class rather than guessed into required, because guessing here is
  exactly how a matching system starts lying.
- A bare section header sets the mode for the clauses beneath it, until the
  next header appears.

Lines are split into clauses before classification. Listings routinely mix the
two in a single line, as in::

    자격요건: 컴퓨터공학 전공자, 경력 3년 이상, TOPIK 4급 우대자

Classifying that line as a whole would call the whole thing required and lose
the ``우대``. Clause-level classification keeps the distinction.
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.nlp.clean import split_lines

REQUIRED = "required"
PREFERRED = "preferred"
DUTY = "duty"
UNSTATED = "unstated"

# Section headers, checked before inline markers. Longest marker first so that
# "자격요건" is not consumed by a shorter overlapping marker.
HEADERS = (
    (
        REQUIRED,
        (
            "자격요건",
            "자격 요건",
            "지원 자격",
            "지원자격",
            "요구사항",
            "필수요건",
            "필요한 역량",
            "requirements",
            "required",
        ),
    ),
    (PREFERRED, ("우대사항", "우대 조건", "우대조건", "preferred", "nice to have")),
    (
        DUTY,
        (
            "담당 업무",
            "주요 업무",
            "업무 내용",
            "주요 역할",
            "하는 일",
            "job duties",
            "responsibilities",
        ),
    ),
)

# Inline markers, checked per clause.
#
# ``가능자`` is deliberately absent from the required list. In Korean it is a
# noun suffix meaning "someone who can", as in "영어 가능자" (those who can do
# English), not a requirement marker. Treating it as required overrode the
# section header and reported a preferred language as mandatory.
INLINE_MARKERS = (
    (PREFERRED, ("우대", "있으면", "우선", "선호", "우수", "더욱 좋")),
    (
        REQUIRED,
        (
            "필수",
            "요건",
            "자격",
            "요구",
            "필요",
            "제한이 있다",
            "must have",
            "required",
        ),
    ),
)

# A header line is a label with nothing else on it.
_HEADER_ONLY = re.compile(
    r"^(자격\s?요건|지원\s?자격|요구사항|필수요건|필요한\s?역량|우대사항|우대\s?조건|"
    r"담당\s?업무|주요\s?업무|업무\s?내용|주요\s?역할|하는\s?일|"
    r"requirements?|required|preferred|nice\s+to\s+have|job\s+duties|responsibilities|"
    r"자격|필수|우대)\s*[:：]?\s*$"
)

# Clause separators. Korean listings separate requirements with these.
_CLAUSE_SPLIT = re.compile(r"[,;/·•\|\n]+")

# A header glued to the front of its first clause, e.g. "자격요건: 컴퓨터공학
# 전공자". Stripped so the evidence a student sees is the requirement itself
# rather than the section label.
_LEADING_HEADER = re.compile(
    r"^(?:자격\s?요건|지원\s?자격|요구사항|필수요건|필요한\s?역량|우대사항|우대\s?조건|"
    r"담당\s?업무|주요\s?업무|업무\s?내용|주요\s?역할|하는\s?일|"
    r"requirements?|required|preferred|nice\s+to\s+have|job\s+duties|responsibilities)"
    r"\s*[:：]\s*",
    re.IGNORECASE,
)


class Segment:
    """One classified clause of a listing."""

    __slots__ = ("text", "kind", "line_index", "is_header", "explicit")

    def __init__(
        self,
        text: str,
        kind: str,
        line_index: int,
        is_header: bool = False,
        explicit: bool = False,
    ):
        self.text = text
        self.kind = kind
        self.line_index = line_index
        self.is_header = is_header
        self.explicit = explicit

    @property
    def is_requirement(self) -> bool:
        return self.kind in (REQUIRED, PREFERRED)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "kind": self.kind,
            "line_index": self.line_index,
            "is_header": self.is_header,
            "explicit": self.explicit,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Segment(kind={0!r}, text={1!r})".format(self.kind, self.text)


def _header_kind(line: str) -> Optional[str]:
    """Return the requirement class a header line introduces, if any."""

    lowered = line.lower()
    best_kind: Optional[str] = None
    best_length = 0
    for kind, markers in HEADERS:
        for marker in markers:
            if marker in lowered and len(marker) > best_length:
                best_kind = kind
                best_length = len(marker)
    return best_kind


def _is_header_only(line: str) -> bool:
    return bool(_HEADER_ONLY.match(line.strip()))


def _inline_kind(text: str) -> Optional[str]:
    """Classify a clause by its inline markers.

    ``우대`` is checked first on purpose. A clause such as
    "TOPIK 4급 우대자" contains a number, a language level, and a preferred
    marker, and the posting is stating a preference.
    """

    lowered = text.lower()
    best_kind: Optional[str] = None
    best_length = 0
    for kind, markers in INLINE_MARKERS:
        for marker in markers:
            if marker in lowered and len(marker) > best_length:
                best_kind = kind
                best_length = len(marker)
    return best_kind


def _split_clauses(line: str) -> List[str]:
    parts = [part.strip() for part in _CLAUSE_SPLIT.split(line)]
    return [part for part in parts if part]


def segment_text(description: str) -> List[Segment]:
    """Split a description into classified clauses.

    Header segments are included with ``is_header`` set, so a caller can show
    the student the original structure rather than a flattened result.
    """

    lines = split_lines(description)
    if not lines:
        return []

    segments: List[Segment] = []
    current_kind: str = UNSTATED

    for line_index, line in enumerate(lines):
        header_kind = _header_kind(line)

        if header_kind is not None and _is_header_only(line):
            current_kind = header_kind
            segments.append(Segment(line, header_kind, line_index, is_header=True))
            continue

        clauses = _split_clauses(line)
        if header_kind is not None and clauses:
            # The header governs its section. Set it before stripping the label
            # off the first clause, so the clause that carries the label still
            # inherits the header's meaning after the label is gone.
            current_kind = header_kind
            clauses[0] = _LEADING_HEADER.sub("", clauses[0]).strip()
            clauses = [clause for clause in clauses if clause]

        for clause in clauses:

            inline = _inline_kind(clause)
            if inline is not None:
                kind = inline
                explicit = True
            else:
                kind = current_kind
                explicit = header_kind is not None

            segments.append(
                Segment(clause, kind, line_index, is_header=False, explicit=explicit)
            )

    return segments


def segments_of_kind(segments: List[Segment], kind: str) -> List[Segment]:
    return [segment for segment in segments if segment.kind == kind and not segment.is_header]
