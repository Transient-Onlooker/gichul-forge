from __future__ import annotations
from ..models import CurriculumUnit

SCIENCE_ALIASES = ["과학", "통합과학", "물리", "화학", "생명", "지구"]
MATH_ALIASES = ["수학", "확률", "미적분", "기하", "대수", "해석"]


def subject_area(subject: str) -> str | None:
    s = subject.replace(" ", "").lower()
    if any(alias in s for alias in MATH_ALIASES):
        return "math"
    if any(alias in s for alias in SCIENCE_ALIASES):
        return "science"
    return None


def supported_subject(subject: str) -> bool:
    return subject_area(subject) is not None


def normalize_subject(subject: str) -> str:
    area = subject_area(subject)
    if area == "math":
        return "수학"
    if area == "science":
        if "물리" in subject:
            return "물리학"
        if "화학" in subject:
            return "화학"
        if "생명" in subject:
            return "생명과학"
        if "지구" in subject:
            return "지구과학"
        return "과학"
    return subject


def curriculum_for(subject: str, grade: str) -> list[CurriculumUnit]:
    area = subject_area(subject)
    if area == "science":
        return [
            CurriculumUnit(id="SCI-1", level="major", title="물질과 규칙성", subjectArea="science", keywords=["원소", "주기율", "결합"], tags=["matter"], children=[
                CurriculumUnit(id="SCI-1-1", level="middle", title="물질의 구성", subjectArea="science", keywords=["원자", "분자", "이온"], tags=["atom"], children=[
                    CurriculumUnit(id="SCI-1-1-1", level="minor", title="원소와 주기율", subjectArea="science", keywords=["원소", "주기율표"], tags=["periodic"]),
                    CurriculumUnit(id="SCI-1-1-2", level="minor", title="화학 결합", subjectArea="science", keywords=["이온 결합", "공유 결합"], tags=["bond"]),
                ]),
            ]),
            CurriculumUnit(id="SCI-2", level="major", title="시스템과 상호작용", subjectArea="science", keywords=["힘", "운동", "에너지"], tags=["system"], children=[
                CurriculumUnit(id="SCI-2-1", level="middle", title="역학적 시스템", subjectArea="science", keywords=["속도", "가속도", "운동량"], tags=["mechanics"], children=[
                    CurriculumUnit(id="SCI-2-1-1", level="minor", title="힘과 운동", subjectArea="science", keywords=["뉴턴", "힘", "운동"], tags=["force"]),
                    CurriculumUnit(id="SCI-2-1-2", level="minor", title="역학적 에너지", subjectArea="science", keywords=["일", "에너지", "보존"], tags=["energy"]),
                ]),
            ]),
        ]
    return [
        CurriculumUnit(id="MATH-1", level="major", title="다항식", subjectArea="math", keywords=["다항식", "나머지정리", "인수분해"], tags=["polynomial"], children=[
            CurriculumUnit(id="MATH-1-1", level="middle", title="다항식의 연산", subjectArea="math", keywords=["전개", "정리", "곱셈공식"], tags=["expand"], children=[
                CurriculumUnit(id="MATH-1-1-1", level="minor", title="다항식의 덧셈과 뺄셈", subjectArea="math", keywords=["덧셈", "뺄셈", "동류항"], tags=["poly-add"]),
                CurriculumUnit(id="MATH-1-1-2", level="minor", title="곱셈공식", subjectArea="math", keywords=["곱셈공식", "전개"], tags=["formula"]),
            ]),
            CurriculumUnit(id="MATH-1-2", level="middle", title="나머지정리와 인수분해", subjectArea="math", keywords=["나머지정리", "인수정리", "인수분해"], tags=["factor"], children=[
                CurriculumUnit(id="MATH-1-2-1", level="minor", title="나머지정리", subjectArea="math", keywords=["나머지", "조립제법"], tags=["remainder"]),
                CurriculumUnit(id="MATH-1-2-2", level="minor", title="인수분해", subjectArea="math", keywords=["인수", "공통인수"], tags=["factorization"]),
            ]),
        ]),
        CurriculumUnit(id="MATH-2", level="major", title="방정식과 부등식", subjectArea="math", keywords=["방정식", "부등식", "이차"], tags=["equation"], children=[
            CurriculumUnit(id="MATH-2-1", level="middle", title="복소수와 이차방정식", subjectArea="math", keywords=["복소수", "판별식", "근"], tags=["quadratic"], children=[
                CurriculumUnit(id="MATH-2-1-1", level="minor", title="복소수", subjectArea="math", keywords=["허수", "i", "복소수"], tags=["complex"]),
                CurriculumUnit(id="MATH-2-1-2", level="minor", title="이차방정식", subjectArea="math", keywords=["근의 공식", "판별식"], tags=["quadratic-equation"]),
            ]),
        ]),
    ]


def minor_units(units: list[CurriculumUnit]) -> list[CurriculumUnit]:
    out: list[CurriculumUnit] = []
    def walk(unit: CurriculumUnit) -> None:
        if unit.level == "minor":
            out.append(unit)
        for child in unit.children:
            walk(child)
    for u in units:
        walk(u)
    return out
