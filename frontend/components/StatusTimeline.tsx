"use client";
import { useMemo, useState } from "react";
import { CheckCircle2, Circle, Clock3, XCircle, AlertTriangle, Search } from "lucide-react";
import type { JobSnapshot, WorkflowNode, WorkflowStatus } from "@/lib/types";

function icon(status: WorkflowStatus) {
  if (status === "completed") return <CheckCircle2 size={15}/>;
  if (status === "running") return <Clock3 size={15}/>;
  if (status === "needs_review") return <AlertTriangle size={15}/>;
  if (status === "failed") return <XCircle size={15}/>;
  return <Circle size={15}/>;
}

export default function StatusTimeline({ job, nodes }: { job: JobSnapshot | null; nodes: WorkflowNode[] }) {
  const [filter, setFilter] = useState("");
  const steps = job?.steps ?? nodes.map(n => ({ ...n, status: "pending" as const, message: undefined }));
  const groups = useMemo(() => {
    const out = new Map<string, typeof steps>();
    for (const step of steps.filter(s => `${s.id} ${s.label} ${s.group}`.toLowerCase().includes(filter.toLowerCase()))) {
      out.set(step.group, [...(out.get(step.group) ?? []), step]);
    }
    return Array.from(out.entries());
  }, [steps, filter]);
  const completed = steps.filter(s => s.status === "completed" || s.status === "skipped").length;
  return <div className="stack">
    <div className="toolbar"><div className="search"><Search size={14}/><input placeholder="노드 검색: H2, OCR, 목차..." value={filter} onChange={e => setFilter(e.target.value)} /></div><span className="pill">{completed}/{steps.length} 반영</span></div>
    <div className="timeline-groups">
      {groups.map(([group, items]) => <details open key={group} className="node-group"><summary>{group}<span>{items.filter(i => i.status === "completed" || i.status === "skipped").length}/{items.length}</span></summary>
        <div className="nodes">
          {items.map(step => <div className={`node ${step.status}`} key={step.id}><div className="node-icon">{icon(step.status)}</div><div><strong>{step.id}</strong> {step.label}<p>{step.message ?? "대기"}</p></div></div>)}
        </div>
      </details>)}
    </div>
  </div>;
}
