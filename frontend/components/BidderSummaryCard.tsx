import Link from "next/link";
import { Bidder } from "@/lib/api";
import VerdictBadge from "./VerdictBadge";
import { Loader2, ChevronRight, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

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
    <div className="flex h-1.5 rounded-full overflow-hidden gap-px mt-1.5">
      {passW > 0 && <div className="bg-green-500 rounded-full" style={{ width: `${passW}%` }} />}
      {failW > 0 && <div className="bg-red-500 rounded-full" style={{ width: `${failW}%` }} />}
      {revW  > 0 && <div className="bg-amber-400 rounded-full" style={{ width: `${revW}%` }} />}
    </div>
  );
}

export default function BidderSummaryCard({ bidder, tenderId }: Props) {
  const isProcessing = bidder.status === "processing";
  const hasScore = bidder.criteria_total != null && bidder.criteria_total > 0;
  const score = bidder.match_score;

  const scoreColor =
    score == null ? "text-slate-400"
    : score >= 80  ? "text-green-600"
    : score >= 50  ? "text-amber-600"
    : "text-red-600";

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <p className="text-sm font-semibold text-slate-800 truncate">{bidder.name}</p>
            {bidder.extraction_method === "ocr" && (
              <span className="text-[10px] bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded shrink-0">OCR</span>
            )}
          </div>
          <p className="text-xs text-slate-400">
            {new Date(bidder.upload_time).toLocaleString("en-IN", {
              day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
            })}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isProcessing ? (
            <span className="flex items-center gap-1 text-xs text-amber-600">
              <Loader2 className="w-3 h-3 animate-spin" /> Evaluating...
            </span>
          ) : (
            <VerdictBadge verdict={bidder.overall_verdict} size="md" />
          )}
        </div>
      </div>

      {/* Match score + criteria breakdown */}
      {!isProcessing && hasScore && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-400">Criteria match</span>
            <span className={`text-xs font-bold tabular-nums ${scoreColor}`}>
              {score != null ? `${score}%` : "—"}
            </span>
          </div>
          <MatchBar
            pass={bidder.criteria_pass ?? 0}
            fail={bidder.criteria_fail ?? 0}
            review={bidder.criteria_review ?? 0}
            total={bidder.criteria_total ?? 0}
          />
          <div className="flex items-center gap-3 mt-1.5">
            <span className="flex items-center gap-1 text-[10px] text-green-600">
              <CheckCircle2 className="w-3 h-3" />{bidder.criteria_pass ?? 0} passed
            </span>
            <span className="flex items-center gap-1 text-[10px] text-red-500">
              <XCircle className="w-3 h-3" />{bidder.criteria_fail ?? 0} failed
            </span>
            <span className="flex items-center gap-1 text-[10px] text-amber-500">
              <AlertCircle className="w-3 h-3" />{bidder.criteria_review ?? 0} review
            </span>
          </div>
        </div>
      )}

      {/* Reasoning */}
      {bidder.overall_reasoning && bidder.status === "evaluated" && (
        <p className="text-xs text-slate-500 italic line-clamp-2 mb-3">{bidder.overall_reasoning}</p>
      )}

      {/* View button */}
      {bidder.status === "evaluated" && (
        <Link
          href={`/evaluation/${tenderId}/${bidder.id}`}
          className="flex items-center justify-center gap-1 w-full bg-[#1e3a5f] text-white py-2 rounded-lg text-xs font-medium hover:bg-blue-800 transition-colors"
        >
          View Full Evaluation <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      )}
    </div>
  );
}
