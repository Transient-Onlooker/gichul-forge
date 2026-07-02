"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Circle, Clock3, Search, XCircle } from "lucide-react";
import type { JobSnapshot, WorkflowNode, WorkflowStatus } from "@/lib/types";

function statusIcon(status: WorkflowStatus) {
  if (status === "completed") return <CheckCircle2 size={15} />;
  if (status === "running") return <Clock3 size={15} />;
  if (status === "needs_review") return <AlertTriangle size={15} />;
  if (status === "failed") return <XCircle size={15} />;
  return <Circle size={15} />;
}

export default function StatusTimeline({ job, nodes }: { job: JobSnapshot | null; nodes: WorkflowNode[] }) {
  const [filter, setFilter] = useState("");
  const steps = job?.steps ?? nodes.map((node) => ({ ...node, status: "pending" as const, message: undefined }));

  const groups = useMemo(() => {
    const out = new Map<string, typeof steps>();
    for (const step of steps.filter((item) => `${item.id} ${item.label} ${item.group}`.toLowerCase().includes(filter.toLowerCase()))) {
      out.set(step.group, [...(out.get(step.group) ?? []), step]);
    }
    return Array.from(out.entries());
  }, [filter, steps]);

  const counts = useMemo(
    () => ({
      completed: steps.filter((step) => step.status === "completed" || step.status === "skipped").length,
      running: steps.filter((step) => step.status === "running").length,
      review: steps.filter((step) => step.status === "needs_review").length,
      failed: steps.filter((step) => step.status === "failed").length,
    }),
    [steps],
  );

  return (
    <div className="stack">
      <div className="toolbar">
        <div className="search">
          <Search size={14} />
          <input placeholder="단계 검색: OCR, curriculum, finalize..." value={filter} onChange={(e) => setFilter(e.target.value)} />
        </div>
        <div className="status-strip">
          <span className="pill success">완료 {counts.completed}</span>
          <span className="pill info">진행 {counts.running}</span>
          <span className="pill warning">검수 {counts.review}</span>
          <span className="pill danger">실패 {counts.failed}</span>
        </div>
      </div>

      {groups.length === 0 && <div className="empty">검색 조건과 일치하는 단계가 없습니다.</div>}

      <div className="timeline-groups">
        {groups.map(([group, items]) => (
          <details open key={group} className="node-group">
            <summary>
              <span>{group}</span>
              <span>
                {items.filter((item) => item.status === "completed" || item.status === "skipped").length}/{items.length}
              </span>
            </summary>
            <div className="nodes">
              {items.map((step) => (
                <div className={`node ${step.status}`} key={step.id}>
                  <div className="node-icon">{statusIcon(step.status)}</div>
                  <div className="node-copy">
                    <div className="node-head">
                      <strong>{step.id}</strong>
                      <span>{step.label}</span>
                    </div>
                    <p>{step.message ?? "대기 중"}</p>
                  </div>
                </div>
              ))}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
