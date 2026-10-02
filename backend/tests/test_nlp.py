"""Tests for the Korean extraction pipeline.

The cases here are chosen for the failure modes that matter rather than for
coverage: required-versus-preferred confusion, the eligibility boundary, the
c++/c false positive, and deadline year inference.
"""

import unittest
from datetime import date, datetime

from app.nlp.clean import normalize_text
from app.nlp.detect import detect_language, hangul_ratio
from app.nlp.eligibility import (
    DISPLAY_ACCEPTED,
    DISPLAY_UNSPECIFIED,
    DISPLAY_VISA,
    extract_eligibility,
    extract_language_requirements,
)
from app.nlp.fields import (
    extract_deadline,
    extract_education,
    extract_experience,
    extract_salary,
    extract_working_hours,
    parse_korean_number,
)
from app.nlp.gazetteer import find_skills, resolve
from app.nlp.pipeline import extract_listing
from app.nlp.segments import DUTY, PREFERRED, REQUIRED, UNSTATED, segment_text

SOFTWARE_INTERNSHIP = """
[채용공고] AI 연구 보조 인턴

고용형태: 인턴
근무지역: 부산광역시
급여: 시급 15,000원

지원자격
- 컴퓨터공학 전공자
- Python 개발 경험 1년 이상
- 머신러닝 기초 지식

우대사항
- 딥러닝 경험자
- TOPIK 4급 우대자
- 영어 가능자

담당 업무
- 데이터 분석 및 모델 학습 보조

기타
- 외국인 가능
- 접수기간: 10월 10일까지
"""

CAFE_PART_TIME = """
카페 홀 직원 모집

시급 12,000원~14,000원
주 20시간 근무, 평일 오후 2시~6시
경력무관
4년제及以上 대 학생
외국인 비자 필요
"""


class CleanTests(unittest.TestCase):
    def test_full_width_digits_and_nbsp_are_normalised(self):
        raw = "시급\u00a0１２,０００원\u3000무관"
        cleaned = normalize_text(raw)
        self.assertIn("12,000원", cleaned)
        self.assertNotIn("\u00a0", cleaned)

    def test_bullets_and_trailing_noise_are_stripped(self):
        cleaned = normalize_text("- 자격요건:\n* Python 경력\n\n\n- React")
        self.assertEqual(cleaned, "자격요건\nPython 경력\nReact")

    def test_empty_input_returns_empty(self):
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")


class DetectTests(unittest.TestCase):
    def test_korean_listing_detected(self):
        self.assertEqual(detect_language("파이썬 개발 경험자"), "ko")

    def test_english_listing_detected(self):
        self.assertEqual(detect_language("Python development experience required"), "en")

    def test_mixed_listing_still_korean(self):
        self.assertEqual(detect_language("Python 개발 경험 및 TOPIK 4급 우대"), "ko")

    def test_empty_is_undetermined(self):
        self.assertEqual(detect_language("   "), "und")

    def test_hangul_ratio_between_zero_and_one(self):
        self.assertEqual(hangul_ratio(""), 0.0)
        self.assertEqual(hangul_ratio("한국어"), 1.0)


class GazetteerTests(unittest.TestCase):
    def test_korean_and_english_aliases_resolve_to_one_skill(self):
        self.assertEqual(resolve("파이썬"), "python")
        self.assertEqual(resolve("Python"), "python")
        self.assertEqual(resolve("Py"), "python")

    def test_cpp_does_not_register_the_c_language(self):
        names = [hit["name"] for hit in find_skills("C++ 개발 경험자")]
        self.assertIn("c++", names)
        self.assertNotIn("c", names)

    def test_c_language_needs_an_explicit_form(self):
        self.assertIn("c", [hit["name"] for hit in find_skills("C언어 가능자")])

    def test_git_does_not_match_github(self):
        names = [hit["name"] for hit in find_skills("GitHub 사용 경험")]
        self.assertIn("github", names)
        self.assertNotIn("git", names)

    def test_evidence_records_the_matched_phrase(self):
        hits = {hit["name"]: hit for hit in find_skills("파이썬 개발 경험")}
        self.assertEqual(hits["python"]["evidence"], "파이썬")

    def test_unknown_text_yields_nothing(self):
        self.assertEqual(find_skills("카페에서 아르바이트"), [])

    def test_no_false_positive_on_ordinary_korean_prose(self):
        names = [hit["name"] for hit in find_skills("매장 관리 및 고객 응대 업무")]
        self.assertEqual(names, [])


class SegmentTests(unittest.TestCase):
    def test_header_sets_mode_for_following_lines(self):
        segments = segment_text(SOFTWARE_INTERNSHIP)
        required = [s.text for s in segments if s.kind == REQUIRED and not s.is_header]
        self.assertTrue(any("컴퓨터공학 전공자" in text for text in required))

    def test_preferred_section_is_not_required(self):
        segments = segment_text(SOFTWARE_INTERNSHIP)
        preferred = [s.text for s in segments if s.kind == PREFERRED and not s.is_header]
        self.assertTrue(any("딥러닝" in text for text in preferred))
        self.assertFalse(any("딥러닝" in s.text for s in segments if s.kind == REQUIRED))

    def test_duties_are_not_requirements(self):
        segments = segment_text(SOFTWARE_INTERNSHIP)
        duties = [s.text for s in segments if s.kind == DUTY and not s.is_header]
        self.assertTrue(any("데이터 분석" in text for text in duties))

    def test_clause_level_split_keeps_required_and_preferred_apart(self):
        text = "자격요건: 컴퓨터공학 전공자, TOPIK 4급 우대자"
        kinds = {s.text: s.kind for s in segment_text(text) if not s.is_header}
        self.assertEqual(kinds["컴퓨터공학 전공자"], REQUIRED)
        self.assertEqual(kinds["TOPIK 4급 우대자"], PREFERRED)

    def test_header_label_is_stripped_from_the_clause_evidence(self):
        kinds = {s.text for s in segment_text("자격요건: Python 경력")}
        self.assertIn("Python 경력", kinds)
        self.assertNotIn("자격요건: Python 경력", kinds)

    def test_header_with_multiple_clauses_governs_all_of_them(self):
        text = "자격요건: 컴퓨터공학 전공자, 성실한 분"
        kinds = [s.kind for s in segment_text(text) if not s.is_header]
        self.assertEqual(kinds, [REQUIRED, REQUIRED])

    def test_text_without_markers_is_unstated(self):
        segments = segment_text("Python으로 데이터 분석")
        self.assertTrue(any(s.kind == UNSTATED for s in segments))


class EligibilityTests(unittest.TestCase):
    def test_stated_acceptance_is_attributed(self):
        result = extract_eligibility("외국인 가능")
        self.assertTrue(result["international_students_accepted"])
        self.assertEqual(result["display"], DISPLAY_ACCEPTED)
        self.assertEqual(result["source"], "employer")

    def test_visa_requirement_is_reported_without_advising(self):
        result = extract_eligibility("외국인 비자 필요")
        self.assertIsNone(result["international_students_accepted"])
        self.assertEqual(result["display"], DISPLAY_VISA)

    def test_silence_means_not_specified_not_refused(self):
        result = extract_eligibility("컴퓨터공학 전공자 우대")
        self.assertIsNone(result["international_students_accepted"])
        self.assertEqual(result["display"], DISPLAY_UNSPECIFIED)

    def test_empty_description_is_not_specified(self):
        self.assertEqual(extract_eligibility("")["display"], DISPLAY_UNSPECIFIED)

    def test_no_phrase_ever_claims_legal_permission(self):
        samples = [
            "외국인 가능",
            "외국인 비자 필요",
            "비자 필요",
            "외국인 환영",
            "",
        ]
        forbidden = ("legal", "permitted to work", "you can work", "eligible to work")
        for sample in samples:
            display = extract_eligibility(sample)["display"].lower()
            for phrase in forbidden:
                self.assertNotIn(phrase, display)


class LanguageRequirementTests(unittest.TestCase):
    def test_topik_level_is_extracted(self):
        segments = segment_text("TOPIK 4급 우대자")
        found = extract_language_requirements(segments)
        korean = [item for item in found if item["language"] == "korean"]
        self.assertTrue(korean)
        self.assertEqual(korean[0]["level_value"], 4)

    def test_english_requirement_is_extracted(self):
        segments = segment_text("영어 가능자")
        found = extract_language_requirements(segments)
        self.assertTrue(any(item["language"] == "english" for item in found))

    def test_preferred_marker_is_carried_through(self):
        segments = segment_text("TOPIK 4급 우대자")
        found = extract_language_requirements(segments)
        self.assertEqual(found[0]["requirement"], PREFERRED)

    def test_possibility_wording_follows_its_section_not_a_noun_suffix(self):
        # "영어 가능자" under 우대사항 is preferred. "가능자" is a noun suffix,
        # not a requirement marker, so it must not override the header.
        segments = segment_text("우대사항\n영어 가능자")
        found = extract_language_requirements(segments)
        english = [item for item in found if item["language"] == "english"]
        self.assertTrue(english)
        self.assertEqual(english[0]["requirement"], PREFERRED)

    def test_possibility_wording_under_a_required_section_is_required(self):
        segments = segment_text("지원자격\n영어 가능자")
        found = extract_language_requirements(segments)
        english = [item for item in found if item["language"] == "english"]
        self.assertEqual(english[0]["requirement"], REQUIRED)


class NumberTests(unittest.TestCase):
    def test_plain_digits(self):
        self.assertEqual(parse_korean_number("12000"), 12000.0)

    def test_comma_grouped(self):
        self.assertEqual(parse_korean_number("12,000"), 12000.0)

    def test_man_unit(self):
        self.assertEqual(parse_korean_number("200만"), 2_000_000.0)

    def test_digit_then_man(self):
        self.assertEqual(parse_korean_number("1.2만"), 12_000.0)

    def test_keun_and_man_are_additive(self):
        # Korean writes 102 million as "1억 2천만". "1억 2천" is 100,002,000.
        self.assertEqual(parse_korean_number("1억 2천"), 100_002_000.0)
        self.assertEqual(parse_korean_number("1억 2천만"), 120_000_000.0)

    def test_unparseable_returns_none(self):
        self.assertIsNone(parse_korean_number("협상"))


class SalaryTests(unittest.TestCase):
    def test_hourly_range(self):
        result = extract_salary("시급 12,000원~14,000원")
        self.assertEqual(result["min"], 12000.0)
        self.assertEqual(result["max"], 14000.0)
        self.assertEqual(result["unit"], "hour")

    def test_monthly_with_man(self):
        result = extract_salary("월급 200만원")
        self.assertEqual(result["min"], 2_000_000.0)
        self.assertEqual(result["unit"], "month")

    def test_negotiable_is_not_zero(self):
        result = extract_salary("급여 면협")
        self.assertIsNone(result["value"])
        self.assertTrue(result["negotiable"])

    def test_absent_salary_returns_none(self):
        result = extract_salary("카페 홀 직원 모집")
        self.assertIsNone(result["value"])


class WorkingHoursTests(unittest.TestCase):
    def test_weekly_hours(self):
        self.assertEqual(extract_working_hours("주 20시간 근무")["weekly_hours"], 20)

    def test_days_per_week(self):
        self.assertEqual(extract_working_hours("주 3회 근무")["days_per_week"], 3)

    def test_weekday_detection(self):
        self.assertEqual(
            extract_working_hours("평일 근무")["weekdays"],
            ["월", "화", "수", "목", "금"],
        )

    def test_weekend_is_not_sunday_only(self):
        self.assertEqual(extract_working_hours("주말 근무")["weekdays"], ["토", "일"])

    def test_full_day_names(self):
        self.assertEqual(extract_working_hours("화, 목 근무")["weekdays"], ["화", "목"])

    def test_day_character_inside_a_word_is_not_a_day(self):
        # "금액" contains 금 and "일" appears in 평일; neither is a weekday.
        result = extract_working_hours("금액 정산 업무")
        self.assertEqual(result["weekdays"], [])

    def test_month_in_a_deadline_is_not_a_weekday(self):
        result = extract_working_hours("접수기간: 10월 10일까지")
        self.assertEqual(result["weekdays"], [])

    def test_a_real_weekday_survives_alongside_a_deadline(self):
        result = extract_working_hours("접수기간: 10월 10일까지, 평일 근무")
        self.assertEqual(result["weekdays"], ["월", "화", "수", "목", "금"])

    def test_afternoon_time_range(self):
        result = extract_working_hours("평일 오후 2시~6시")
        self.assertEqual(result["start"], "14:00")
        self.assertEqual(result["end"], "18:00")

    def test_morning_noon_edge_case(self):
        self.assertEqual(extract_working_hours("오전 9시 ~ 오후 6시")["end"], "18:00")


class ExperienceTests(unittest.TestCase):
    def test_years_required(self):
        self.assertEqual(extract_experience("경력 3년 이상")["years"], 3)

    def test_reversed_word_order(self):
        self.assertEqual(extract_experience("3년 이상 경력")["years"], 3)

    def test_fresh_graduate_allowed(self):
        result = extract_experience("경력무관")
        self.assertTrue(result["fresh_graduate_ok"])
        self.assertIsNone(result["years"])

    def test_not_stated_returns_none(self):
        self.assertIsNone(extract_experience("성실한 분")["years"])


class EducationTests(unittest.TestCase):
    def test_undergraduate(self):
        self.assertEqual(extract_education("4년제 졸업자")["level"], "bachelor")

    def test_graduate_student(self):
        self.assertEqual(extract_education("대학원생 가능")["level"], "graduate")


class DeadlineTests(unittest.TestCase):
    def test_iso_date(self):
        result = extract_deadline("마감 2026-10-10", today=date(2026, 9, 26))
        self.assertEqual(result["value"], "2026-10-10")

    def test_korean_full_date(self):
        result = extract_deadline("접수기간: 2026년 10월 10일까지", today=date(2026, 9, 26))
        self.assertEqual(result["value"], "2026-10-10")

    def test_missing_year_infers_from_posted_at(self):
        result = extract_deadline("접수기간: 10월 10일까지", posted_at=datetime(2026, 9, 26))
        self.assertEqual(result["value"], "2026-10-10")
        self.assertTrue(result["inferred_year"])

    def test_missing_year_rolls_forward_when_already_past(self):
        result = extract_deadline("접수기간: 1월 15일까지", posted_at=datetime(2026, 11, 20))
        self.assertEqual(result["value"], "2027-01-15")

    def test_date_without_keyword_is_ignored(self):
        result = extract_deadline("근무 시작 3월 1일", today=date(2026, 9, 26))
        self.assertIsNone(result["value"])

    def test_invalid_date_is_ignored_not_raised(self):
        result = extract_deadline("마감 13월 45일", today=date(2026, 9, 26))
        self.assertIsNone(result["value"])


class PipelineTests(unittest.TestCase):
    def test_full_korean_listing(self):
        result = extract_listing(SOFTWARE_INTERNSHIP, posted_at=datetime(2026, 9, 26))

        self.assertEqual(result.original_language, "ko")
        self.assertIn("python", result.skill_names(REQUIRED))
        self.assertIn("machine learning", result.skill_names(REQUIRED))
        self.assertIn("deep learning", result.skill_names(PREFERRED))
        self.assertIn("data analysis", result.skill_names(DUTY))
        self.assertTrue(result.eligibility["international_students_accepted"])
        self.assertEqual(result.deadline, "2026-10-10")
        self.assertEqual(result.salary["unit"], "hour")
        self.assertEqual(result.warnings, [])

    def test_english_under_preferred_section_is_not_promoted_to_required(self):
        result = extract_listing(SOFTWARE_INTERNSHIP, posted_at=datetime(2026, 9, 26))
        english = [item for item in result.language_requirements if item["language"] == "english"]
        self.assertTrue(english)
        self.assertEqual(english[0]["requirement"], PREFERRED)

    def test_cafe_listing_with_visa_requirement(self):
        result = extract_listing(CAFE_PART_TIME, posted_at=datetime(2026, 9, 26))

        self.assertIsNone(result.eligibility["international_students_accepted"])
        self.assertEqual(result.eligibility["display"], DISPLAY_VISA)
        self.assertTrue(result.experience["fresh_graduate_ok"])
        self.assertEqual(result.salary["min"], 12000.0)
        self.assertEqual(result.salary["max"], 14000.0)
        self.assertEqual(result.working_hours["weekly_hours"], 20)

    def test_original_text_is_not_returned_or_modified(self):
        result = extract_listing(SOFTWARE_INTERNSHIP)
        self.assertNotIn("description", result.to_dict())

    def test_empty_description_warns_instead_of_raising(self):
        result = extract_listing("")
        self.assertTrue(result.warnings)
        self.assertEqual(result.required_skills, [])

    def test_to_dict_is_serialisable(self):
        import json

        payload = extract_listing(SOFTWARE_INTERNSHIP).to_dict()
        json.dumps(payload)
        self.assertIn("eligibility", payload)
        self.assertIn("extraction_version", payload)

    def test_english_listing_still_yields_skills(self):
        result = extract_listing("Requirements: Python and SQL experience")
        self.assertEqual(result.original_language, "en")
        self.assertTrue(result.skill_names(REQUIRED) or result.skill_names(UNSTATED))

    def test_a_failing_stage_does_not_lose_other_results(self):
        original = find_skills

        def boom(text, restrict_to=None):
            if text and "salary-poison" in text:
                raise ValueError("synthetic failure")
            return original(text, restrict_to)

        import app.nlp.pipeline as pipeline_module

        pipeline_module.find_skills = boom
        try:
            result = pipeline_module.extract_listing("salary-poison\nPython 경력")
        finally:
            pipeline_module.find_skills = original

        self.assertTrue(any("failed" in warning for warning in result.warnings))
        self.assertEqual(result.experience.get("years"), None)


if __name__ == "__main__":
    unittest.main()
