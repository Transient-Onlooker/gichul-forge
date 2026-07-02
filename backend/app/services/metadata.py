from __future__ import annotations
import re
from pathlib import Path
from ..models import ExamMetadata
from .curriculum import normalize_subject
from .nim import nim_client

SCHOOL_PATTERN = re.compile(r"([가-힣A-Za-z0-9]+(?:중학교|고등학교|중|고))")
YEAR_PATTERN = re.compile(r"(20\d{2})")
GRADE_PATTERN = re.compile(r"(중|고)?\s*([1-3])\s*학년|([1-3])\s*학년")
SEMESTER_PATTERN = re.compile(r"([12])\s*학기")
EXAM_PATTERN = re.compile(r"(중간|기말|1차|2차|모의|수행)")
KOREAN_OR_KNOWN_PATTERN = re.compile(r"[가-힣0-9A-Za-z]")


def metadata_from_text(filename: str, first_page_text: str, subject: str, grade_hint: str | None = None) -> ExamMetadata:
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
        grade=(f"{grade_m.group(1) or ''}{grade_m.group(2) or grade_m.group(3)}" if grade_m else (grade_hint or "미확인 학년")),
        semester=(f"{semester.group(1)}학기" if semester else "미확인 학기"),
        examName=(f"{exam.group(1)}고사" if exam else "미확인 시험"),
        subjectName=subject,
        normalizedSubjectName=normalized,
    )


async def metadata_from_text_ai(filename: str, first_page_text: str, subject: str, grade_hint: str | None = None) -> ExamMetadata:
    fallback = metadata_from_text(filename, first_page_text, subject, grade_hint)
    system = (
        "You extract Korean exam metadata. Return JSON only with keys: "
        "schoolName, schoolYear, grade, semester, examName, subjectName, normalizedSubjectName. "
        "Use unknown Korean placeholders only when the value is truly missing."
    )
    user = (
        f"Filename: {filename}\n"
        f"User subject: {subject}\n"
        f"2022 normalized subject should be based on this project policy.\n"
        f"Text:\n{first_page_text[:5000]}"
    )
    data = await nim_client.extract_json(
        nim_client.settings.nvidia_nim_metadata_model,
        system,
        user,
        fallback.model_dump(),
    )
    try:
        clean = fallback.model_dump()
        for key, value in data.items():
            if key not in clean or not isinstance(value, str):
                continue
            value = value.strip()
            if not value or not KOREAN_OR_KNOWN_PATTERN.search(value):
                continue
            if key == "schoolYear" and not re.fullmatch(r"20\d{2}|미확인 학년도", value):
                continue
            if key == "semester" and not re.search(r"[12]\s*학기|미확인", value):
                continue
            clean[key] = value
        clean["subjectName"] = subject
        clean["normalizedSubjectName"] = normalize_subject(subject)
        return ExamMetadata(**clean)
    except Exception:
        return fallback


def exam_id_from_metadata(meta: ExamMetadata) -> str:
    raw = "_".join([meta.schoolName, meta.schoolYear, meta.grade, meta.semester, meta.examName, meta.normalizedSubjectName])
    safe = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", raw).strip("_")
    return safe or "exam"


def standardized_pdf_name(meta: ExamMetadata, role: str) -> str:
    return f"{exam_id_from_metadata(meta)}_{role}.pdf"
