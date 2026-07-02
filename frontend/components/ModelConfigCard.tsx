"use client";
import { Cpu, KeyRound, Server } from "lucide-react";
import type { PublicConfig } from "@/lib/types";

export default function ModelConfigCard({ config }: { config: PublicConfig | null }) {
  const models = config?.nim.models;
  return <section className="panel stack">
    <div className="section-title"><Cpu size={18}/><span>모델/서버 설정</span></div>
    <div className="kv"><Server size={14}/><span>Base URL</span><b>{config?.nim.baseUrl ?? "-"}</b></div>
    <div className="kv"><KeyRound size={14}/><span>API Key</span><b>{config?.nim.hasApiKey ? "설정됨" : "미설정"}</b></div>
    <div className="model-grid">
      {models && Object.entries(models).map(([key, value]) => <div className="model-cell" key={key}><span>{key}</span><strong>{value}</strong></div>)}
    </div>
    <p className="muted">모델명은 `.env.local`에서 역할별로 변경합니다. 변경 후 백엔드를 재시작하세요.</p>
  </section>;
}
