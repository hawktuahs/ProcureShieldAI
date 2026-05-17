import Link from "next/link";
import {
  LayoutDashboard, ShieldCheck, UploadCloud, Search, FileText,
  ArrowRight, ChevronRight, Eye, BarChart2, Zap, Lock, CheckCircle2
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function HelpPage() {
  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-[#1e3a5f] flex items-center justify-center">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">ProcureShield AI</h1>
            <p className="text-sm text-slate-500">AI-Powered Government Procurement Evaluation Platform</p>
          </div>
        </div>
        <p className="text-slate-600 text-sm leading-relaxed max-w-2xl">
          ProcureShield AI automates the extraction and evaluation of eligibility criteria from government tender documents.
          It enables procurement officers to instantly compare multiple bidders against dozens of criteria — with full AI-sourced evidence for every verdict.
        </p>
      </div>

      {/* What we do */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-slate-800 mb-4 border-b border-slate-200 pb-2">What ProcureShield Does</h2>
        <div className="grid grid-cols-3 gap-4">
          {[
            {
              icon: UploadCloud,
              title: "Automatic Extraction",
              desc: "Upload any government tender PDF. AI reads the document — even scanned image-based PDFs — and extracts all eligibility criteria, documents required, scope of work, contacts, and items."
            },
            {
              icon: ShieldCheck,
              title: "Bidder Evaluation",
              desc: "Upload a bidder's submission PDF. AI evaluates each extracted criterion against the bidder's documents, returning a PASS / FAIL / REVIEW verdict with confidence scores and source quotes."
            },
            {
              icon: BarChart2,
              title: "Comparative Analysis",
              desc: "Compare all bidders side by side in a matrix. Visual charts (bar, radar, ranking) show which bidder best meets the tender requirements at a glance."
            },
          ].map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="border border-slate-200">
              <CardContent className="pt-4 pb-4 px-4">
                <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center mb-3">
                  <Icon className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="text-sm font-semibold text-slate-800 mb-1.5">{title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* How to use — step by step */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-slate-800 mb-4 border-b border-slate-200 pb-2">How to Use the Platform</h2>
        <div className="flex flex-col gap-3">
          {[
            {
              step: 1, title: "Upload a Tender Document",
              desc: "Click Upload Tender on the Dashboard. Drop in a government tender PDF (e.g., GeM/CPP portal NIT). The AI will extract criteria in ~30–60 seconds."
            },
            {
              step: 2, title: "Review Extracted Analysis",
              desc: "Click View Tender to open the analysis. Check Overview, Documents, Eligibility, Scope of Work, Items & Qty tabs. Click any 👁 pg.N badge to jump the PDF viewer to the source page and see the exact AI evidence quote."
            },
            {
              step: 3, title: "Upload Bidder Submissions",
              desc: "Scroll below the analysis workspace. Upload each bidder's response PDF. Evaluation runs automatically in the background."
            },
            {
              step: 4, title: "Review Bidder Evaluation",
              desc: "Click a bidder card to open the full audit matrix. Each criterion shows a PASS / FAIL / REVIEW verdict with the extracted evidence and AI reasoning."
            },
            {
              step: 5, title: "Compare All Bidders",
              desc: "Click Compare All from the tender page. Switch between Charts view (bar + radar + ranking) and Matrix view to see which bidder best meets the tender."
            },
            {
              step: 6, title: "Export Report",
              desc: "Click Export Report to download the full comparative statement as a formatted report for audit and approval records."
            },
          ].map(({ step, title, desc }) => (
            <div key={step} className="flex gap-4 bg-white border border-slate-200 rounded-xl px-5 py-4">
              <div className="w-7 h-7 rounded-full bg-[#1e3a5f] text-white text-sm font-bold flex items-center justify-center shrink-0 mt-0.5">
                {step}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-800">{title}</p>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Key features */}
      <section className="mb-10">
        <h2 className="text-lg font-bold text-slate-800 mb-4 border-b border-slate-200 pb-2">Key Features</h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            { icon: Eye, label: "Source-linked Evidence", desc: "Every AI extraction links back to the exact PDF page and verbatim quote." },
            { icon: Zap, label: "OCR Support for Scanned PDFs", desc: "Works with both text-native and image-scanned government tender PDFs." },
            { icon: Lock, label: "Cryptographic Audit Trail", desc: "All AI verdicts and human overrides are logged in an immutable ledger." },
            { icon: CheckCircle2, label: "Human Override", desc: "Evaluators can override any AI verdict with a reason, and it propagates to reports." },
          ].map(({ icon: Icon, label, desc }) => (
            <div key={label} className="flex gap-3 bg-slate-50 border border-slate-100 rounded-xl px-4 py-3.5">
              <Icon className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-slate-700">{label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Quick links */}
      <div className="bg-[#1e3a5f] rounded-xl px-6 py-5 flex items-center justify-between">
        <div>
          <p className="text-white font-semibold">Ready to get started?</p>
          <p className="text-blue-300 text-sm mt-0.5">Upload your first tender to begin automated analysis.</p>
        </div>
        <Link href="/" className="flex items-center gap-2 bg-white text-[#1e3a5f] px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-50 transition-colors">
          Go to Dashboard <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
