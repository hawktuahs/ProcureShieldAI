import Link from "next/link";
import { Bidder } from "@/lib/api";
import VerdictBadge from "./VerdictBadge";
import { Loader2, ChevronRight, CheckCircle2, XCircle, AlertCircle, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Props {
  bidder: Bidder;
  tenderId: number;
}

function MatchBar({ pass, fail, review, total }: { pass: number; fail: number; review: number; total: number }) {
  if (!total) return null;
  const passW  = Math.round((pass   / total) * 100);
  const failW  = Math.round((fail   / total) * 100);
  const revW   = 100 - passW - failW;
  return (
    <div className="flex h-1.5 rounded-full overflow-hidden gap-px mt-1.5 bg-slate-100">
      {passW > 0 && <div className="bg-green-500 rounded-full" style={{ width: `${passW}%` }} title={`${pass} passed`} />}
      {failW > 0 && <div className="bg-red-500 rounded-full" style={{ width: `${failW}%` }} title={`${fail} failed`} />}
      {revW  > 0 && <div className="bg-amber-400 rounded-full" style={{ width: `${revW}%` }} title={`${review} needs review`} />}
    </div>
  );
}

export default function BidderSummaryCard({ bidder, tenderId }: Props) {
  const isProcessing = bidder.status === "processing";
  const hasScore = bidder.criteria_total != null && bidder.criteria_total > 0;
  
  const riskScore = bidder.risk_score || 0;
  const riskColor = riskScore < 30 ? "text-green-600" : riskScore < 60 ? "text-amber-600" : "text-red-600";
  const riskBg = riskScore < 30 ? "bg-green-500" : riskScore < 60 ? "bg-amber-500" : "bg-red-500";

  return (
    <Card className="hover:shadow-md transition-shadow overflow-hidden group">
      {/* Top row */}
      <CardHeader className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-row items-start justify-between gap-3 space-y-0">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-bold text-slate-800 truncate" title={bidder.name}>{bidder.name}</h3>
            {bidder.extraction_method === "ocr" && (
              <Badge variant="secondary" className="text-[9px] font-bold bg-purple-100 text-purple-700 hover:bg-purple-200 uppercase tracking-wider px-1.5 py-0.5 rounded">
                OCR
              </Badge>
            )}
          </div>
          <p className="text-[11px] text-slate-500 font-medium">
            Submitted: {new Date(bidder.upload_time).toLocaleString("en-US", {
              month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
            })}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isProcessing ? (
            <Badge variant="outline" className="flex items-center gap-1.5 text-xs font-semibold text-amber-600 bg-amber-50 border-amber-200">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Evaluating
            </Badge>
          ) : (
            <VerdictBadge verdict={bidder.overall_verdict} size="md" />
          )}
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {/* Match score + criteria breakdown */}
        {!isProcessing && hasScore && (
          <div className="grid grid-cols-2 gap-6 mb-4">
            {/* Criteria Match */}
            <div>
              <div className="flex items-center justify-between mb-1 text-xs">
                <span className="text-slate-500 font-semibold uppercase tracking-wider">Criteria Match</span>
                <span className="font-bold text-slate-700">{bidder.match_score != null ? `${bidder.match_score}%` : "—"}</span>
              </div>
              <MatchBar
                pass={bidder.criteria_pass ?? 0}
                fail={bidder.criteria_fail ?? 0}
                review={bidder.criteria_review ?? 0}
                total={bidder.criteria_total ?? 0}
              />
              <div className="flex justify-between mt-2">
                <span className="text-[10px] font-semibold text-green-600">{bidder.criteria_pass ?? 0} Pass</span>
                <span className="text-[10px] font-semibold text-amber-500">{bidder.criteria_review ?? 0} Rev</span>
                <span className="text-[10px] font-semibold text-red-500">{bidder.criteria_fail ?? 0} Fail</span>
              </div>
            </div>

            {/* Risk Profile */}
            <div>
              <div className="flex items-center justify-between mb-1 text-xs">
                <span className="text-slate-500 font-semibold uppercase tracking-wider flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3"/> Risk Score
                </span>
                <span className={`font-bold ${riskColor}`}>{riskScore} / 100</span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mt-1.5">
                <div className={`h-full rounded-full ${riskBg}`} style={{ width: `${riskScore}%` }} />
              </div>
              <p className="text-[10px] font-medium text-slate-400 mt-2 text-right">Lower is better</p>
            </div>
          </div>
        )}

        {/* Executive Summary */}
        {!isProcessing && bidder.overall_reasoning && (
          <div className="mb-4 bg-blue-50/50 rounded-lg p-3 border border-blue-100">
            <h4 className="text-[10px] font-bold text-blue-600 uppercase tracking-wider mb-1">Executive Summary</h4>
            <p className="text-xs text-slate-700 leading-relaxed line-clamp-3">
              {bidder.overall_reasoning}
            </p>
          </div>
        )}

        <Link
          href={`/evaluation/${tenderId}/${bidder.id}`}
          className={`flex items-center justify-center gap-1.5 w-full py-2.5 rounded-lg text-sm font-semibold transition-all mt-4 ${
            isProcessing 
              ? "bg-slate-100 text-slate-400 cursor-not-allowed"
              : "bg-[#1e3a5f] text-white hover:bg-blue-800 shadow-sm hover:shadow"
          }`}
          onClick={(e) => isProcessing && e.preventDefault()}
        >
          {isProcessing ? "Evaluation in Progress..." : "View Full Audit Matrix"}
          {!isProcessing && <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />}
        </Link>
      </CardContent>
    </Card>
  );
}
