"use client";
import { useState } from "react";
import { X, CheckCircle } from "lucide-react";
import { reviewEvaluation, Criterion, Evaluation, VERDICT_LABEL } from "@/lib/api";
import ConfidenceBar from "./ConfidenceBar";

interface Props {
  criterion: Criterion;
  evaluation: Evaluation;
  onClose: () => void;
  onSaved: (evaluationId: number, humanVerdict: string) => void;
}

export default function ReviewPanel({ criterion, evaluation, onClose, onSaved }: Props) {
  const [verdict, setVerdict] = useState<string>(evaluation.human_verdict || evaluation.verdict || "needs_review");
  const [note, setNote] = useState(evaluation.human_note || "");
  const [reviewer, setReviewer] = useState(evaluation.reviewed_by || "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!evaluation.id) return;
    setSaving(true);
    setError(null);
    try {
      await reviewEvaluation(evaluation.id, {
        human_verdict: verdict,
        human_note: note,
        reviewed_by: reviewer || "Reviewer",
      });
      setSaved(true);
      onSaved(evaluation.id, verdict);
      setTimeout(() => onClose(), 800);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to save review");
    } finally {
      setSaving(false);
    }
  };

  const typeMap: Record<string, string> = {
    financial: "bg-blue-100 text-blue-800",
    technical: "bg-green-100 text-green-800",
    compliance: "bg-amber-100 text-amber-800",
    documentation: "bg-purple-100 text-purple-800",
  };

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-full max-w-lg bg-white shadow-2xl flex flex-col overflow-y-auto">
        {/* Header */}
        <div className="bg-[#1e3a5f] text-white px-6 py-4 flex items-center justify-between shrink-0">
          <h2 className="font-semibold text-lg">Review Criterion</h2>
          <button onClick={onClose} className="hover:bg-blue-800 rounded p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 flex flex-col gap-4 flex-1">
          {/* Criterion */}
          <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
            <div className="flex gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeMap[criterion.criterion_type] || ""}`}>
                {criterion.criterion_type}
              </span>
              {criterion.is_mandatory && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">Mandatory</span>
              )}
            </div>
            <p className="text-sm font-medium text-slate-800">{criterion.description}</p>
            {criterion.threshold_value && (
              <p className="text-xs text-slate-500 mt-1">Threshold: {criterion.threshold_value}</p>
            )}
          </div>

          {/* AI result */}
          <div className="border border-slate-200 rounded-lg p-4">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">AI Evaluation</h3>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <p className="text-xs text-slate-400 mb-1">Verdict</p>
                <span className={`text-xs font-semibold px-2 py-1 rounded ${
                  evaluation.verdict === "pass" ? "bg-green-100 text-green-700" :
                  evaluation.verdict === "fail" ? "bg-red-100 text-red-700" :
                  "bg-amber-100 text-amber-700"
                }`}>
                  {VERDICT_LABEL[evaluation.verdict || ""] || evaluation.verdict}
                </span>
              </div>
              <div>
                <p className="text-xs text-slate-400 mb-1">Confidence</p>
                <ConfidenceBar value={evaluation.confidence || 0} />
              </div>
            </div>
            {evaluation.extracted_value && (
              <div className="mb-2">
                <p className="text-xs text-slate-400 mb-0.5">Extracted Value</p>
                <p className="text-xs font-medium text-slate-700">{evaluation.extracted_value}</p>
              </div>
            )}
            {evaluation.evidence_snippet && (
              <div className="mb-2">
                <p className="text-xs text-slate-400 mb-0.5">Evidence</p>
                <p className="text-xs italic text-slate-600 bg-slate-50 rounded p-2 leading-relaxed">
                  "{evaluation.evidence_snippet}"
                </p>
              </div>
            )}
            {evaluation.reasoning && (
              <div>
                <p className="text-xs text-slate-400 mb-0.5">Reasoning</p>
                <p className="text-xs text-slate-600 leading-relaxed">{evaluation.reasoning}</p>
              </div>
            )}
          </div>

          {/* Override */}
          <div className="border border-blue-200 rounded-lg p-4 bg-blue-50">
            <h3 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-3">Human Review</h3>
            <div className="flex flex-col gap-2 mb-4">
              {[
                { value: "pass", label: "Override to Pass", color: "border-green-400 text-green-700" },
                { value: "fail", label: "Override to Fail", color: "border-red-400 text-red-700" },
                { value: "needs_review", label: "Flag for Manual Review", color: "border-amber-400 text-amber-700" },
              ].map((opt) => (
                <label key={opt.value} className={`flex items-center gap-3 p-2.5 rounded border cursor-pointer transition-colors ${
                  verdict === opt.value ? `${opt.color} bg-white border-2` : "border-slate-200 bg-white hover:border-slate-300"
                }`}>
                  <input
                    type="radio"
                    name="verdict"
                    value={opt.value}
                    checked={verdict === opt.value}
                    onChange={() => setVerdict(opt.value)}
                    className="accent-blue-600"
                  />
                  <span className={`text-sm font-medium ${verdict === opt.value ? opt.color.split(" ")[1] : "text-slate-700"}`}>
                    {opt.label}
                  </span>
                </label>
              ))}
            </div>

            <div className="mb-3">
              <label className="text-xs font-medium text-slate-600 block mb-1">Review Note</label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={3}
                placeholder="Reason for override (optional)..."
                className="w-full text-sm border border-slate-300 rounded-md p-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div className="mb-4">
              <label className="text-xs font-medium text-slate-600 block mb-1">Reviewer Name</label>
              <input
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder="Your name"
                className="w-full text-sm border border-slate-300 rounded-md p-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>

            {error && <p className="text-xs text-red-500 mb-2">{error}</p>}

            <button
              onClick={handleSave}
              disabled={saving || saved}
              className={`w-full py-2.5 rounded-md text-sm font-semibold transition-colors flex items-center justify-center gap-2 ${
                saved ? "bg-green-500 text-white" :
                "bg-[#1e3a5f] text-white hover:bg-blue-800 disabled:opacity-60"
              }`}
            >
              {saved ? <><CheckCircle className="w-4 h-4" /> Saved</> :
               saving ? "Saving..." : "Submit Review"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
