"use client";
import { useMemo, useState } from "react";
import { Upload, ShieldCheck, FileArchive, Play, Trash2 } from "lucide-react";
import type { ConsentState, OutputMode } from "@/lib/types";

interface Props {
  busy: boolean;
  onSubmit: (data: { files: File[]; subject: string; grade: string; outputMode: OutputMode; consent: ConsentState }) => void;
}

const emptyConsent: ConsentState = { aiOcrProcessing: false, personalDataRisk: false, storageRetention: false };

export default function UploadWizard({ busy, onSubmit }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [subject, setSubject] = useState("수학");
  const [grade, setGrade] = useState("고1");
  const [outputMode, setOutputMode] = useState<OutputMode>("primary");
  const [consent, setConsent] = useState<ConsentState>(emptyConsent);
  const allConsent = consent.aiOcrProcessing && consent.personalDataRisk && consent.storageRetention;
  const canSubmit = files.length > 0 && subject.trim() && allConsent && !busy;
  const totalSize = useMemo(() => files.reduce((sum, f) => sum + f.size, 0), [files]);

  function addFiles(list: FileList | null) {
    if (!list) return;
    const next = [...files, ...Array.from(list)].filter((file, idx, arr) => arr.findIndex(f => f.name === file.name && f.size === file.size) === idx);
    setFiles(next);
  }

  return (
    <section className="panel stack">
      <div className="section-title"><Upload size={18}/><span>1. 업로드 및 동의</span></div>
      <label className="dropzone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); addFiles(e.dataTransfer.files); }}>
        <FileArchive size={26}/>
        <strong>PDF 또는 ZIP을 드래그하거나 선택</strong>
        <span>여러 시험지를 한 번에 넣을 수 있습니다. 브라우저에서는 파일명과 크기만 먼저 확인합니다.</span>
        <input type="file" multiple accept=".pdf,.zip,application/pdf,application/zip" onChange={e => addFiles(e.target.files)} />
      </label>
      {files.length > 0 && <div className="file-list">
        <div className="file-list-head"><span>{files.length}개 파일</span><span>{(totalSize/1024/1024).toFixed(1)} MB</span></div>
        {files.map(file => <div className="file-row" key={`${file.name}-${file.size}`}><span>{file.name}</span><span>{(file.size/1024/1024).toFixed(1)} MB</span></div>)}
        <button className="ghost danger" onClick={() => setFiles([])}><Trash2 size={14}/> 목록 비우기</button>
      </div>}
      <div className="form-grid">
        <label>과목<input value={subject} onChange={e => setSubject(e.target.value)} placeholder="수학, 통합과학, 물리학Ⅰ" /></label>
        <label>학년<select value={grade} onChange={e => setGrade(e.target.value)}><option>중1</option><option>중2</option><option>중3</option><option>고1</option><option>고2</option><option>고3</option></select></label>
        <label>배치 방식<select value={outputMode} onChange={e => setOutputMode(e.target.value as OutputMode)}><option value="primary">주단원 기준</option><option value="secondary-duplicate">보조단원 중복 포함</option></select></label>
      </div>
      <div className="consent-card">
        <div className="section-title"><ShieldCheck size={17}/><span>필수 확인</span></div>
        <label><input type="checkbox" checked={consent.personalDataRisk} onChange={e => setConsent(c => ({ ...c, personalDataRisk: e.target.checked }))}/> 개인정보, 필기, 채점 흔적이 포함될 수 있음을 확인했습니다.</label>
        <label><input type="checkbox" checked={consent.aiOcrProcessing} onChange={e => setConsent(c => ({ ...c, aiOcrProcessing: e.target.checked }))}/> AI/OCR 서버 처리에 동의합니다.</label>
        <label><input type="checkbox" checked={consent.storageRetention} onChange={e => setConsent(c => ({ ...c, storageRetention: e.target.checked }))}/> 저장 기간과 삭제 가능 여부 안내를 확인했습니다.</label>
      </div>
      <button className="primary" disabled={!canSubmit} onClick={() => onSubmit({ files, subject, grade, outputMode, consent })}><Play size={16}/>{busy ? "업로드 중" : "분석 시작"}</button>
    </section>
  );
}
