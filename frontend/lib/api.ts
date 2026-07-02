import type { ExamMetadata, JobSnapshot, PublicConfig } from "@/lib/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { ...options, cache: "no-store" });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getConfig() { return request<PublicConfig>("/api/config"); }
export function getJob(id: string) { return request<JobSnapshot>(`/api/jobs/${id}`); }
export function getCurriculum(subject: string, grade: string) { return request<{ units: unknown[] }>(`/api/curriculum?subject=${encodeURIComponent(subject)}&grade=${encodeURIComponent(grade)}`); }

export async function createJob(input: { files: File[]; subject: string; grade: string; outputMode: string; consent: { aiOcrProcessing: boolean; personalDataRisk: boolean; storageRetention: boolean } }) {
  const form = new FormData();
  input.files.forEach(file => form.append("files", file));
  form.append("subject", input.subject);
  form.append("grade", input.grade);
  form.append("outputMode", input.outputMode);
  form.append("aiOcrProcessing", String(input.consent.aiOcrProcessing));
  form.append("personalDataRisk", String(input.consent.personalDataRisk));
  form.append("storageRetention", String(input.consent.storageRetention));
  return request<{ jobId: string }>("/api/jobs", { method: "POST", body: form });
}

export function patchMetadata(jobId: string, metadata: ExamMetadata) {
  return request<JobSnapshot>(`/api/jobs/${jobId}/metadata`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ metadata }) });
}

export type AssetPatch = Partial<Pick<import("@/lib/types").PdfAsset, "role" | "questionRange" | "answerRange" | "confidence">>;
export function patchAsset(jobId: string, assetId: string, patch: AssetPatch) {
  return request<JobSnapshot>(`/api/jobs/${jobId}/assets/${assetId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
}

export function continueJob(jobId: string) {
  return request<{ ok: boolean }>(`/api/jobs/${jobId}/continue`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "continue" }) });
}

export function finalizeJob(jobId: string) {
  return request<JobSnapshot>(`/api/jobs/${jobId}/finalize`, { method: "POST" });
}

export function resolveIssue(jobId: string, issueId: string, resolution = "확인 완료") {
  return request<JobSnapshot>(`/api/jobs/${jobId}/issues/${issueId}/resolve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ resolution }) });
}

export function downloadUrl(jobId: string) { return `${API_BASE}/api/jobs/${jobId}/download`; }
