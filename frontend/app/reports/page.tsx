"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, FileText, ArrowLeft } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function ReportsPage() {
  const [tenders, setTenders] = useState<{ id: number; name: string; bidder_count: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/tenders")
      .then(r => r.json())
      .then(data => setTenders(data.filter((t: any) => t.status === "ready")))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Reports</h1>
        <p className="text-sm text-slate-500 mt-0.5">Download comparative evaluation reports for ready tenders</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      ) : tenders.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-slate-200 rounded-xl bg-white text-slate-400">
          <FileText className="w-10 h-10 mx-auto mb-3 text-slate-300" />
          <p className="font-medium">No evaluated tenders yet</p>
          <p className="text-sm mt-1">Upload a tender and evaluate bidders to generate reports.</p>
          <Link href="/" className="mt-4 inline-flex items-center gap-1.5 text-sm text-blue-600 hover:underline">
            <ArrowLeft className="w-4 h-4" /> Go to Dashboard
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {tenders.map(t => (
            <Card key={t.id} className="border border-slate-200 hover:shadow-sm transition-all">
              <CardContent className="px-5 py-4 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-800 line-clamp-1">{t.name}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{t.bidder_count} bidder{t.bidder_count !== 1 ? "s" : ""} evaluated</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    href={`/tender/${t.id}/compare`}
                    className="text-sm font-medium text-blue-600 hover:text-blue-800 border border-blue-200 bg-blue-50 px-3 py-1.5 rounded-lg hover:bg-blue-100 transition-colors"
                  >
                    View Comparison
                  </Link>
                  <a
                    href={`/api/tenders/${t.id}/report`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium text-white bg-[#1e3a5f] hover:bg-blue-800 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    Download Report
                  </a>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
