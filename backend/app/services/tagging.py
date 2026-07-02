from __future__ import annotations
from ..models import QuestionRecord, CurriculumUnit
from .curriculum import minor_units


def tag_questions_heuristic(questions: list[QuestionRecord], curriculum: list[CurriculumUnit]) -> list[QuestionRecord]:
    minors = minor_units(curriculum)
    if not minors:
        return questions
    for index, q in enumerate(questions):
        unit = minors[index % len(minors)]
        q.primaryUnitId = unit.id
        q.secondaryUnitIds = [u.id for u in minors if u.id != unit.id][:1]
        q.tags = unit.tags + unit.keywords[:2]
        q.tagConfidence = 0.74
        q.isLong = (q.questionNumber % 7 == 0)
    return questions


def sorted_questions(questions: list[QuestionRecord]) -> list[QuestionRecord]:
    return sorted(questions, key=lambda q: (q.primaryUnitId or "ZZZ", q.sourceName, q.questionNumber))
