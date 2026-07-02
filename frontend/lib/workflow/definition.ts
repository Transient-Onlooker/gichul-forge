import type { WorkflowNode } from "@/lib/types";

const groups: [string, string][] = [
  ["A", "동의/업로드"], ["B", "과목/교육과정"], ["C", "파일 분석"], ["D", "메타데이터"], ["E", "PDF 역할"], ["F", "PDF 분리"], ["G", "OCR/답지"], ["H", "단원 태깅"], ["I", "문항 추출"], ["J", "이미지 품질"], ["K", "문항 ID"], ["L", "정렬/배치"], ["M", "문제 PDF"], ["N", "답지 PDF"], ["O", "표지"], ["P", "목차"], ["Q", "병합"], ["R", "최종 검수"], ["S", "최종 확인"], ["X", "종료/오류"]
];

function groupFor(id: string) {
  if (id === "STATUS") return "상태 패널";
  return groups.find(([prefix]) => id.startsWith(prefix))?.[1] ?? "기타";
}

export function parseWorkflowNodes(source: string): WorkflowNode[] {
  const seen = new Set<string>();
  const nodes: WorkflowNode[] = [];
  const regexp = /\b([A-Z]+\d*|STATUS)\s*(\[|\{)"([^"]+)"(?:\]|\})/g;
  let match: RegExpExecArray | null;
  while ((match = regexp.exec(source))) {
    const [, id, open, label] = match;
    if (seen.has(id)) continue;
    seen.add(id);
    nodes.push({ id, label, shape: open === "{" ? "decision" : "process", group: groupFor(id) });
  }
  return nodes;
}
