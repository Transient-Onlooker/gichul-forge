"use client";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Download, RefreshCw, Sparkles } from "lucide-react";
import UploadWizard from "@/components/UploadWizard";
import ModelConfigCard from "@/components/ModelConfigCard";
import StatusTimeline from "@/components/StatusTimeline";
import ReviewPanel from "@/components/ReviewPanel";
import CurriculumPanel from "@/components/CurriculumPanel";
import MermaidDiagram from "@/components/MermaidDiagram";
import { createJob, downloadUrl, getConfig, getCurriculum, getJob } from "@/lib/api";
import type { CurriculumUnit, JobSnapshot, PublicConfig } from "@/lib/types";
import { MERMIAD_MERMAID_SOURCE } from "@/lib/workflow/mermaidSource";
import { parseWorkflowNodes } from "@/lib/workflow/definition";

export default function Home() {
  const nodes = useMemo(() => parseWorkflowNodes(MERMIAD_MERMAID_SOURCE), []);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [job, setJob] = useState<JobSnapshot | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"status" | "review" | "curriculum" | "graph">("status");
  const [curriculum, setCurriculum] = useState<CurriculumUnit[]>([]);

  const refresh = async () => { if (jobId) setJob(await getJob(jobId)); };

  useEffect(() => { getConfig().then(setConfig).catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (!jobId) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let stop = false;
    const poll = async () => {
      try {
        const next = await getJob(jobId);
        setJob(next);
        if (["queued", "running"].includes(next.status) && !stop) timer = setTimeout(poll, 1300);
      } catch (e) { setError(e instanceof Error ? e.message : "상태 조회 실패"); }
    };
    poll();
    return () => { stop = true; if (timer) clearTimeout(timer); };
  }, [jobId]);
  useEffect(() => {
    const subject = job?.input.subject ?? "수학";
    const grade = job?.input.grade ?? "고1";
    getCurriculum(subject, grade).then(data => setCurriculum(data.units as CurriculumUnit[])).catch(() => setCurriculum([]));
  }, [job?.input.subject, job?.input.grade]);

  return <main className="page">
    <section className="hero panel">
      <div>
        <div className="eyebrow"><Sparkles size={16}/> MERMIAD Service v2</div>
        <h1>기출 PDF를 단원별 문제 모음집으로 재구성</h1>
        <p>업로드 동의부터 OCR, 문항 추출, 단원 태깅, 답지 재정렬, 최종 검수까지 Mermaid 161개 노드를 Python 백엔드 파이프라인과 UX 상태 패널에 연결했습니다.</p>
        <div className="hero-actions"><span className="pill">Frontend: React/TypeScript</span><span className="pill">Backend: Python/FastAPI</span><span className="pill">NIM models: env configurable</span></div>
      </div>
      <div className="score-card"><span>진행률</span><strong>{job?.progress ?? 0}%</strong><div className="progress"><div style={{ width: `${job?.progress ?? 0}%` }}/></div><small>상태: {job?.status ?? "대기"} {job?.waitingFor ? `· 대기 노드 ${job.waitingFor}` : ""}</small>{job?.result.downloadReady && <a className="primary" href={downloadUrl(job.id)}><Download size={16}/> 최종 PDF 다운로드</a>}</div>
    </section>
    {error && <div className="issue critical"><AlertTriangle size={16}/>{error}</div>}
    <section className="layout">
      <aside className="left stack">
        <UploadWizard busy={busy} onSubmit={async data => { setBusy(true); setError(null); try { const res = await createJob(data); setJobId(res.jobId); setTab("status"); } catch (e) { setError(e instanceof Error ? e.message : "업로드 실패"); } finally { setBusy(false); } }}/>
        <ModelConfigCard config={config}/>
      </aside>
      <section className="workspace panel">
        <div className="tabs"><button className={tab === "status" ? "active" : ""} onClick={() => setTab("status")}>상태 패널</button><button className={tab === "review" ? "active" : ""} onClick={() => setTab("review")}>확인/수정</button><button className={tab === "curriculum" ? "active" : ""} onClick={() => setTab("curriculum")}>교육과정</button><button className={tab === "graph" ? "active" : ""} onClick={() => setTab("graph")}>Mermaid 원문</button><button className="ghost" onClick={refresh}><RefreshCw size={14}/> 새로고침</button></div>
        {tab === "status" && <StatusTimeline job={job} nodes={nodes}/>} 
        {tab === "review" && <ReviewPanel job={job} refresh={refresh}/>} 
        {tab === "curriculum" && <CurriculumPanel units={job?.curriculum?.length ? job.curriculum : curriculum}/>} 
        {tab === "graph" && <MermaidDiagram source={MERMIAD_MERMAID_SOURCE}/>} 
      </section>
    </section>
  </main>;
}
