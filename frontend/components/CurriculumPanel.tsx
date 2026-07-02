"use client";
import type { CurriculumUnit } from "@/lib/types";

export default function CurriculumPanel({ units }: { units: CurriculumUnit[] }) {
  if (!units.length) return <div className="empty">교육과정은 과목 검증 후 로드됩니다.</div>;
  return <div className="stack">{units.map(unit => <Unit key={unit.id} unit={unit}/>)}</div>;
}
function Unit({ unit }: { unit: CurriculumUnit }) {
  return <details open className={`unit ${unit.level}`}><summary><strong>{unit.title}</strong><span>{unit.id}</span></summary><div className="tags">{[...unit.keywords, ...unit.tags].map(t => <span key={t}>{t}</span>)}</div>{unit.children?.map(child => <Unit key={child.id} unit={child}/>)}</details>;
}
