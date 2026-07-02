"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BookOpenText,
  CheckCircle2,
  ClipboardList,
  Copy,
  Download,
  Files,
  GitBranchPlus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
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

type TabKey = "status" | "review" | "curriculum" | "graph";

const ACTIVE_JOB_KEY = "mermiad.activeJobId";

function statusLabel(status?: JobSnapshot["status"]) {
  switch (status) {
    case "queued":
      return "대기 중";
    case "running":
      return "처리 중";
    case "needs_review":
      return "검수 필요";
    case "failed":
      return "실패";
    case "completed":
      return "완료";
    case "cancelled":
      return "취소됨";
    default:
      return "작업 전";
  }
}

function waitingLabel(code?: string) {
  if (code === "E16") return "교육과정 확인";
  if (code === "S2") return "최종 검수";
  return code ?? "없음";
}

function nextAction(job: JobSnapshot | null) {
  if (!job) {
    return {
      title: "작업을 시작하세요",
      detail: "좌측에서 PDF 또는 ZIP을 올리면 자동으로 OCR과 단원 매핑이 시작됩니다.",
      tab: "status" as TabKey,
      tone: "info" as const,
    };
  }
  if (job.waitingFor === "E16") {
    return {
      title: "이동 단원 포함 여부를 먼저 정해야 합니다",
      detail: "검수 탭에서 2022 개정 이동 단원 이슈를 처리한 뒤 계속 진행할 수 있습니다.",
      tab: "review" as TabKey,
      tone: "warning" as const,
    };
  }
  if (job.waitingFor === "S2") {
    return {
      title: "최종 PDF 생성 전 마지막 확인 단계입니다",
      detail: "메타데이터와 문제지/답지 범위를 검수 탭에서 확인한 뒤 최종 생성 버튼을 누르세요.",
      tab: "review" as TabKey,
      tone: "info" as const,
    };
  }
  if (job.status === "completed") {
    return {
      title: "최종 결과가 준비되었습니다",
      detail: "다운로드 버튼으로 PDF를 받고, 필요하면 다른 자료로 새 작업을 시작하면 됩니다.",
      tab: "status" as TabKey,
      tone: "success" as const,
    };
  }
  if (job.status === "failed") {
    return {
      title: "처리가 중단되었습니다",
      detail: "상태 탭의 실패 단계와 오류 메시지를 먼저 확인하고 다시 업로드하는 편이 빠릅니다.",
      tab: "status" as TabKey,
      tone: "danger" as const,
    };
  }
  return {
    title: "자동 처리 중입니다",
    detail: "상태 탭에서 OCR, 분류, 매핑 단계가 완료되는지 확인하면 됩니다.",
    tab: "status" as TabKey,
    tone: "info" as const,
  };
}

export default function Home() {
  const nodes = useMemo(() => parseWorkflowNodes(MERMIAD_MERMAID_SOURCE), []);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [job, setJob] = useState<JobSnapshot | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("status");
  const [curriculum, setCurriculum] = useState<CurriculumUnit[]>([]);
  const [copied, setCopied] = useState(false);

  const refresh = async () => {
    if (!jobId) return;
    setJob(await getJob(jobId));
  };

  useEffect(() => {
    getConfig().then(setConfig).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    const saved = window.localStorage.getItem(ACTIVE_JOB_KEY);
    if (saved) setJobId(saved);
  }, []);

  useEffect(() => {
    if (jobId) {
      window.localStorage.setItem(ACTIVE_JOB_KEY, jobId);
    } else {
      window.localStorage.removeItem(ACTIVE_JOB_KEY);
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let stop = false;

    const poll = async () => {
      try {
        const next = await getJob(jobId);
        setJob(next);
        if (["queued", "running"].includes(next.status) && !stop) timer = setTimeout(poll, 1300);
      } catch (e) {
        setError(e instanceof Error ? e.message : "상태 조회에 실패했습니다.");
      }
    };

    poll();
    return () => {
      stop = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  useEffect(() => {
    if (job?.waitingFor === "E16" || job?.waitingFor === "S2" || job?.status === "needs_review") {
      setTab("review");
    }
  }, [job?.status, job?.waitingFor]);

  useEffect(() => {
    const subject = job?.input.subject ?? "공통수학1";
    getCurriculum(subject)
      .then((data) => setCurriculum(data.units as CurriculumUnit[]))
      .catch(() => setCurriculum([]));
  }, [job?.input.subject]);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1200);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const overview = useMemo(() => {
    const unresolvedIssues = job?.issues.filter((issue) => !issue.resolved).length ?? 0;
    const activeCurriculum = (job?.curriculum.length ? job.curriculum : curriculum).length;
    const completedSteps = job?.steps.filter((step) => step.status === "completed" || step.status === "skipped").length ?? 0;
    const totalSteps = job?.steps.length ?? nodes.length;

    return {
      unresolvedIssues,
      activeCurriculum,
      completedSteps,
      totalSteps,
      assetCount: job?.assets.length ?? 0,
      progress: job?.progress ?? 0,
    };
  }, [curriculum, job, nodes.length]);

  const action = nextAction(job);
  const curriculumUnits = job?.curriculum.length ? job.curriculum : curriculum;
  const reviewCount = job?.issues.filter((issue) => !issue.resolved).length ?? 0;

  const tabMeta: { key: TabKey; label: string; count?: string }[] = [
    { key: "status", label: "진행 현황", count: `${overview.completedSteps}/${overview.totalSteps}` },
    { key: "review", label: "검수", count: `${reviewCount}` },
    { key: "curriculum", label: "교육과정", count: `${overview.activeCurriculum}` },
    { key: "graph", label: "워크플로우" },
  ];

  async function copyJobId() {
    if (!job?.id) return;
    await navigator.clipboard.writeText(job.id);
    setCopied(true);
  }

  return (
    <main className="page">
      <section className="hero-shell">
        <div className="hero-copy">
          <div className="eyebrow">
            <Sparkles size={15} />
            <span>MERMIAD Service v2</span>
          </div>
          <h1>기출 PDF를 2022 개정 기준 단원 문제집으로 정리합니다.</h1>
          <p>업로드, OCR, 단원 배치, 검수, 최종 PDF 생성까지 한 화면에서 이어서 처리할 수 있게 정리한 작업 대시보드입니다.</p>
          <div className="hero-actions">
            <span className="pill">Frontend: React / TypeScript</span>
            <span className="pill">Backend: FastAPI</span>
            <span className="pill">NVIDIA NIM: 환경 변수로 전환</span>
          </div>
        </div>

        <div className="hero-status panel">
          <div className="status-head">
            <span className="status-label">현재 작업</span>
            <button className="ghost icon-only" onClick={refresh} aria-label="새로고침">
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="status-main">
            <strong>{overview.progress}%</strong>
            <span>{statusLabel(job?.status)}</span>
          </div>
          <div className="progress" aria-hidden="true">
            <div style={{ width: `${overview.progress}%` }} />
          </div>
          <div className="status-pairs">
            <div className="status-pair">
              <span>작업 ID</span>
              <b>{job?.id ?? "생성 전"}</b>
            </div>
            <div className="status-pair">
              <span>대기 코드</span>
              <b>{waitingLabel(job?.waitingFor)}</b>
            </div>
          </div>
          <div className="hero-inline-actions">
            <button className="ghost" onClick={copyJobId} disabled={!job?.id}>
              <Copy size={15} />
              <span>{copied ? "복사됨" : "작업 ID 복사"}</span>
            </button>
            {job?.result.downloadReady && (
              <a className="primary" href={downloadUrl(job.id)}>
                <Download size={15} />
                <span>최종 PDF 다운로드</span>
              </a>
            )}
          </div>
        </div>
      </section>

      <section className="stat-grid">
        <article className="stat-card">
          <div className="stat-icon">
            <Files size={17} />
          </div>
          <div>
            <strong>{overview.assetCount}</strong>
            <span>업로드 자산</span>
          </div>
        </article>
        <article className="stat-card">
          <div className="stat-icon">
            <ClipboardList size={17} />
          </div>
          <div>
            <strong>
              {overview.completedSteps}/{overview.totalSteps}
            </strong>
            <span>단계 완료</span>
          </div>
        </article>
        <article className="stat-card">
          <div className="stat-icon">
            <AlertTriangle size={17} />
          </div>
          <div>
            <strong>{overview.unresolvedIssues}</strong>
            <span>미해결 이슈</span>
          </div>
        </article>
        <article className="stat-card">
          <div className="stat-icon">
            <BookOpenText size={17} />
          </div>
          <div>
            <strong>{overview.activeCurriculum}</strong>
            <span>표시 중인 단원</span>
          </div>
        </article>
      </section>

      {error && (
        <div className="issue critical">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      <section className={`banner ${action.tone}`}>
        <div className="banner-copy">
          <strong>{action.title}</strong>
          <p>{action.detail}</p>
        </div>
        <button className="secondary" onClick={() => setTab(action.tab)}>
          {action.tab === "review" ? <CheckCircle2 size={15} /> : action.tab === "status" ? <ClipboardList size={15} /> : <GitBranchPlus size={15} />}
          <span>{action.tab === "review" ? "검수로 이동" : action.tab === "status" ? "상태 보기" : "확인하기"}</span>
        </button>
      </section>

      {job && (
        <section className="job-strip panel">
          <div className="job-strip-item">
            <span>과목</span>
            <strong>{job.input.subject}</strong>
          </div>
          <div className="job-strip-item">
            <span>교육과정</span>
            <strong>2022 개정</strong>
          </div>
          <div className="job-strip-item">
            <span>출력 방식</span>
            <strong>{job.input.outputMode === "primary" ? "주단원 기준" : "보조단원 중복 포함"}</strong>
          </div>
          <div className="job-strip-item">
            <span>열린 이슈</span>
            <strong>{reviewCount}건</strong>
          </div>
        </section>
      )}

      <section className="layout">
        <aside className="left stack">
          <UploadWizard
            busy={busy}
            maxUploadMb={config?.maxUploadMb}
            onClearActiveJob={() => {
              setJob(null);
              setJobId(null);
              setTab("status");
            }}
            activeJobId={job?.id ?? jobId}
            onSubmit={async (data) => {
              setBusy(true);
              setError(null);
              try {
                const res = await createJob(data);
                setJobId(res.jobId);
                setTab("status");
              } catch (e) {
                setError(e instanceof Error ? e.message : "업로드에 실패했습니다.");
              } finally {
                setBusy(false);
              }
            }}
          />
          <ModelConfigCard config={config} />
        </aside>

        <section className="workspace panel">
          <div className="workspace-head">
            <div>
              <h2>작업 영역</h2>
              <p>진행 상황 확인, 수동 검수, 2022 개정 교육과정 배치를 이 영역에서 처리합니다.</p>
            </div>
            <div className="tabs" role="tablist" aria-label="작업 탭">
              {tabMeta.map((item) => (
                <button
                  key={item.key}
                  className={tab === item.key ? "active" : ""}
                  onClick={() => setTab(item.key)}
                  role="tab"
                  aria-selected={tab === item.key}
                >
                  {item.key === "status" && <ClipboardList size={15} />}
                  {item.key === "review" && <CheckCircle2 size={15} />}
                  {item.key === "curriculum" && <BookOpenText size={15} />}
                  {item.key === "graph" && <GitBranchPlus size={15} />}
                  <span>{item.label}</span>
                  {item.count && <span className="tab-count">{item.count}</span>}
                </button>
              ))}
              <button className="ghost" onClick={refresh}>
                <RefreshCw size={14} />
                <span>새로고침</span>
              </button>
            </div>
          </div>

          {tab === "status" && <StatusTimeline job={job} nodes={nodes} />}
          {tab === "review" && <ReviewPanel job={job} refresh={refresh} />}
          {tab === "curriculum" && <CurriculumPanel units={curriculumUnits} />}
          {tab === "graph" && <MermaidDiagram source={MERMIAD_MERMAID_SOURCE} />}
        </section>
      </section>
    </main>
  );
}
