from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field

WorkflowStatus = Literal["pending", "running", "completed", "failed", "skipped", "needs_review"]
JobStatus = Literal["queued", "running", "needs_review", "failed", "completed", "cancelled"]
PdfRole = Literal["question", "answer", "combined", "unknown"]
OutputMode = Literal["primary", "secondary-duplicate"]
IssueSeverity = Literal["info", "warning", "critical"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConsentState(BaseModel):
    aiOcrProcessing: bool = False
    personalDataRisk: bool = False
    storageRetention: bool = False


class WorkflowNode(BaseModel):
    id: str
    label: str
    shape: Literal["process", "decision"] = "process"
    group: str = "기타"


class WorkflowStepState(WorkflowNode):
    status: WorkflowStatus = "pending"
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    message: Optional[str] = None


class CurriculumUnit(BaseModel):
    id: str
    level: Literal["major", "middle", "minor"]
    title: str
    subjectArea: Literal["math", "science"]
    keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    children: list["CurriculumUnit"] = Field(default_factory=list)


class ExamMetadata(BaseModel):
    schoolName: str = "미확인 학교"
    schoolYear: str = "미확인 학년도"
    grade: str = "미확인 학년"
    semester: str = "미확인 학기"
    examName: str = "미확인 시험"
    subjectName: str = "미확인 과목"
    normalizedSubjectName: str = "미확인 과목"


class PageRange(BaseModel):
    start: int = 1
    end: int = 1


class PdfAsset(BaseModel):
    id: str
    originalName: str
    storedPath: str
    role: PdfRole = "unknown"
    confidence: float = 0
    pageCount: int = 0
    questionRange: Optional[PageRange] = None
    answerRange: Optional[PageRange] = None
    firstPageText: Optional[str] = None
    standardizedName: Optional[str] = None
    sizeBytes: int = 0


class AnswerRecord(BaseModel):
    examId: str
    questionNumber: int
    answer: str
    raw: str


class QuestionRecord(BaseModel):
    examId: str
    questionId: str
    questionNumber: int
    sourcePdfId: str
    sourceName: str
    pageNumber: int
    cropPath: Optional[str] = None
    ocrText: Optional[str] = None
    primaryUnitId: Optional[str] = None
    secondaryUnitIds: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    tagConfidence: float = 0
    answer: Optional[str] = None
    isLong: bool = False
    quality: dict = Field(default_factory=dict)


class IssueRecord(BaseModel):
    id: str
    nodeId: str
    title: str
    detail: str
    severity: IssueSeverity = "warning"
    autoFixable: bool = False
    resolved: bool = False
    resolution: Optional[str] = None
    createdAt: str = Field(default_factory=now_iso)


class JobInput(BaseModel):
    subject: str
    grade: str
    outputMode: OutputMode = "primary"
    consent: ConsentState
    uploadIds: list[str] = Field(default_factory=list)


class JobResult(BaseModel):
    finalPdfPath: Optional[str] = None
    previewPath: Optional[str] = None
    downloadReady: bool = False


class JobSnapshot(BaseModel):
    id: str
    status: JobStatus = "queued"
    createdAt: str = Field(default_factory=now_iso)
    updatedAt: str = Field(default_factory=now_iso)
    progress: int = 0
    input: JobInput
    waitingFor: Optional[str] = None
    steps: list[WorkflowStepState] = Field(default_factory=list)
    assets: list[PdfAsset] = Field(default_factory=list)
    metadata: Optional[ExamMetadata] = None
    curriculum: list[CurriculumUnit] = Field(default_factory=list)
    questions: list[QuestionRecord] = Field(default_factory=list)
    answers: list[AnswerRecord] = Field(default_factory=list)
    issues: list[IssueRecord] = Field(default_factory=list)
    result: JobResult = Field(default_factory=JobResult)
    error: Optional[str] = None


class MetadataPatch(BaseModel):
    metadata: ExamMetadata


class AssetPatch(BaseModel):
    role: Optional[PdfRole] = None
    questionRange: Optional[PageRange] = None
    answerRange: Optional[PageRange] = None
    confidence: Optional[float] = None


class ContinueRequest(BaseModel):
    action: Literal["continue", "auto_fix", "regenerate_partial"] = "continue"
    note: str = ""


class ResolveIssueRequest(BaseModel):
    resolution: str = "사용자가 확인함"
