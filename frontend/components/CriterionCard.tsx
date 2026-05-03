import { Criterion, TYPE_COLOR } from "@/lib/api";
import ConfidenceBar from "./ConfidenceBar";

interface Props {
  criterion: Criterion;
}

export default function CriterionCard({ criterion }: Props) {
  const typeColor = TYPE_COLOR[criterion.criterion_type] || "bg-slate-100 text-slate-700";

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeColor}`}>
          {criterion.criterion_type.charAt(0).toUpperCase() + criterion.criterion_type.slice(1)}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          criterion.is_mandatory
            ? "bg-red-100 text-red-700"
            : "bg-slate-100 text-slate-600"
        }`}>
          {criterion.is_mandatory ? "Mandatory" : "Optional"}
        </span>
      </div>

      <p className="text-sm text-slate-800 font-medium leading-snug mb-2">{criterion.description}</p>

      {criterion.threshold_value && (
        <div className="text-xs text-slate-500 mb-2">
          <span className="font-medium text-slate-600">Threshold: </span>
          {criterion.threshold_value}
        </div>
      )}

      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Extraction confidence</span>
        <ConfidenceBar value={criterion.extraction_confidence} />
      </div>

      {criterion.raw_source_text && (
        <details className="mt-2">
          <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-600">Source text</summary>
          <p className="mt-1 text-xs text-slate-500 italic bg-slate-50 rounded p-2 leading-relaxed">
            "{criterion.raw_source_text}"
          </p>
        </details>
      )}
    </div>
  );
}
