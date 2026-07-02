from __future__ import annotations
from ..models import QuestionRecord, CurriculumUnit
from .curriculum import minor_units
from .nim import nim_client


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


async def tag_questions_ai(questions: list[QuestionRecord], curriculum: list[CurriculumUnit]) -> list[QuestionRecord]:
    minors = minor_units(curriculum)
    if not minors or not nim_client.enabled:
        return tag_questions_heuristic(questions, curriculum)

    unit_catalog = [
        {
            "id": unit.id,
            "title": unit.title,
            "course": unit.course,
            "keywords": unit.keywords,
            "tags": unit.tags,
            "status": unit.status,
        }
        for unit in minors
    ]
    system = (
        "You map Korean exam questions to the 2022 revised Korean curriculum. "
        "Return JSON only. Choose only active 2022 unit IDs from the provided catalog. "
        "If text is insufficient, still choose the best unit with low confidence."
    )
    for index, q in enumerate(questions):
        fallback_unit = minors[index % len(minors)]
        fallback = {
            "primaryUnitId": fallback_unit.id,
            "secondaryUnitIds": [],
            "tags": fallback_unit.tags + fallback_unit.keywords[:2],
            "confidence": 0.55,
            "isLong": q.isLong,
        }
        user = {
            "questionNumber": q.questionNumber,
            "sourceName": q.sourceName,
            "ocrText": q.ocrText or "",
            "unitCatalog": unit_catalog,
        }
        data = await nim_client.extract_json(
            nim_client.settings.nvidia_nim_tagger_model,
            system,
            str(user),
            fallback,
        )
        valid_ids = {unit.id for unit in minors}
        primary = data.get("primaryUnitId")
        if primary not in valid_ids:
            primary = fallback["primaryUnitId"]
        secondary = [u for u in data.get("secondaryUnitIds", []) if u in valid_ids and u != primary]
        q.primaryUnitId = primary
        q.secondaryUnitIds = secondary[:3]
        q.tags = [str(t) for t in data.get("tags", fallback["tags"])][:10]
        try:
            q.tagConfidence = float(data.get("confidence", fallback["confidence"]))
        except Exception:
            q.tagConfidence = fallback["confidence"]
        q.isLong = bool(data.get("isLong", q.isLong))
    return questions
