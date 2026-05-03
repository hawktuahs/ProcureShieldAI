import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProcureShield AI — AI-Powered Procurement Evaluation",
  description: "AI-Based Tender Evaluation and Eligibility Analysis for Government Procurement",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50">
        <header className="bg-[#1e3a5f] text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold tracking-tight">ProcureShield AI</h1>
              <p className="text-blue-300 text-xs mt-0.5">AI-Powered Procurement Evaluation System</p>
            </div>
            <div className="text-xs text-blue-200 text-right">
              <div>CRPF / AI for Bharat</div>
              <div className="text-blue-400">Government Procurement Platform</div>
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-6 py-6">{children}</main>
        <footer className="border-t border-slate-200 mt-12 py-4 text-center text-xs text-slate-400">
          ProcureShield AI — For official use only. All decisions subject to human review and approval.
        </footer>
      </body>
    </html>
  );
}
