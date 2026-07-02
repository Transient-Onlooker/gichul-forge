from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..models import CurriculumUnit
from ..settings import get_settings

REVISION = "2022"
SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "curriculum_2022_seed.json"

SUPPORTED_SUBJECTS = ("공통수학1", "공통수학2", "통합과학1", "통합과학2")
SUBJECT_ALIASES = {
    "공통수학1": ("공통수학1", "공수1", "공통수학", "수학"),
    "공통수학2": ("공통수학2", "공수2"),
    "통합과학1": ("통합과학1", "통과1", "통합과학", "과학"),
    "통합과학2": ("통합과학2", "통과2"),
}
SUBJECT_AREA = {
    "공통수학1": "math",
    "공통수학2": "math",
    "통합과학1": "science",
    "통합과학2": "science",
}


def _compact(text: str) -> str:
    return text.replace(" ", "").lower()


def normalize_subject(subject: str) -> str:
    compact = _compact(subject)

    for canonical in SUPPORTED_SUBJECTS:
        if compact == _compact(canonical):
            return canonical

    for canonical, aliases in SUBJECT_ALIASES.items():
        if any(compact == _compact(alias) for alias in aliases):
            return canonical

    for canonical, aliases in SUBJECT_ALIASES.items():
        specific_aliases = [alias for alias in aliases if alias not in {"공통수학", "수학", "통합과학", "과학"}]
        if any(_compact(alias) in compact for alias in specific_aliases):
            return canonical

    if "공통수학" in compact or compact == "수학":
        return "공통수학1"
    if "통합과학" in compact or compact == "과학":
        return "통합과학1"

    return subject.strip()


def subject_area(subject: str) -> str | None:
    return SUBJECT_AREA.get(normalize_subject(subject))


def supported_subject(subject: str) -> bool:
    return normalize_subject(subject) in SUPPORTED_SUBJECTS


def _db_path() -> Path:
    settings = get_settings()
    path = settings.storage_path / "curriculum_2022.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS units (
            id TEXT PRIMARY KEY,
            revision TEXT NOT NULL,
            subject_area TEXT NOT NULL,
            course TEXT NOT NULL,
            grade_band TEXT NOT NULL,
            parent_id TEXT REFERENCES units(id),
            level TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            source_note TEXT,
            requires_confirmation INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            keywords_json TEXT NOT NULL DEFAULT '[]',
            tags_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS legacy_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_area TEXT NOT NULL,
            legacy_title TEXT NOT NULL,
            legacy_keywords_json TEXT NOT NULL DEFAULT '[]',
            target_unit_id TEXT REFERENCES units(id),
            action TEXT NOT NULL,
            note TEXT NOT NULL
        );
        """
    )


def _seed_version() -> str:
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return str(data["version"])


def _needs_seed(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT value FROM metadata WHERE key = 'seed_version'").fetchone()
    return not row or row["value"] != _seed_version()


def _seed(conn: sqlite3.Connection) -> None:
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    conn.executescript("DELETE FROM legacy_mappings; DELETE FROM units; DELETE FROM metadata;")
    for unit in data["units"]:
        conn.execute(
            """
            INSERT INTO units (
                id, revision, subject_area, course, grade_band, parent_id, level, title,
                status, source_note, requires_confirmation, sort_order, keywords_json, tags_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                unit["id"],
                data["revision"],
                unit["subjectArea"],
                unit["course"],
                unit.get("gradeBand", "high"),
                unit.get("parentId"),
                unit["level"],
                unit["title"],
                unit.get("status", "active"),
                unit.get("sourceNote"),
                1 if unit.get("requiresConfirmation") else 0,
                unit.get("sortOrder", 0),
                json.dumps(unit.get("keywords", []), ensure_ascii=False),
                json.dumps(unit.get("tags", []), ensure_ascii=False),
            ),
        )
    for mapping in data.get("legacyMappings", []):
        conn.execute(
            """
            INSERT INTO legacy_mappings (
                subject_area, legacy_title, legacy_keywords_json, target_unit_id, action, note
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                mapping["subjectArea"],
                mapping["legacyTitle"],
                json.dumps(mapping.get("legacyKeywords", []), ensure_ascii=False),
                mapping.get("targetUnitId"),
                mapping["action"],
                mapping["note"],
            ),
        )
    conn.execute("INSERT INTO metadata (key, value) VALUES ('seed_version', ?)", (str(data["version"]),))
    conn.commit()


@lru_cache(maxsize=1)
def ensure_curriculum_db() -> Path:
    path = _db_path()
    with _connect() as conn:
        _schema(conn)
        if _needs_seed(conn):
            _seed(conn)
    return path


def _rows_for(subject: str) -> list[sqlite3.Row]:
    normalized = normalize_subject(subject)
    area = SUBJECT_AREA.get(normalized)
    if not area:
        return []
    ensure_curriculum_db()
    with _connect() as conn:
        return conn.execute(
            """
            SELECT * FROM units
            WHERE revision = ?
              AND subject_area = ?
              AND course = ?
              AND status IN ('active', 'new', 'transferred')
            ORDER BY sort_order, id
            """,
            (REVISION, area, normalized),
        ).fetchall()


def _unit_from_row(row: sqlite3.Row) -> CurriculumUnit:
    return CurriculumUnit(
        id=row["id"],
        level=row["level"],
        title=row["title"],
        subjectArea=row["subject_area"],
        curriculumRevision=row["revision"],
        course=row["course"],
        status=row["status"],
        sourceNote=row["source_note"],
        requiresConfirmation=bool(row["requires_confirmation"]),
        keywords=json.loads(row["keywords_json"]),
        tags=json.loads(row["tags_json"]),
        children=[],
    )


def curriculum_for(subject: str, grade: str | None = None) -> list[CurriculumUnit]:
    rows = _rows_for(subject)
    units_by_id = {row["id"]: _unit_from_row(row) for row in rows}
    roots: list[CurriculumUnit] = []
    for row in rows:
        unit = units_by_id[row["id"]]
        parent_id = row["parent_id"]
        if parent_id and parent_id in units_by_id:
            units_by_id[parent_id].children.append(unit)
        else:
            roots.append(unit)
    return roots


def minor_units(units: list[CurriculumUnit]) -> list[CurriculumUnit]:
    out: list[CurriculumUnit] = []

    def walk(unit: CurriculumUnit) -> None:
        if unit.level == "minor" and unit.status != "removed":
            out.append(unit)
        for child in unit.children:
            walk(child)

    for unit in units:
        walk(unit)
    return out


def confirmation_units(units: list[CurriculumUnit]) -> list[CurriculumUnit]:
    out: list[CurriculumUnit] = []

    def walk(unit: CurriculumUnit) -> None:
        if unit.requiresConfirmation:
            out.append(unit)
        for child in unit.children:
            walk(child)

    for unit in units:
        walk(unit)
    return out


def legacy_mapping_for_text(subject: str, text: str) -> dict[str, Any] | None:
    ensure_curriculum_db()
    area = subject_area(subject)
    if not area:
        return None
    haystack = _compact(text)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM legacy_mappings WHERE subject_area = ? ORDER BY id",
            (area,),
        ).fetchall()
    for row in rows:
        terms = [row["legacy_title"], *json.loads(row["legacy_keywords_json"])]
        if any(_compact(term) in haystack for term in terms):
            return {
                "legacyTitle": row["legacy_title"],
                "targetUnitId": row["target_unit_id"],
                "action": row["action"],
                "note": row["note"],
            }
    return None
