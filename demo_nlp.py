import json
from datetime import datetime
from app.nlp import extract_listing

listing = """
[채용공고] AI 연구 보조 인턴 (외국인 환영)

고용형태: 인턴 / 근무지역: 부산광역시
급여: 시급 15,000원~18,000원 (주 20시간)

지원자격
- 컴퓨터공학 전공자
- Python 개발 경험 1년 이상
- 머신러닝 기초 지식
- 토픽 4급

우대사항
- 딥러닝 경험자
- 영어 가능자
- GitHub 공개 프로젝트

담당 업무
- 데이터 분석 및 모델 학습 보조

기타
- 외국인 환영
- 접수기간: 10월 10일까지
"""
r = extract_listing(listing, posted_at=datetime(2026, 9, 26))
for k in ("original_language", "deadline"):
    print(k, "=", r.to_dict()[k])
print("required  =", r.skill_names("required"))
print("preferred =", r.skill_names("preferred"))
print("unstated  =", r.skill_names("unstated"))
print("duties    =", r.skill_names("duty"))
print("language  =", [(l["language"], l["level"], l["requirement"]) for l in r.language_requirements])
print("salary    =", {k: r.salary[k] for k in ("min","max","unit")})
print("hours     =", {k: r.working_hours[k] for k in ("weekly_hours","weekdays")})
print("exp       =", r.experience)
print("eligible  =", r.eligibility["display"])
print("warnings  =", r.warnings)
