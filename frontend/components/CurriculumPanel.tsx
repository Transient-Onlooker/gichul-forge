"use client";

import type { CurriculumUnit } from "@/lib/types";

export default function CurriculumPanel({ units }: { units: CurriculumUnit[] }) {
  if (!units.length) {
    return <div className="empty">교육과정 데이터가 아직 로드되지 않았습니다.</div>;
  }

  return (
    <div className="stack">
      <div className="subpanel">
        <div className="panel-head">
          <div className="section-title">
            <span>2022 개정 단원 트리</span>
          </div>
          <p className="section-copy">신설 단원과 이동 단원은 상태 배지로 표시됩니다.</p>
        </div>
      </div>
      {units.map((unit) => (
        <Unit key={unit.id} unit={unit} />
      ))}
    </div>
  );
}

function Unit({ unit }: { unit: CurriculumUnit }) {
  const keywords = Array.from(new Set(unit.keywords)).filter(Boolean);

  return (
    <details open className={`unit ${unit.level}`}>
      <summary className="unit-summary">
        <strong>{unit.title}</strong>
        {unit.level !== "major" && <span>{unit.course}</span>}
        {unit.status !== "active" && (
          <span className={`status-chip ${unit.status}`}>
            {unit.status === "new" ? "신설" : unit.status === "transferred" ? "이동" : "제외"}
          </span>
        )}
        {unit.requiresConfirmation && <span className="status-chip transferred">확인 필요</span>}
      </summary>
      {unit.sourceNote && <p className="muted">{unit.sourceNote}</p>}
      <div className="tags">
        {keywords.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
      {unit.children?.map((child) => (
        <Unit key={child.id} unit={child} />
      ))}
    </details>
  );
}
