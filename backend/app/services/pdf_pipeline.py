from __future__ import annotations
import re
import uuid
from pathlib import Path
from typing import Iterable
import fitz  # PyMuPDF
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from ..models import PdfAsset, PageRange, QuestionRecord, AnswerRecord, IssueRecord, ExamMetadata
from ..settings import get_settings
from .nim import nim_client


def detect_role(asset: PdfAsset) -> PdfAsset:
    text = f"{asset.originalName} {asset.firstPageText or ''}".lower()
    if any(k in text for k in ["정답", "해설", "답지", "answer", "solution"]):
        asset.role = "answer"
        asset.confidence = 0.86
    elif any(k in text for k in ["문제", "시험지", "기출", "question", "exam"]):
        asset.role = "question"
        asset.confidence = 0.78
    else:
        asset.role = "unknown"
        asset.confidence = 0.45
    if asset.role == "question":
        asset.questionRange = PageRange(start=1, end=max(asset.pageCount, 1))
    elif asset.role == "answer":
        asset.answerRange = PageRange(start=1, end=max(asset.pageCount, 1))
    return asset


async def detect_role_ai(asset: PdfAsset) -> PdfAsset:
    if not nim_client.enabled:
        return detect_role(asset)
    fallback = {
        "role": asset.role,
        "confidence": asset.confidence,
        "questionRange": asset.questionRange.model_dump() if asset.questionRange else None,
        "answerRange": asset.answerRange.model_dump() if asset.answerRange else None,
    }
    data = await nim_client.extract_json(
        nim_client.settings.nvidia_nim_text_model,
        "Classify a Korean exam PDF. Return JSON only with role as one of question, answer, combined, unknown; confidence 0..1; optional questionRange and answerRange objects with start/end page numbers.",
        f"filename={asset.originalName}\npageCount={asset.pageCount}\nfirstPageText={asset.firstPageText or ''}",
        fallback,
    )
    role = data.get("role")
    if role in {"question", "answer", "combined", "unknown"}:
        asset.role = role
    try:
        asset.confidence = float(data.get("confidence", asset.confidence))
    except Exception:
        pass
    for attr in ("questionRange", "answerRange"):
        raw = data.get(attr)
        if isinstance(raw, dict) and raw.get("start") and raw.get("end"):
            try:
                setattr(asset, attr, PageRange(start=int(raw["start"]), end=int(raw["end"])))
            except Exception:
                pass
    return asset


def infer_combined_ranges(asset: PdfAsset) -> PdfAsset:
    text = asset.firstPageText or ""
    if asset.role == "unknown" and asset.pageCount >= 2 and re.search(r"정답|해설|답", text):
        asset.role = "combined"
        asset.confidence = 0.62
    if asset.role == "combined":
        mid = max(1, asset.pageCount - 1)
        asset.questionRange = PageRange(start=1, end=mid)
        asset.answerRange = PageRange(start=mid + 1, end=asset.pageCount)
    return asset


def extract_pdf_range(src: Path, dst: Path, page_range: PageRange) -> None:
    reader = PdfReader(str(src))
    writer = PdfWriter()
    start = max(1, page_range.start)
    end = min(len(reader.pages), page_range.end)
    for idx in range(start - 1, end):
        writer.add_page(reader.pages[idx])
    with dst.open("wb") as out:
        writer.write(out)




def extract_pdf_text(path: Path, page_range: PageRange | None = None) -> str:
    try:
        reader = PdfReader(str(path))
        start = 1 if page_range is None else max(1, page_range.start)
        end = len(reader.pages) if page_range is None else min(len(reader.pages), page_range.end)
        chunks = []
        for idx in range(start - 1, end):
            chunks.append(reader.pages[idx].extract_text() or "")
        return "\n".join(chunks)
    except Exception:
        return ""


async def extract_pdf_text_with_vision(path: Path, page_range: PageRange | None = None, max_pages: int = 3) -> str:
    text = extract_pdf_text(path, page_range)
    if len(text.strip()) >= 80 or not nim_client.enabled:
        return text
    out_dir = path.parent / f"{path.stem}_ocr_pages"
    pages = render_pages(path, out_dir, dpi=160)
    if page_range:
        pages = pages[max(0, page_range.start - 1):page_range.end]
    chunks: list[str] = []
    for page in pages[:max_pages]:
        chunk = await nim_client.vision_text(
            nim_client.settings.nvidia_nim_ocr_model,
            page,
            "Read all visible Korean and English text in this exam page. Return plain text only, preserving problem numbers and answer numbers when visible.",
            "",
        )
        if chunk.strip():
            chunks.append(chunk.strip())
    return "\n\n".join(chunks) if chunks else text

def render_pages(pdf_path: Path, out_dir: Path, dpi: int = 180) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    doc = fitz.open(pdf_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        target = out_dir / f"page_{i:03d}.png"
        pix.save(str(target))
        paths.append(target)
    return paths


def heuristic_question_records(asset: PdfAsset, exam_id: str, image_paths: Iterable[Path]) -> list[QuestionRecord]:
    records: list[QuestionRecord] = []
    q_no = 1
    for page_no, image_path in enumerate(image_paths, start=1):
        # 초기 구현은 페이지당 최대 6문항 슬롯을 생성한다. 비전 모델이 있으면 worker에서 좌표/번호를 보강한다.
        for _ in range(6):
            records.append(QuestionRecord(
                examId=exam_id,
                questionId=f"{exam_id}_{q_no:03d}",
                questionNumber=q_no,
                sourcePdfId=asset.id,
                sourceName=Path(asset.standardizedName or asset.originalName).stem,
                pageNumber=page_no,
                cropPath=str(image_path),
                isLong=False,
                quality={"heuristicSlot": True},
            ))
            q_no += 1
    return records


def parse_answers(text: str, exam_id: str) -> list[AnswerRecord]:
    answers: list[AnswerRecord] = []
    pattern = re.compile(r"(?:^|\s)(\d{1,3})\s*[\).:-]?\s*([①②③④⑤1-5A-E가-힣]+)")
    for num, ans in pattern.findall(text):
        n = int(num)
        if 1 <= n <= 200:
            answers.append(AnswerRecord(examId=exam_id, questionNumber=n, answer=ans, raw=f"{num} {ans}"))
    return answers


def register_korean_font() -> str:
    settings = get_settings()
    candidates = [
        settings.mermiad_korean_font_path,
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            try:
                pdfmetrics.registerFont(TTFont("Korean", candidate))
                return "Korean"
            except Exception:
                pass
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
        return "HYSMyeongJo-Medium"
    except Exception:
        return "Helvetica"


def build_problem_pdf(path: Path, metadata: ExamMetadata, questions: list[QuestionRecord]) -> None:
    font = register_korean_font()
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    per_page = 6
    slot_w = (width - 24 * mm) / 2
    slot_h = (height - 34 * mm) / 3
    for i, q in enumerate(questions):
        if i % per_page == 0:
            if i:
                c.showPage()
            c.setFont(font, 13)
            c.drawString(12 * mm, height - 14 * mm, f"{metadata.normalizedSubjectName} | 단원별 문제")
        idx = i % per_page
        col = idx % 2
        row = idx // 2
        x = 12 * mm + col * slot_w
        y = height - 28 * mm - (row + 1) * slot_h
        c.setLineWidth(1)
        c.rect(x, y, slot_w - 3 * mm, slot_h - 3 * mm)
        c.setFont(font, 8)
        c.drawString(x + 3 * mm, y + slot_h - 9 * mm, f"{q.sourceName} #{q.questionNumber} | {q.primaryUnitId or '단원 미확인'}")
        c.setFont(font, 10)
        c.drawString(x + 3 * mm, y + slot_h - 18 * mm, f"문항 이미지: {Path(q.cropPath or '').name or '미생성'}")
        c.setFont(font, 8)
        c.drawString(x + 3 * mm, y + 6 * mm, "원본 PDF 이미지 크롭은 backend/storage/jobs/.../pages에 저장됩니다.")
    c.save()


def build_answer_pdf(path: Path, answers: list[AnswerRecord], title: str) -> None:
    font = register_korean_font()
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont(font, 14)
    c.drawString(15 * mm, height - 18 * mm, f"{title} 답지")
    x, y = 15 * mm, height - 30 * mm
    c.setFont(font, 10)
    for i, a in enumerate(answers, start=1):
        c.drawString(x, y, f"{a.questionNumber}. {a.answer}")
        y -= 8 * mm
        if y < 20 * mm:
            c.showPage(); c.setFont(font, 10); y = height - 20 * mm
    c.save()


def build_cover_pdf(path: Path, metadata: ExamMetadata, source_names: list[str]) -> None:
    font = register_korean_font()
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont(font, 24)
    c.drawCentredString(width / 2, height - 80 * mm, f"{metadata.schoolName} 기출문제 모음집")
    c.setFont(font, 13)
    c.drawCentredString(width / 2, height - 100 * mm, metadata.normalizedSubjectName)
    c.setFont(font, 9)
    y = 55 * mm
    c.drawString(18 * mm, y, "사용한 기출문제:")
    for name in source_names[:12]:
        y -= 6 * mm
        c.drawString(22 * mm, y, f"- {name}")
    c.setFont(font, 9)
    c.drawString(18 * mm, 18 * mm, f"이 모음집의 저작권은 {metadata.schoolName}에 있습니다")
    c.save()


def build_toc_pdf(path: Path, units: list[str], copyright_holder: str) -> None:
    font = register_korean_font()
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont(font, 18)
    c.drawString(15 * mm, height - 20 * mm, "목차")
    c.setFont(font, 11)
    y = height - 35 * mm
    for i, unit in enumerate(units, start=1):
        c.drawString(20 * mm, y, f"{i}. {unit}")
        y -= 8 * mm
        if y < 25 * mm:
            c.showPage(); c.setFont(font, 11); y = height - 20 * mm
    c.setFont(font, 9)
    c.drawString(15 * mm, 15 * mm, f"저작권: {copyright_holder}")
    c.save()


def merge_pdfs(paths: list[Path], output: Path) -> None:
    writer = PdfWriter()
    for path in paths:
        if not path.exists():
            continue
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    with output.open("wb") as out:
        writer.write(out)


def final_quality_check(final_pdf: Path, question_count: int, answer_count: int) -> list[IssueRecord]:
    issues: list[IssueRecord] = []
    try:
        reader = PdfReader(str(final_pdf))
        if len(reader.pages) < 3:
            issues.append(IssueRecord(id=uuid.uuid4().hex, nodeId="R8", title="페이지 수 부족", detail="최종 PDF 페이지가 너무 적습니다.", severity="critical", autoFixable=False))
    except Exception as exc:
        issues.append(IssueRecord(id=uuid.uuid4().hex, nodeId="R8", title="최종 PDF 읽기 실패", detail=str(exc), severity="critical", autoFixable=False))
    if answer_count and question_count and answer_count < min(question_count, 5):
        issues.append(IssueRecord(id=uuid.uuid4().hex, nodeId="R6", title="문항 수와 답지 수 불일치 가능성", detail=f"문항 {question_count}개, 답 {answer_count}개입니다.", severity="warning", autoFixable=True))
    return issues
