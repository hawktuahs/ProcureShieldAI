"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getCompareData, getReportUrl, CompareData, VERDICT_LABEL, TYPE_COLOR } from "@/lib/api";
import { ArrowLeft, Download, Loader2, ShieldAlert, GitMerge, FileText, BarChart2, TableIcon } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, Cell,
} from "recharts";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const VERDICT_CELL_COLOR: Record<string, string> = {
  pass: "bg-green-50 text-green-700 border-green-200",
  fail: "bg-red-50 text-red-700 border-red-200",
  needs_review: "bg-amber-50 text-amber-700 border-amber-200",
  eligible: "bg-green-100 text-green-800 border-green-300",
  not_eligible: "bg-red-100 text-red-800 border-red-300",
};

const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316"];

type FilterType = "ALL" | "QUALIFIED" | "FAILED" | "REVIEW";
type ViewMode = "table" | "chart";

export default function ComparePage() {
  const { id } = useParams<{ id: string }>();
  const tenderId = parseInt(id);

  const [data, setData] = useState<CompareData | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("ALL");
  const [viewMode, setViewMode] = useState<ViewMode>("chart");

  useEffect(() => {
    getCompareData(tenderId)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tenderId]);

  if (loading) {
    return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 animate-spin text-slate-400" /></div>;
  }
  if (!data) {
    return <div className="py-20 text-center text-slate-500">Could not load comparison data.</div>;
  }

  const allEvaluated = data.matrix.filter((b) => b.status === "evaluated");

  const filteredBidders = allEvaluated.filter(b => {
    if (filter === "QUALIFIED") return b.overall_verdict === "eligible";
    if (filter === "FAILED") return b.overall_verdict === "not_eligible";
    if (filter === "REVIEW") return b.overall_verdict === "needs_review";
    return true;
  });

  // ── Chart data ─────────────────────────────────────────────────────────────

  // Bar chart: pass rate per bidder
  const barData = allEvaluated.map(b => {
    const evals = Object.values(b.criteria);
    const total = evals.length;
    const pass = evals.filter(e => (e.human_verdict || e.verdict) === "pass").length;
    const fail = evals.filter(e => (e.human_verdict || e.verdict) === "fail").length;
    const review = evals.filter(e => (e.human_verdict || e.verdict) === "needs_review").length;
    return {
      name: b.bidder_name.length > 16 ? b.bidder_name.slice(0, 14) + "…" : b.bidder_name,
      fullName: b.bidder_name,
      pass, fail, review,
      passRate: total > 0 ? Math.round((pass / total) * 100) : 0,
      verdict: b.overall_verdict,
    };
  }).sort((a, b) => b.passRate - a.passRate);

  // Radar chart: scores by criterion type
  const typeOrder = ["financial", "technical", "compliance", "documentation"];
  const radarData = typeOrder.map(type => {
    const entry: Record<string, string | number> = { type: type.slice(0, 6) + "." };
    allEvaluated.forEach(b => {
      const evals = Object.values(b.criteria).filter((_, idx) => {
        const crit = data.criteria[idx];
        return crit?.criterion_type === type;
      });
      const pass = evals.filter(e => (e.human_verdict || e.verdict) === "pass").length;
      entry[b.bidder_name] = evals.length > 0 ? Math.round((pass / evals.length) * 100) : 0;
    });
    return entry;
  });

  const verdictSummary = {
    eligible: allEvaluated.filter(b => b.overall_verdict === "eligible").length,
    not_eligible: allEvaluated.filter(b => b.overall_verdict === "not_eligible").length,
    needs_review: allEvaluated.filter(b => b.overall_verdict === "needs_review").length,
  };

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-5 text-sm text-slate-500">
        <Link href="/" className="hover:text-slate-700 flex items-center gap-1"><ArrowLeft className="w-4 h-4" /> Dashboard</Link>
        <span className="text-slate-300">/</span>
        <Link href={`/tender/${tenderId}`} className="hover:text-slate-700">{data.tender.name}</Link>
        <span className="text-slate-300">/</span>
        <span className="text-slate-800 font-medium">Comparative Statement</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Bidder Comparison</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {allEvaluated.length} bidders evaluated · {data.criteria.length} criteria
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex bg-slate-100 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode("chart")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === "chart" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
            >
              <BarChart2 className="w-3.5 h-3.5" /> Charts
            </button>
            <button
              onClick={() => setViewMode("table")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${viewMode === "table" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
            >
              <TableIcon className="w-3.5 h-3.5" /> Matrix
            </button>
          </div>
          <a
            href={getReportUrl(tenderId)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 bg-[#1e3a5f] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors"
          >
            <Download className="w-4 h-4" /> Export Report
          </a>
        </div>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Qualified", value: verdictSummary.eligible, color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" },
          { label: "Needs Review", value: verdictSummary.needs_review, color: "text-amber-700", bg: "bg-amber-50 border-amber-200" },
          { label: "Not Eligible", value: verdictSummary.not_eligible, color: "text-red-700", bg: "bg-red-50 border-red-200" },
        ].map(({ label, value, color, bg }) => (
          <Card key={label} className={`border ${bg}`}>
            <CardContent className="p-4 flex items-center gap-3">
              <div>
                <p className={`text-3xl font-bold ${color}`}>{value}</p>
                <p className={`text-sm font-medium ${color} opacity-80`}>{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {allEvaluated.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-slate-200 rounded-xl text-slate-400 text-sm bg-white">
          No bidders have been evaluated yet.
        </div>
      ) : viewMode === "chart" ? (
        /* ── CHART VIEW ───────────────────────────────── */
        <div className="grid gap-6 grid-cols-1 xl:grid-cols-2">
          {/* Bar Chart — Pass Rate per Bidder */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-2 px-5 pt-4">
              <h2 className="text-sm font-semibold text-slate-700">Pass Rate by Bidder</h2>
              <p className="text-xs text-slate-400">Percentage of criteria passed (higher is better)</p>
            </CardHeader>
            <CardContent className="px-2 pb-4">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                  <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <YAxis dataKey="name" type="category" width={90} tick={{ fontSize: 11, fill: "#475569" }} />
                  <Tooltip
                    formatter={(v) => [`${v}%`, "Pass Rate"]}
                    labelFormatter={(l) => barData.find(d => d.name === l)?.fullName || l}
                    contentStyle={{ fontSize: 12, border: "1px solid #e2e8f0", borderRadius: 8 }}
                  />
                  <Bar dataKey="passRate" radius={[0, 4, 4, 0]} maxBarSize={28}>
                    {barData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={entry.verdict === "eligible" ? "#10b981" : entry.verdict === "not_eligible" ? "#ef4444" : "#f59e0b"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Pass / Fail / Review Stacked Bar */}
          <Card className="border border-slate-200">
            <CardHeader className="pb-2 px-5 pt-4">
              <h2 className="text-sm font-semibold text-slate-700">Criteria Breakdown</h2>
              <p className="text-xs text-slate-400">Pass, Review, and Fail counts per bidder</p>
            </CardHeader>
            <CardContent className="px-2 pb-4">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "#94a3b8" }} />
                  <YAxis dataKey="name" type="category" width={90} tick={{ fontSize: 11, fill: "#475569" }} />
                  <Tooltip contentStyle={{ fontSize: 12, border: "1px solid #e2e8f0", borderRadius: 8 }} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="pass" name="Pass" fill="#10b981" stackId="a" radius={[0, 0, 0, 0]} maxBarSize={24} />
                  <Bar dataKey="review" name="Review" fill="#f59e0b" stackId="a" maxBarSize={24} />
                  <Bar dataKey="fail" name="Fail" fill="#ef4444" stackId="a" radius={[0, 4, 4, 0]} maxBarSize={24} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Radar chart (only when ≥ 2 bidders) */}
          {allEvaluated.length >= 2 && (
            <Card className="border border-slate-200 xl:col-span-2">
              <CardHeader className="pb-2 px-5 pt-4">
                <h2 className="text-sm font-semibold text-slate-700">Performance Radar by Criterion Type</h2>
                <p className="text-xs text-slate-400">Pass rate (%) across each criterion category</p>
              </CardHeader>
              <CardContent className="pb-4">
                <ResponsiveContainer width="100%" height={320}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="type" tick={{ fontSize: 12, fill: "#64748b" }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                    {allEvaluated.slice(0, 6).map((b, i) => (
                      <Radar
                        key={b.bidder_id}
                        name={b.bidder_name}
                        dataKey={b.bidder_name}
                        stroke={CHART_COLORS[i % CHART_COLORS.length]}
                        fill={CHART_COLORS[i % CHART_COLORS.length]}
                        fillOpacity={0.08}
                        strokeWidth={2}
                      />
                    ))}
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: 12, border: "1px solid #e2e8f0", borderRadius: 8 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* Bidder ranking cards */}
          <Card className="border border-slate-200 xl:col-span-2">
            <CardHeader className="pb-2 px-5 pt-4">
              <h2 className="text-sm font-semibold text-slate-700">Bidder Ranking</h2>
              <p className="text-xs text-slate-400">Sorted by pass rate, highest first</p>
            </CardHeader>
            <CardContent className="px-5 pb-4">
              <div className="flex flex-col gap-2">
                {barData.map((b, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className="w-6 text-center text-xs font-bold text-slate-400">#{i + 1}</span>
                    <span className="w-40 text-sm text-slate-700 truncate" title={b.fullName}>{b.fullName}</span>
                    <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${b.passRate}%`,
                          background: b.verdict === "eligible" ? "#10b981" : b.verdict === "not_eligible" ? "#ef4444" : "#f59e0b",
                        }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-slate-500 w-10 text-right">{b.passRate}%</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold border ${VERDICT_CELL_COLOR[b.verdict || ""] || "bg-slate-50 text-slate-500 border-slate-200"}`}>
                      {VERDICT_LABEL[b.verdict || ""] || "PENDING"}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        /* ── TABLE VIEW ───────────────────────────────── */
        <>
          {/* Filters */}
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            {[
              { id: "ALL", label: `All (${allEvaluated.length})` },
              { id: "REVIEW", label: `Needs Review (${verdictSummary.needs_review})` },
              { id: "FAILED", label: `Failed (${verdictSummary.not_eligible})` },
              { id: "QUALIFIED", label: `Qualified (${verdictSummary.eligible})` },
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id as FilterType)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${
                  filter === f.id
                    ? "bg-[#1e3a5f] text-white border-[#1e3a5f]"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {filteredBidders.length === 0 ? (
            <div className="text-center py-20 bg-white border border-slate-200 rounded-xl text-slate-400">
              No bidders match the selected filter.
            </div>
          ) : (
            <div className="bg-white border border-slate-200 shadow-sm overflow-hidden rounded-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      <th className="bg-[#f8fafc] border-b border-r border-slate-200 p-4 min-w-[280px] sticky left-0 z-20 text-left align-bottom">
                        <div className="text-slate-400 italic mb-1 text-xs uppercase tracking-wider">Evaluation Criteria</div>
                      </th>
                      {filteredBidders.map(b => (
                        <th key={b.bidder_id} className="bg-white border-b border-r border-slate-200 p-4 min-w-[200px] align-top text-left">
                          <Link href={`/evaluation/${tenderId}/${b.bidder_id}`} className="block text-blue-700 font-bold hover:underline mb-2 truncate" title={b.bidder_name}>
                            {b.bidder_name}
                          </Link>
                          <div className="flex items-center gap-2 mt-2">
                            {b.risk_score != null && (
                              <div className="flex items-center gap-1.5">
                                <div className="h-1.5 w-16 bg-slate-100 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full ${b.risk_score < 30 ? "bg-green-500" : b.risk_score < 60 ? "bg-amber-500" : "bg-red-500"}`}
                                    style={{ width: `${b.risk_score}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-slate-500">Risk {b.risk_score}</span>
                              </div>
                            )}
                            <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${VERDICT_CELL_COLOR[b.overall_verdict || ""] || "bg-slate-100 text-slate-500 border-slate-200"}`}>
                              {VERDICT_LABEL[b.overall_verdict || ""] || "PENDING"}
                            </span>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.criteria.map((c, idx) => (
                      <tr key={c.id} className="hover:bg-blue-50/30 transition-colors">
                        <td className="bg-white border-b border-r border-slate-200 p-4 sticky left-0 z-10 align-top shadow-[4px_0_12px_-4px_rgba(0,0,0,0.05)]">
                          <div className="flex gap-2 items-start mb-1">
                            <span className="text-slate-400 text-xs font-mono mt-0.5">{idx + 1}.</span>
                            <p className="font-medium text-slate-800 text-sm leading-snug">{c.description}</p>
                          </div>
                          <div className="flex items-center gap-2 ml-5 mt-1.5">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${TYPE_COLOR[c.criterion_type] || "bg-slate-100 text-slate-600"}`}>
                              {c.criterion_type}
                            </span>
                            {c.is_mandatory && <span className="text-[10px] text-red-600 font-bold bg-red-50 px-1.5 py-0.5 rounded border border-red-100">MANDATORY</span>}
                            {c.threshold_value && <span className="text-[10px] text-slate-500 border border-slate-200 px-1.5 py-0.5 rounded bg-slate-50 truncate max-w-[100px]" title={c.threshold_value}>≥ {c.threshold_value}</span>}
                          </div>
                        </td>
                        {filteredBidders.map(b => {
                          const cell = b.criteria[c.id];
                          const effective = cell?.human_verdict || cell?.verdict;
                          const isOverridden = cell?.human_verdict && cell.human_verdict !== cell.verdict;
                          return (
                            <td key={`${b.bidder_id}-${c.id}`} className="bg-white border-b border-r border-slate-200 p-3 align-middle text-center">
                              {effective ? (
                                <div className="flex flex-col items-center gap-1">
                                  <span className={`inline-block px-2.5 py-1 rounded text-xs font-bold border ${VERDICT_CELL_COLOR[effective] || "bg-slate-100"}`}>
                                    {effective === "needs_review" ? "REVIEW" : effective === "pass" ? "PASS" : "FAIL"}
                                  </span>
                                  {cell?.confidence != null && (
                                    <span className="text-[10px] text-slate-400">
                                      {Math.round(cell.confidence * 100)}%{isOverridden && " ★"}
                                    </span>
                                  )}
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
            </div>
          )}
        </>
      )}
    </div>
  );
}
