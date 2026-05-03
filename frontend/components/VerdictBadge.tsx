import { VERDICT_LABEL, VERDICT_COLOR } from "@/lib/api";

interface Props {
  verdict: string | null | undefined;
  humanVerdict?: string | null;
  size?: "sm" | "md" | "lg";
}

export default function VerdictBadge({ verdict, humanVerdict, size = "md" }: Props) {
  const effective = humanVerdict || verdict;
  if (!effective) return <span className="text-slate-400 text-xs">—</span>;

  const label = VERDICT_LABEL[effective] || effective;
  const color = VERDICT_COLOR[effective] || "bg-slate-400 text-white";
  const isOverridden = humanVerdict && humanVerdict !== verdict;

  const sizeClass = {
    sm: "text-xs px-2 py-0.5",
    md: "text-xs px-2.5 py-1",
    lg: "text-sm px-3 py-1.5 font-semibold",
  }[size];

  return (
    <span className="inline-flex items-center gap-1">
      <span className={`rounded-full font-medium ${color} ${sizeClass}`}>{label}</span>
      {isOverridden && (
        <span className="text-xs text-blue-600 font-medium" title="Human override">★</span>
      )}
    </span>
  );
}
