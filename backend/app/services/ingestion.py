from __future__ import annotations
import shutil
import uuid
import zipfile
from pathlib import Path
from fastapi import UploadFile
from pypdf import PdfReader
from ..models import PdfAsset, IssueRecord


def safe_filename(name: str) -> str:
    return Path(name).name.replace("/", "_").replace("\\", "_")


async def save_uploads(files: list[UploadFile], job_dir: Path, max_mb: int) -> list[Path]:
    upload_dir = job_dir / "raw"
    upload_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for f in files:
        target = upload_dir / f"{uuid.uuid4().hex}_{safe_filename(f.filename or 'upload.bin')}"
        size = 0
        with target.open("wb") as out:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_mb * 1024 * 1024:
                    raise ValueError(f"업로드 제한 {max_mb}MB를 초과했습니다: {f.filename}")
                out.write(chunk)
        paths.append(target)
    return paths


def unpack_inputs(paths: list[Path], job_dir: Path) -> tuple[list[Path], list[IssueRecord]]:
    pdf_dir = job_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdfs: list[Path] = []
    issues: list[IssueRecord] = []
    for path in paths:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            target = pdf_dir / safe_filename(path.name)
            shutil.copy2(path, target)
            pdfs.append(target)
        elif suffix == ".zip":
            extract_dir = job_dir / "unzipped" / path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path) as zf:
                zf.extractall(extract_dir)
            for pdf in extract_dir.rglob("*.pdf"):
                target = pdf_dir / f"{uuid.uuid4().hex}_{safe_filename(pdf.name)}"
                shutil.copy2(pdf, target)
                pdfs.append(target)
        else:
            issues.append(IssueRecord(id=uuid.uuid4().hex, nodeId="X3", title="지원하지 않는 파일 형식", detail=f"{path.name}은 PDF/ZIP이 아닙니다.", severity="critical"))
    return pdfs, issues


def read_first_page_text(path: Path) -> tuple[str, int]:
    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        text = reader.pages[0].extract_text() if page_count else ""
        return text or "", page_count
    except Exception:
        return "", 0


def make_asset(path: Path, original_name: str, first_text: str, page_count: int) -> PdfAsset:
    return PdfAsset(
        id=uuid.uuid4().hex,
        originalName=original_name,
        storedPath=str(path),
        pageCount=page_count,
        firstPageText=first_text,
        sizeBytes=path.stat().st_size if path.exists() else 0,
    )
