import type { Metadata } from "next";
import "./globals.css";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";
import SidebarNav from "@/components/SidebarNav";

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

export const metadata: Metadata = {
  title: "ProcureShield AI — AI-Powered Procurement Evaluation",
  description: "AI-Based Tender Evaluation and Eligibility Analysis for Government Procurement",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn("font-sans", inter.variable)}>
      <body className="min-h-screen bg-[#f8fafc] flex">
        <SidebarNav />
        {/* Main area */}
        <div className="flex-1 flex flex-col min-w-0">
          <main className="flex-1 px-6 py-6 overflow-auto">
            {children}
          </main>
          <footer className="border-t border-slate-200 py-3 px-6 text-xs text-slate-400 bg-white shrink-0">
            ProcureShield AI — For official use only. All decisions subject to human review and approval.
          </footer>
        </div>
      </body>
    </html>
  );
}
