export type WorkflowStatus = "pending" | "running" | "completed" | "failed" | "skipped" | "needs_review";
export type JobStatus = "queued" | "running" | "needs_review" | "failed" | "completed" | "cancelled";
export type PdfRole = "question" | "answer" | "combined" | "unknown";
export type OutputMode = "primary" | "secondary-duplicate";

export interface ConsentState {
  aiOcrProcessing: boolean;
  personalDataRisk: boolean;
  storageRetention: boolean;
}
export interface WorkflowNode { id: string; label: string; shape: "process" | "decision"; group: string; }
export interface WorkflowStepState extends WorkflowNode { status: WorkflowStatus; startedAt?: string; completedAt?: string; message?: string; }
export interface CurriculumUnit { id: string; level: "major" | "middle" | "minor"; title: string; subjectArea: "math" | "science"; curriculumRevision: string; course: string; status: "active" | "new" | "transferred" | "removed"; sourceNote?: string; requiresConfirmation: boolean; keywords: string[]; tags: string[]; children: CurriculumUnit[]; }
export interface ExamMetadata { schoolName: string; schoolYear: string; grade: string; semester: string; examName: string; subjectName: string; normalizedSubjectName: string; }
export interface PageRange { start: number; end: number; }
export interface PdfAsset { id: string; originalName: string; storedPath: string; role: PdfRole; confidence: number; pageCount: number; questionRange?: PageRange; answerRange?: PageRange; firstPageText?: string; standardizedName?: string; sizeBytes: number; }
export interface AnswerRecord { examId: string; questionNumber: number; answer: string; raw: string; }
export interface QuestionRecord { examId: string; questionId: string; questionNumber: number; sourcePdfId: string; sourceName: string; pageNumber: number; cropPath?: string; ocrText?: string; primaryUnitId?: string; secondaryUnitIds: string[]; tags: string[]; tagConfidence: number; answer?: string; isLong: boolean; quality: Record<string, unknown>; }
export interface IssueRecord { id: string; nodeId: string; title: string; detail: string; severity: "info" | "warning" | "critical"; autoFixable: boolean; resolved: boolean; resolution?: string; context: Record<string, unknown>; createdAt: string; }
export interface JobInput { subject: string; grade: string; outputMode: OutputMode; consent: ConsentState; uploadIds: string[]; }
export interface JobResult { finalPdfPath?: string; previewPath?: string; downloadReady: boolean; }
export interface JobSnapshot { id: string; status: JobStatus; createdAt: string; updatedAt: string; progress: number; input: JobInput; waitingFor?: string; steps: WorkflowStepState[]; assets: PdfAsset[]; metadata?: ExamMetadata; curriculum: CurriculumUnit[]; questions: QuestionRecord[]; answers: AnswerRecord[]; issues: IssueRecord[]; result: JobResult; error?: string; }
export interface PublicConfig { appEnv: string; reviewPolicy: string; confidenceThreshold: number; retentionDays: number; maxUploadMb: number; workflowNodeCount: number; nim: { baseUrl: string; hasApiKey: boolean; models: { text: string; vision: string; ocr: string; metadata: string; tagger: string; qa: string } } }
