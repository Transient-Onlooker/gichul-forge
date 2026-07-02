"use client";
import { useEffect, useRef } from "react";
import mermaid from "mermaid";

export default function MermaidDiagram({ source }: { source: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let mounted = true;
    mermaid.initialize({ startOnLoad: false, theme: "base", securityLevel: "loose", flowchart: { curve: "basis", htmlLabels: true } });
    mermaid.render(`mermiad-${Date.now()}`, source).then(({ svg }) => { if (mounted && ref.current) ref.current.innerHTML = svg; });
    return () => { mounted = false; };
  }, [source]);
  return <div className="mermaid-wrap" ref={ref}/>;
}
