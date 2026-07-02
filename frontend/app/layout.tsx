import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MERMIAD",
  description: "기출 PDF를 2022 개정 교육과정 기준 단원 문제집으로 정리하는 작업 대시보드",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
