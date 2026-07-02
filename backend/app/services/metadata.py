from __future__ import annotations
import re
from pathlib import Path
from ..models import ExamMetadata
from .curriculum import normalize_subject

SCHOOL_PATTERN = re.compile(r"([가-힣A-Za-z0-9]+(?:중학교|고등학교|중|고))")
YEAR_PATTERN = re.compile(r"(20\d{2})")
GRADE_PATTERN = re.compile(r"(중|고)?\s*([1-3])\s*학년|([1-3])\s*학년")
SEMESTER_PATTERN = re.compile(r"([12])\s*학기")
EXAM_PATTERN = re.compile(r"(중간|기말|1차|2차|모의|수행)")


def metadata_from_text(filename: str, first_page_text: str, subject: str, grade: str) -> ExamMetadata:
    text = f"{Path(filename).stem} {first_page_text[:2000]}"
    school = SCHOOL_PATTERN.search(text)
    year = YEAR_PATTERN.search(text)
    grade_m = GRADE_PATTERN.search(text)
    semester = SEMESTER_PATTERN.search(text)
    exam = EXAM_PATTERN.search(text)
    normalized = normalize_subject(subject)
    return ExamMetadata(
        schoolName=school.group(1) if school else "미확인 학교",
        schoolYear=year.group(1) if year else "미확인 학년도",
        grade=(f"{grade_m.group(1) or ''}{grade_m.group(2) or grade_m.group(3)}" if grade_m else grade),
        semester=(f"{semester.group(1)}학기" if semester else "미확인 학기"),
        examName=(f"{exam.group(1)}고사" if exam else "미확인 시험"),
        subjectName=subject,
        normalizedSubjectName=normalized,
    )


def exam_id_from_metadata(meta: ExamMetadata) -> str:
    raw = "_".join([meta.schoolName, meta.schoolYear, meta.grade, meta.semester, meta.examName, meta.normalizedSubjectName])
    safe = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", raw).strip("_")
    return safe or "exam"


def standardized_pdf_name(meta: ExamMetadata, role: str) -> str:
    return f"{exam_id_from_metadata(meta)}_{role}.pdf"
