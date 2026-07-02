"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Check, FileCheck2, Save } from "lucide-react";
import type { ExamMetadata, IssueRecord, JobSnapshot, PdfAsset, PdfRole } from "@/lib/types";
import { continueJob, finalizeJob, patchAsset, patchMetadata, resolveIssue } from "@/lib/api";

export default function ReviewPanel({ job, refresh }: { job: JobSnapshot | null; refresh: () => void }) {
  const [saving, setSaving] = useState(false);

  if (!job) {
    return <div className="empty">작업을 시작하면 메타데이터, PDF 역할, 검수 이슈가 여기 표시됩니다.</div>;
  }

  const currentJob = job;
  const unresolvedCurriculum = currentJob.issues.some(
    (issue) => issue.context?.type === "curriculum_confirmation" && !issue.resolved,
  );
  const sortedIssues = useMemo(
    () => [...currentJob.issues].sort((a, b) => Number(a.resolved) - Number(b.resolved)),
    [currentJob.issues],
  );

  async function saveMetadata(metadata: ExamMetadata) {
    setSaving(true);
    await patchMetadata(currentJob.id, metadata);
    setSaving(false);
    refresh();
  }

  async function saveAsset(asset: PdfAsset) {
    setSaving(true);
    await patchAsset(currentJob.id, asset.id, {
      role: asset.role,
      questionRange: asset.questionRange,
      answerRange: asset.answerRange,
      confidence: asset.confidence,
    });
    setSaving(false);
    refresh();
  }

  return (
    <div className="stack">
      <section className="review-summary">
        <div className="review-summary-card">
          <span>열린 이슈</span>
          <strong>{currentJob.issues.filter((issue) => !issue.resolved).length}</strong>
        </div>
        <div className="review-summary-card">
          <span>업로드 파일</span>
          <strong>{currentJob.assets.length}</strong>
        </div>
        <div className="review-summary-card">
          <span>대기 단계</span>
          <strong>{currentJob.waitingFor ?? "없음"}</strong>
        </div>
      </section>

      {currentJob.metadata && <MetadataEditor metadata={currentJob.metadata} onSave={saveMetadata} saving={saving} />}

      <section className="subpanel stack">
        <div className="panel-head">
          <div className="section-title">
            <FileCheck2 size={17} />
            <span>PDF 역할과 페이지 범위</span>
          </div>
          <p className="section-copy">문제지, 답지, 혼합본 구분이 잘못되었으면 여기서 바로 수정할 수 있습니다.</p>
        </div>
        {currentJob.assets.map((asset) => (
          <AssetEditor key={asset.id} asset={asset} onSave={saveAsset} saving={saving} />
        ))}
      </section>

      <section className="subpanel stack">
        <div className="panel-head">
          <div className="section-title">
            <AlertTriangle size={17} />
            <span>검수 이슈</span>
          </div>
          <p className="section-copy">자동 분류가 애매한 항목이나 교육과정 이동 단원 확인 요청이 이곳에 쌓입니다.</p>
        </div>
        {sortedIssues.length === 0 && <p className="muted">현재 열린 이슈가 없습니다.</p>}
        {sortedIssues.map((issue) => (
          <IssueItem key={issue.id} jobId={currentJob.id} issue={issue} refresh={refresh} />
        ))}
      </section>

      <div className="action-bar">
        {currentJob.waitingFor === "E16" && (
          <button
            className="primary"
            disabled={unresolvedCurriculum}
            onClick={async () => {
              await continueJob(currentJob.id);
              refresh();
            }}
          >
            <Check size={16} />
            <span>검수 완료 후 계속</span>
          </button>
        )}
        {currentJob.waitingFor === "S2" && (
          <button
            className="primary"
            onClick={async () => {
              await finalizeJob(currentJob.id);
              refresh();
            }}
          >
            <Check size={16} />
            <span>최종 PDF 생성</span>
          </button>
        )}
      </div>

      {currentJob.waitingFor === "E16" && unresolvedCurriculum && (
        <p className="muted">2022 개정에서 이동된 단원은 포함 여부를 먼저 선택해야 합니다.</p>
      )}
    </div>
  );
}

function IssueItem({ jobId, issue, refresh }: { jobId: string; issue: IssueRecord; refresh: () => void }) {
  const isCurriculum = issue.context?.type === "curriculum_confirmation";
  const unitId = String(issue.context?.unitId || "");

  return (
    <div className={`issue ${issue.severity}`}>
      <div className="issue-copy">
        <strong>
          {issue.nodeId} · {issue.title}
        </strong>
        <p>{issue.detail}</p>
        <small>{issue.resolved ? `해결됨: ${issue.resolution}` : issue.autoFixable ? "자동 수정 가능" : "사용자 확인 필요"}</small>
      </div>

      {!issue.resolved && isCurriculum && (
        <div className="inline-actions">
          <button
            className="secondary"
            onClick={async () => {
              await resolveIssue(jobId, issue.id, `include_unit:${unitId}`);
              refresh();
            }}
          >
            <Check size={14} />
            <span>포함</span>
          </button>
          <button
            className="ghost"
            onClick={async () => {
              await resolveIssue(jobId, issue.id, `exclude_unit:${unitId}`);
              refresh();
            }}
          >
            <span>제외하고 진행</span>
          </button>
        </div>
      )}

      {!issue.resolved && !isCurriculum && (
        <button
          className="ghost"
          onClick={async () => {
            await resolveIssue(jobId, issue.id);
            refresh();
          }}
        >
          <Check size={14} />
          <span>확인 완료</span>
        </button>
      )}
    </div>
  );
}

function MetadataEditor({
  metadata,
  onSave,
  saving,
}: {
  metadata: ExamMetadata;
  onSave: (metadata: ExamMetadata) => void;
  saving: boolean;
}) {
  const [draft, setDraft] = useState(metadata);
  const keys: (keyof ExamMetadata)[] = [
    "schoolName",
    "schoolYear",
    "grade",
    "semester",
    "examName",
    "subjectName",
    "normalizedSubjectName",
  ];
  const labels: Record<keyof ExamMetadata, string> = {
    schoolName: "학교명",
    schoolYear: "학년도",
    grade: "학년",
    semester: "학기",
    examName: "시험명",
    subjectName: "원본 과목명",
    normalizedSubjectName: "정규화 과목명",
  };

  return (
    <section className="subpanel stack">
      <div className="panel-head">
        <div className="section-title">
          <Save size={17} />
          <span>메타데이터 확인</span>
        </div>
        <p className="section-copy">학교명, 학기, 과목 정규화 결과가 어색하면 최종 생성 전에 수정하세요.</p>
      </div>
      <div className="form-grid">
        {keys.map((key) => (
          <label key={key}>
            {labels[key]}
            <input value={draft[key]} onChange={(e) => setDraft({ ...draft, [key]: e.target.value })} />
          </label>
        ))}
      </div>
      <button className="secondary" disabled={saving} onClick={() => onSave(draft)}>
        메타데이터 저장
      </button>
    </section>
  );
}

function AssetEditor({ asset, onSave, saving }: { asset: PdfAsset; onSave: (asset: PdfAsset) => void; saving: boolean }) {
  const [draft, setDraft] = useState(asset);
  const setRole = (role: PdfRole) => setDraft({ ...draft, role });

  return (
    <div className="asset-editor">
      <div className="asset-summary">
        <strong>{asset.originalName}</strong>
        <p>
          {asset.pageCount}p · confidence {(asset.confidence * 100).toFixed(0)}% · {asset.standardizedName}
        </p>
      </div>
      <div className="asset-controls">
        <select value={draft.role} onChange={(e) => setRole(e.target.value as PdfRole)}>
          <option value="question">문제지</option>
          <option value="answer">답지</option>
          <option value="combined">혼합본</option>
          <option value="unknown">미분류</option>
        </select>
        <label>
          문제 시작
          <input
            type="number"
            value={draft.questionRange?.start ?? 1}
            onChange={(e) =>
              setDraft({
                ...draft,
                questionRange: { start: Number(e.target.value), end: draft.questionRange?.end ?? asset.pageCount },
              })
            }
          />
        </label>
        <label>
          문제 끝
          <input
            type="number"
            value={draft.questionRange?.end ?? asset.pageCount}
            onChange={(e) =>
              setDraft({
                ...draft,
                questionRange: { start: draft.questionRange?.start ?? 1, end: Number(e.target.value) },
              })
            }
          />
        </label>
        <label>
          답지 시작
          <input
            type="number"
            value={draft.answerRange?.start ?? 1}
            onChange={(e) =>
              setDraft({
                ...draft,
                answerRange: { start: Number(e.target.value), end: draft.answerRange?.end ?? asset.pageCount },
              })
            }
          />
        </label>
        <label>
          답지 끝
          <input
            type="number"
            value={draft.answerRange?.end ?? asset.pageCount}
            onChange={(e) =>
              setDraft({
                ...draft,
                answerRange: { start: draft.answerRange?.start ?? 1, end: Number(e.target.value) },
              })
            }
          />
        </label>
        <button className="secondary" disabled={saving} onClick={() => onSave(draft)}>
          저장
        </button>
      </div>
    </div>
  );
}
