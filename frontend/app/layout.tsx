import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MERMIAD",
  description: "기출 PDF를 단원별 모음집으로 자동 재구성"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
