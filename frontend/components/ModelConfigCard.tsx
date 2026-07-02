"use client";

import { Cpu, KeyRound, Server } from "lucide-react";
import type { PublicConfig } from "@/lib/types";

export default function ModelConfigCard({ config }: { config: PublicConfig | null }) {
  const models = config?.nim.models;

  return (
    <section className="panel stack">
      <div className="panel-head">
        <div className="section-title">
          <Cpu size={18} />
          <span>AI 모델 설정</span>
        </div>
        <p className="section-copy">`.env.local` 값을 읽어 현재 백엔드가 어떤 NIM 모델을 사용할지 보여줍니다.</p>
      </div>

      <div className="meta-grid">
        <div className="kv">
          <div className="kv-label">
            <Server size={14} />
            <span>Base URL</span>
          </div>
          <b>{config?.nim.baseUrl ?? "-"}</b>
        </div>
        <div className="kv">
          <div className="kv-label">
            <KeyRound size={14} />
            <span>API Key</span>
          </div>
          <b>{config?.nim.hasApiKey ? "설정됨" : "미설정"}</b>
        </div>
      </div>

      <div className="model-grid">
        {models &&
          Object.entries(models).map(([key, value]) => (
            <div className="model-cell" key={key}>
              <span>{key}</span>
              <strong>{value}</strong>
            </div>
          ))}
      </div>

      <p className="muted">모델명 변경은 `.env.local`에서 하고, 변경 후에는 백엔드를 재시작해야 반영됩니다.</p>
    </section>
  );
}
