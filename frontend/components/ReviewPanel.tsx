"use client";
import { useState } from "react";
import { AlertTriangle, Check, FileCheck2, Save } from "lucide-react";
import type { ExamMetadata, JobSnapshot, PdfAsset, PdfRole } from "@/lib/types";
import { continueJob, finalizeJob, patchAsset, patchMetadata, resolveIssue } from "@/lib/api";

export default function ReviewPanel({ job, refresh }: { job: JobSnapshot | null; refresh: () => void }) {
  const [saving, setSaving] = useState(false);
  if (!job) return <div className="empty">작업을 시작하면 메타데이터, PDF 역할, 검수 이슈가 여기에 표시됩니다.</div>;
  async function saveMetadata(meta: ExamMetadata) {
    if (!job) return;
    setSaving(true); await patchMetadata(job.id, meta); setSaving(false); refresh();
  }
  async function saveAsset(asset: PdfAsset) {
    if (!job) return;
    setSaving(true); await patchAsset(job.id, asset.id, { role: asset.role, questionRange: asset.questionRange, answerRange: asset.answerRange, confidence: asset.confidence }); setSaving(false); refresh();
  }
  return <div className="stack">
    {job.metadata && <MetadataEditor metadata={job.metadata} onSave={saveMetadata} saving={saving}/>} 
    <section className="subpanel stack"><div className="section-title"><FileCheck2 size={17}/><span>PDF 역할/페이지 범위</span></div>{job.assets.map(asset => <AssetEditor key={asset.id} asset={asset} onSave={saveAsset} saving={saving}/>)}</section>
    <section className="subpanel stack"><div className="section-title"><AlertTriangle size={17}/><span>Issue Queue</span></div>{job.issues.length === 0 && <p className="muted">등록된 이슈가 없습니다.</p>}{job.issues.map(issue => <div className={`issue ${issue.severity}`} key={issue.id}><div><strong>{issue.nodeId} · {issue.title}</strong><p>{issue.detail}</p><small>{issue.resolved ? `해결됨: ${issue.resolution}` : issue.autoFixable ? "자동 수정 가능" : "사용자 확인 필요"}</small></div>{!issue.resolved && <button className="ghost" onClick={async () => { await resolveIssue(job.id, issue.id); refresh(); }}><Check size={14}/> 해결 처리</button>}</div>)}</section>
    <div className="action-bar">
      {job.waitingFor === "E16" && <button className="primary" onClick={async () => { await continueJob(job.id); refresh(); }}><Check size={16}/> 역할/메타데이터 확정 후 계속</button>}
      {job.waitingFor === "S2" && <button className="primary" onClick={async () => { await finalizeJob(job.id); refresh(); }}><Check size={16}/> 최종 확인 및 다운로드 활성화</button>}
    </div>
  </div>;
}

function MetadataEditor({ metadata, onSave, saving }: { metadata: ExamMetadata; onSave: (m: ExamMetadata) => void; saving: boolean }) {
  const [m, setM] = useState(metadata);
  const keys: (keyof ExamMetadata)[] = ["schoolName", "schoolYear", "grade", "semester", "examName", "subjectName", "normalizedSubjectName"];
  const labels: Record<keyof ExamMetadata, string> = { schoolName: "학교명", schoolYear: "학년도", grade: "학년", semester: "학기", examName: "시험명", subjectName: "과목명", normalizedSubjectName: "정규화 과목명" };
  return <section className="subpanel stack"><div className="section-title"><Save size={17}/><span>메타데이터 확인</span></div><div className="form-grid">{keys.map(k => <label key={k}>{labels[k]}<input value={m[k]} onChange={e => setM({ ...m, [k]: e.target.value })}/></label>)}</div><button className="secondary" disabled={saving} onClick={() => onSave(m)}>메타데이터 저장</button></section>;
}

function AssetEditor({ asset, onSave, saving }: { asset: PdfAsset; onSave: (a: PdfAsset) => void; saving: boolean }) {
  const [a, setA] = useState(asset);
  const setRole = (role: PdfRole) => setA({ ...a, role });
  return <div className="asset-editor"><div><strong>{asset.originalName}</strong><p>{asset.pageCount}p · confidence {(asset.confidence*100).toFixed(0)}% · {asset.standardizedName}</p></div><div className="asset-controls"><select value={a.role} onChange={e => setRole(e.target.value as PdfRole)}><option value="question">문제지</option><option value="answer">답지</option><option value="combined">합본</option><option value="unknown">불명확</option></select><label>문제 시작<input type="number" value={a.questionRange?.start ?? 1} onChange={e => setA({ ...a, questionRange: { start: Number(e.target.value), end: a.questionRange?.end ?? a.pageCount } })}/></label><label>문제 끝<input type="number" value={a.questionRange?.end ?? a.pageCount} onChange={e => setA({ ...a, questionRange: { start: a.questionRange?.start ?? 1, end: Number(e.target.value) } })}/></label><label>답 시작<input type="number" value={a.answerRange?.start ?? 1} onChange={e => setA({ ...a, answerRange: { start: Number(e.target.value), end: a.answerRange?.end ?? a.pageCount } })}/></label><label>답 끝<input type="number" value={a.answerRange?.end ?? a.pageCount} onChange={e => setA({ ...a, answerRange: { start: a.answerRange?.start ?? 1, end: Number(e.target.value) } })}/></label><button className="secondary" disabled={saving} onClick={() => onSave(a)}>저장</button></div></div>;
}
