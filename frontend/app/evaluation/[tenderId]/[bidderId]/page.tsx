"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getBidder, getBidderFileUrl, BidderDetail, CriterionEvaluation, TYPE_COLOR, VERDICT_LABEL } from "@/lib/api";
import VerdictBadge from "@/components/VerdictBadge";
import ConfidenceBar from "@/components/ConfidenceBar";
import ReviewPanel from "@/components/ReviewPanel";
import SplitWorkspace, { useProvenance } from "@/components/SplitWorkspace";
import { ArrowLeft, Download, Loader2, ClipboardCheck, ShieldAlert, FileText, Eye } from "lucide-react";

function EvaluationContent() {
  const { tenderId, bidderId } = useParams<{ tenderId: string; bidderId: string }>();
  const tId = parseInt(tenderId);
  const bId = parseInt(bidderId);

  const [bidder, setBidder] = useState<BidderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState<CriterionEvaluation | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<Record<number, boolean>>({});
  const [filterVerdict, setFilterVerdict] = useState<string>("ALL");
  const [filterType, setFilterType] = useState<string>("ALL");

  const toggleEvidence = (id: number) => setExpandedEvidence((p) => ({ ...p, [id]: !p[id] }));

  const { openProvenance } = useProvenance();

  const fetchBidder = useCallback(async () => {
    try {
      const res = await getBidder(tId, bId);
      setBidder(res.data);
    } catch {}
  }, [tId, bId]);

  useEffect(() => {
    fetchBidder().finally(() => setLoading(false));
    const interval = setInterval(() => {
      if (bidder?.status !== "evaluated") fetchBidder();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchBidder, bidder?.status]);

  const handleReviewSaved = async () => {
    await fetchBidder();
    setReviewing(null);
  };

  const uniqueTypes = Array.from(new Set(bidder?.criteria_evaluations.map(ce => ce.criterion.criterion_type) || []));

  const filteredEvaluations = bidder?.criteria_evaluations.filter(ce => {
    const { criterion, evaluation } = ce;
    const effectiveVerdict = evaluation?.human_verdict || evaluation?.verdict;
    
    if (filterVerdict !== "ALL" && effectiveVerdict !== filterVerdict) return false;
    if (filterType !== "ALL" && criterion.criterion_type !== filterType) return false;
    return true;
  }) || [];

  if (loading) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>;
  }
  if (!bidder) {
    return <div className="py-20 text-center text-slate-500">Bidder not found.</div>;
  }

  return (
    
      <div className="max-w-[1200px] mx-auto pb-10">
        {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4 text-sm text-slate-500">
        <Link href="/" className="hover:text-slate-700">Dashboard</Link>
        <span className="text-slate-300">/</span>
        <Link href={`/tender/${tId}`} className="hover:text-slate-700">Tender</Link>
        <span className="text-slate-300">/</span>
        <span className="text-slate-700 font-medium truncate">{bidder.name}</span>
      </div>

      {/* Header bar / Executive Summary */}
      <div className="bg-white border border-slate-200 rounded-xl mb-6 shadow-sm overflow-hidden">
        <div className="bg-[#1e3a5f] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-white/10 p-2 rounded-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{bidder.name}</h2>
              <p className="text-blue-200 text-sm">Bidder Submission Evaluation</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <a
              href={`http://localhost:8000/api/tenders/${tId}/report`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 bg-white text-[#1e3a5f] px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-50 transition-colors shadow"
            >
              <Download className="w-4 h-4" /> Export Report
            </a>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Status & Verdict */}
          <div className="border-r border-slate-100 pr-6">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Overall Verdict</h3>
            {bidder.status === "processing" ? (
              <span className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200 w-fit">
                <Loader2 className="w-4 h-4 animate-spin" /> Evaluating...
              </span>
            ) : (
              <VerdictBadge verdict={bidder.overall_verdict} size="lg" />
            )}
            
            {bidder.risk_score != null && (
              <div className="mt-5">
                <div className="flex items-center justify-between mb-1.5">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5" /> Risk Profile
                  </h3>
                  <span className={`text-sm font-bold ${
                    bidder.risk_score < 30 ? "text-green-600" :
                    bidder.risk_score < 60 ? "text-amber-600" : "text-red-600"
                  }`}>{bidder.risk_score} / 100</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${
                      bidder.risk_score < 30 ? "bg-green-500" :
                      bidder.risk_score < 60 ? "bg-amber-500" : "bg-red-500"
                    }`}
                    style={{ width: `${bidder.risk_score}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* AI Executive Summary */}
          <div className="md:col-span-2">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Executive Summary</h3>
            <div className="bg-slate-50 border border-slate-100 rounded-lg p-4">
              {bidder.status === "processing" ? (
                <div className="flex items-center gap-2 text-slate-400 text-sm italic">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating executive summary...
                </div>
              ) : bidder.overall_reasoning ? (
                <p className="text-sm text-slate-700 leading-relaxed">
                  {bidder.overall_reasoning}
                </p>
              ) : (
                <p className="text-sm text-slate-400 italic">No summary generated.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Evaluation table */}
      {bidder.status === "processing" ? (
        <div className="text-center py-16 text-slate-400 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin" />
          <p>Evaluating criteria against bidder documents...</p>
          <p className="text-xs">This may take 1–2 minutes depending on the number of criteria</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-4 bg-white p-3 border border-slate-200 rounded-xl shadow-sm">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Type:</label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="text-sm border-slate-200 rounded-md py-1.5 px-3 bg-slate-50 border outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="ALL">All Types</option>
                {uniqueTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Verdict:</label>
              <select
                value={filterVerdict}
                onChange={(e) => setFilterVerdict(e.target.value)}
                className="text-sm border-slate-200 rounded-md py-1.5 px-3 bg-slate-50 border outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="ALL">All Verdicts</option>
                <option value="pass">Pass</option>
                <option value="fail">Fail</option>
                <option value="needs_review">Needs Review</option>
              </select>
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#1e3a5f] text-white text-xs">
                  <th className="text-left px-4 py-3 font-semibold w-8">#</th>
                  <th className="text-left px-4 py-3 font-semibold min-w-[200px]">Criterion</th>
                  <th className="text-left px-4 py-3 font-semibold w-28">Type</th>
                  <th className="text-left px-4 py-3 font-semibold w-16">M?</th>
                  <th className="text-left px-4 py-3 font-semibold min-w-[140px]">Extracted Value</th>
                  <th className="text-left px-4 py-3 font-semibold w-28">Verdict</th>
                  <th className="text-left px-4 py-3 font-semibold w-28">Confidence</th>
                  <th className="text-left px-4 py-3 font-semibold min-w-[200px]">Evidence</th>
                  <th className="text-left px-4 py-3 font-semibold w-24">Review</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvaluations.length === 0 ? (
                  <tr><td colSpan={9} className="px-4 py-8 text-center text-slate-500 text-sm">No criteria match the selected filters.</td></tr>
                ) : filteredEvaluations.map((ce, i) => {
                  const { criterion, evaluation } = ce;
                  const effective = evaluation?.human_verdict || evaluation?.verdict;
                  const rowBg = i % 2 === 0 ? "bg-white" : "bg-slate-50";
                  const isExpanded = expandedEvidence[criterion.id] || false;

                  return (
                    <tr key={criterion.id} className={`${rowBg} border-b border-slate-100 hover:bg-blue-50/30`}>
                      <td className="px-4 py-3 text-slate-400 text-xs">{i + 1}</td>
                      <td className="px-4 py-3">
                        <p className="text-xs font-medium text-slate-800 leading-snug">{criterion.description}</p>
                        {criterion.threshold_value && (
                          <p className="text-xs text-slate-400 mt-0.5">Threshold: {criterion.threshold_value}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TYPE_COLOR[criterion.criterion_type] || "bg-slate-100 text-slate-600"}`}>
                          {criterion.criterion_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium ${criterion.is_mandatory ? "text-red-600" : "text-slate-400"}`}>
                          {criterion.is_mandatory ? "Yes" : "No"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {evaluation?.extracted_value || <span className="text-slate-300">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        {evaluation ? (
                          <VerdictBadge
                            verdict={evaluation.verdict}
                            humanVerdict={evaluation.human_verdict}
                          />
                        ) : <span className="text-slate-300 text-xs">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        {evaluation?.confidence != null ? (
                          <ConfidenceBar value={evaluation.confidence} />
                        ) : <span className="text-slate-300 text-xs">—</span>}
                      </td>
                      <td className="px-4 py-3 max-w-[220px]">
                        {evaluation ? (
                          <div>
                            {evaluation.evidence_snippet && (
                              <div>
                                <p className="text-xs text-slate-500 italic leading-relaxed mb-1">
                                  {isExpanded
                                    ? `"${evaluation.evidence_snippet}"`
                                    : `"${evaluation.evidence_snippet.slice(0, 80)}${evaluation.evidence_snippet.length > 80 ? "..." : ""}"`}
                                  {evaluation.evidence_snippet.length > 80 && (
                                    <button
                                      onClick={() => toggleEvidence(criterion.id)}
                                      className="ml-1 text-blue-500 hover:underline text-xs"
                                    >
                                      {isExpanded ? "less" : "more"}
                                    </button>
                                  )}
                                </p>
                                {criterion.source_page && (
                                  <button
                                    onClick={() => openProvenance(criterion.source_page!, evaluation.evidence_snippet || undefined)}
                                    className="inline-flex items-center gap-1 text-[10px] bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5 rounded hover:bg-blue-100 hover:border-blue-300 transition-colors cursor-pointer font-medium mt-1"
                                    title={`View source on page ${criterion.source_page}`}
                                  >
                                    <Eye className="w-3 h-3" />
                                    Page {criterion.source_page}
                                  </button>
                                )}
                              </div>
                            )}
                            {evaluation.human_verdict && evaluation.human_verdict !== evaluation.verdict && (
                              <p className="text-xs text-blue-600 font-medium mt-1 flex items-center gap-0.5">
                                ★ Overridden: {evaluation.human_note?.slice(0, 60)}
                              </p>
                            )}
                          </div>
                        ) : <span className="text-slate-300 text-xs">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        {evaluation ? (
                          evaluation.human_verdict ? (
                            <button
                              onClick={() => setReviewing(ce)}
                              className="text-xs text-blue-600 hover:underline flex items-center gap-0.5"
                            >
                              <ClipboardCheck className="w-3 h-3" /> Reviewed
                            </button>
                          ) : (
                            <button
                              onClick={() => setReviewing(ce)}
                              className="text-xs bg-amber-50 border border-amber-300 text-amber-700 px-2 py-1 rounded hover:bg-amber-100 transition-colors"
                            >
                              Review
                            </button>
                          )
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        </div>
      )}

      {/* Review Panel */}
      {reviewing && reviewing.evaluation && (
        <ReviewPanel
          criterion={reviewing.criterion}
          evaluation={reviewing.evaluation}
          onClose={() => setReviewing(null)}
          onSaved={handleReviewSaved}
        />
      )}
    </div>
    
  );
}

export default function EvaluationPage() {
  const { tenderId, bidderId } = useParams<{ tenderId: string; bidderId: string }>();
  const tId = parseInt(tenderId);
  const bId = parseInt(bidderId);
  return (
    
      <EvaluationContent />
    
  );
}
