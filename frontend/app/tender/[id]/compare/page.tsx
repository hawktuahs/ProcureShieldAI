"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getCompareData, getReportUrl, CompareData, VERDICT_LABEL, TYPE_COLOR } from "@/lib/api";
import { ArrowLeft, Download, Loader2 } from "lucide-react";

const VERDICT_CELL_COLOR: Record<string, string> = {
  pass: "bg-green-500 text-white",
  fail: "bg-red-500 text-white",
  needs_review: "bg-amber-500 text-white",
  eligible: "bg-green-500 text-white",
  not_eligible: "bg-red-500 text-white",
};

export default function ComparePage() {
  const { id } = useParams<{ id: string }>();
  const tenderId = parseInt(id);

  const [data, setData] = useState<CompareData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCompareData(tenderId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tenderId]);

  if (loading) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>;
  }
  if (!data) {
    return <div className="py-20 text-center text-slate-500">Could not load comparison data.</div>;
  }

  const evaluatedBidders = data.matrix.filter((b) => b.status === "evaluated");

  // Summary counts
  const eligible = evaluatedBidders.filter((b) => b.overall_verdict === "eligible").length;
  const notEligible = evaluatedBidders.filter((b) => b.overall_verdict === "not_eligible").length;
  const needsReview = evaluatedBidders.filter((b) => b.overall_verdict === "needs_review").length;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4 text-sm text-slate-500">
        <Link href="/" className="hover:text-slate-700">Dashboard</Link>
        <span className="text-slate-300">/</span>
        <Link href={`/tender/${tenderId}`} className="hover:text-slate-700">{data.tender.name}</Link>
        <span className="text-slate-300">/</span>
        <span className="text-slate-700 font-medium">Compare</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Bidder Comparison Matrix</h2>
          <p className="text-sm text-slate-500 mt-0.5">{data.tender.name}</p>
        </div>
        <a
          href={getReportUrl(tenderId)}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 bg-[#1e3a5f] text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors shadow-sm"
        >
          <Download className="w-4 h-4" /> Export Full Report (PDF)
        </a>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Eligible", count: eligible, color: "bg-green-50 border-green-200 text-green-700" },
          { label: "Not Eligible", count: notEligible, color: "bg-red-50 border-red-200 text-red-700" },
          { label: "Needs Review", count: needsReview, color: "bg-amber-50 border-amber-200 text-amber-700" },
        ].map((s) => (
          <div key={s.label} className={`border rounded-xl p-4 text-center ${s.color}`}>
            <p className="text-3xl font-bold">{s.count}</p>
            <p className="text-sm font-medium mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Matrix */}
      {evaluatedBidders.length === 0 ? (
        <div className="text-center py-12 text-slate-400">No evaluated bidders yet.</div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="text-xs">
              <thead>
                <tr className="bg-[#1e3a5f] text-white">
                  <th className="text-left px-4 py-3 font-semibold min-w-[160px] sticky left-0 bg-[#1e3a5f] z-10">Bidder</th>
                  <th className="text-center px-3 py-3 font-semibold min-w-[100px]">Overall</th>
                  {data.criteria.map((c) => (
                    <th key={c.id} className="px-2 py-3 font-medium min-w-[90px] text-center">
                      <div className="flex flex-col items-center gap-1">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${TYPE_COLOR[c.criterion_type] || ""} text-center leading-tight`}>
                          {c.criterion_type.slice(0, 4).toUpperCase()}
                        </span>
                        <span className="leading-tight text-[10px] max-w-[80px] text-center break-words font-normal text-blue-100">
                          {c.description.slice(0, 40)}{c.description.length > 40 ? "…" : ""}
                        </span>
                        {c.is_mandatory && (
                          <span className="text-red-300 text-[9px]">mandatory</span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {evaluatedBidders.map((row, i) => (
                  <tr key={row.bidder_id} className={i % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                    <td className="px-4 py-3 sticky left-0 bg-inherit z-10 border-r border-slate-100">
                      <Link
                        href={`/evaluation/${tenderId}/${row.bidder_id}`}
                        className="font-medium text-slate-800 hover:text-blue-600 hover:underline"
                      >
                        {row.bidder_name}
                      </Link>
                    </td>
                    <td className="px-3 py-3 text-center">
                      <span className={`inline-block px-2 py-1 rounded-full text-[10px] font-bold ${VERDICT_CELL_COLOR[row.overall_verdict || ""] || "bg-slate-200 text-slate-600"}`}>
                        {VERDICT_LABEL[row.overall_verdict || ""] || "—"}
                      </span>
                    </td>
                    {data.criteria.map((c) => {
                      const cell = row.criteria[c.id];
                      const effective = cell?.human_verdict || cell?.verdict;
                      const isOverridden = cell?.human_verdict && cell.human_verdict !== cell.verdict;
                      return (
                        <td key={c.id} className="px-2 py-3 text-center">
                          {effective ? (
                            <div className="flex flex-col items-center gap-0.5">
                              <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${VERDICT_CELL_COLOR[effective] || "bg-slate-200"}`}>
                                {effective === "needs_review" ? "REV" : effective === "pass" ? "P" : "F"}
                              </span>
                              {cell?.confidence != null && (
                                <span className="text-[9px] text-slate-400">{Math.round(cell.confidence * 100)}%</span>
                              )}
                              {isOverridden && <span className="text-[9px] text-blue-500">★</span>}
                            </div>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="border-t border-slate-100 px-4 py-3 flex items-center gap-4 text-xs text-slate-500">
            <span className="font-medium text-slate-600">Legend:</span>
            <span className="flex items-center gap-1"><span className="bg-green-500 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">P</span> Pass</span>
            <span className="flex items-center gap-1"><span className="bg-red-500 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">F</span> Fail</span>
            <span className="flex items-center gap-1"><span className="bg-amber-500 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">REV</span> Needs Review</span>
            <span className="flex items-center gap-1"><span className="text-blue-500">★</span> Human Override</span>
          </div>
        </div>
      )}
    </div>
  );
}
