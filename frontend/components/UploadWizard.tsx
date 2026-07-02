"use client";

import { useMemo, useState } from "react";
import { FileArchive, Play, RotateCcw, ShieldCheck, Trash2, Upload } from "lucide-react";
import type { ConsentState, OutputMode } from "@/lib/types";

interface Props {
  busy: boolean;
  activeJobId?: string | null;
  maxUploadMb?: number;
  onClearActiveJob: () => void;
  onSubmit: (data: { files: File[]; subject: string; outputMode: OutputMode; consent: ConsentState }) => void;
}

const emptyConsent: ConsentState = {
  aiOcrProcessing: false,
  personalDataRisk: false,
  storageRetention: false,
};

const subjectPresets = [
  { value: "공통수학1", description: "다항식, 방정식과 부등식, 경우의 수, 행렬" },
  { value: "공통수학2", description: "도형의 방정식, 집합과 명제, 함수와 그래프" },
  { value: "통합과학1", description: "과학의 기초, 물질과 규칙성, 시스템과 상호작용" },
  { value: "통합과학2", description: "변화와 다양성, 환경과 에너지, 과학과 미래 사회" },
];

export default function UploadWizard({ busy, activeJobId, maxUploadMb, onClearActiveJob, onSubmit }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [subject, setSubject] = useState("공통수학1");
  const [outputMode, setOutputMode] = useState<OutputMode>("primary");
  const [consent, setConsent] = useState<ConsentState>(emptyConsent);

  const allConsent = consent.aiOcrProcessing && consent.personalDataRisk && consent.storageRetention;
  const totalSizeMb = useMemo(() => files.reduce((sum, file) => sum + file.size, 0) / 1024 / 1024, [files]);
  const oversized = typeof maxUploadMb === "number" && totalSizeMb > maxUploadMb;
  const canSubmit = files.length > 0 && allConsent && !busy && !oversized;

  function addFiles(list: FileList | null) {
    if (!list) return;
    const next = [...files, ...Array.from(list)].filter(
      (file, idx, arr) => arr.findIndex((target) => target.name === file.name && target.size === file.size) === idx,
    );
    setFiles(next);
  }

  return (
    <section className="panel stack">
      <div className="panel-head">
        <div className="section-title">
          <Upload size={18} />
          <span>업로드 설정</span>
        </div>
        <p className="section-copy">기출 PDF 또는 ZIP을 올리면 업로드 직후 작업 ID가 생성되고 파이프라인이 시작됩니다.</p>
      </div>

      {activeJobId && (
        <div className="resume-card">
          <div>
            <strong>이전 작업 이어보기</strong>
            <p>새로고침해도 마지막 작업 ID를 기억합니다. 완전히 새로 시작하려면 아래 버튼으로 초기화하세요.</p>
          </div>
          <button className="ghost" type="button" onClick={onClearActiveJob}>
            <RotateCcw size={15} />
            <span>현재 작업 초기화</span>
          </button>
        </div>
      )}

      <label
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          addFiles(e.dataTransfer.files);
        }}
      >
        <FileArchive size={24} />
        <strong>PDF 또는 ZIP을 끌어놓거나 클릭해서 선택</strong>
        <span>여러 파일을 한 번에 넣을 수 있습니다. 브라우저에서는 파일명과 크기만 먼저 확인합니다.</span>
        <div className="drop-meta">
          <span className="pill">허용 형식: .pdf, .zip</span>
          <span className="pill">중복 파일 자동 제거</span>
          {typeof maxUploadMb === "number" && <span className="pill">최대 {maxUploadMb}MB</span>}
        </div>
        <input type="file" multiple accept=".pdf,.zip,application/pdf,application/zip" onChange={(e) => addFiles(e.target.files)} />
      </label>

      <div className="stack">
        <div className="panel-head">
          <div className="section-title">
            <span>대상 과목</span>
          </div>
          <p className="section-copy">22개정 기준 과목만 선택합니다. 예전 기출문제라도 최종 배치 대상은 여기서 고른 과목입니다.</p>
        </div>
        <div className="quick-picks">
          {subjectPresets.map((item) => (
            <button
              key={item.value}
              type="button"
              className={subject === item.value ? "quick-pill active" : "quick-pill"}
              onClick={() => setSubject(item.value)}
              title={item.description}
            >
              {item.value}
            </button>
          ))}
        </div>
      </div>

      {files.length > 0 && (
        <div className="file-list">
          <div className="file-list-head">
            <span>{files.length}개 파일</span>
            <span>{totalSizeMb.toFixed(1)} MB</span>
          </div>
          {files.map((file) => (
            <div className="file-row" key={`${file.name}-${file.size}`}>
              <span>{file.name}</span>
              <span>{(file.size / 1024 / 1024).toFixed(1)} MB</span>
            </div>
          ))}
          <button className="ghost danger" type="button" onClick={() => setFiles([])}>
            <Trash2 size={14} />
            <span>목록 비우기</span>
          </button>
        </div>
      )}

      {oversized && <div className="issue warning">총 업로드 용량이 제한을 넘었습니다. 파일을 줄이거나 나눠서 올리세요.</div>}

      <div className="form-grid">
        <label>
          선택된 과목
          <input value={subject} readOnly />
        </label>
        <label>
          배치 방식
          <select value={outputMode} onChange={(e) => setOutputMode(e.target.value as OutputMode)}>
            <option value="primary">주단원 기준</option>
            <option value="secondary-duplicate">보조단원 중복 포함</option>
          </select>
        </label>
      </div>

      <div className="consent-card">
        <div className="section-title">
          <ShieldCheck size={17} />
          <span>처리 동의</span>
        </div>
        <div className="consent-list">
          <label>
            <input
              type="checkbox"
              checked={consent.personalDataRisk}
              onChange={(e) => setConsent((current) => ({ ...current, personalDataRisk: e.target.checked }))}
            />
            <span>개인정보, 필기, 채점 흔적이 포함될 수 있음을 확인했습니다.</span>
          </label>
          <label>
            <input
              type="checkbox"
              checked={consent.aiOcrProcessing}
              onChange={(e) => setConsent((current) => ({ ...current, aiOcrProcessing: e.target.checked }))}
            />
            <span>AI OCR 및 분류 처리를 위한 서버 전송에 동의합니다.</span>
          </label>
          <label>
            <input
              type="checkbox"
              checked={consent.storageRetention}
              onChange={(e) => setConsent((current) => ({ ...current, storageRetention: e.target.checked }))}
            />
            <span>보관 기간과 삭제 가능 여부를 확인했습니다.</span>
          </label>
        </div>
      </div>

      <button className="primary" type="button" disabled={!canSubmit} onClick={() => onSubmit({ files, subject, outputMode, consent })}>
        <Play size={16} />
        <span>{busy ? "업로드 중" : "분석 시작"}</span>
      </button>
    </section>
  );
}
