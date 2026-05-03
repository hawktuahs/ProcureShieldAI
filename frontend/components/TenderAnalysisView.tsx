"use client";
import { useState } from "react";
import {
  FileText, Target, Shield, Phone, MessageSquare,
  ChevronDown, ChevronUp, Loader2, MapPin, Mail,
  Building2, LayoutDashboard, Package, Calendar,
  IndianRupee, CheckCircle2, Info, RefreshCw, Send, AlertCircle,
} from "lucide-react";
import { askTender } from "@/lib/api";
import {
  TenderAnalysisData, TenderOverview, AnalysisDocument,
  ScopeItem, EligibilityItem, ContactItem, ItemEntry, Criterion,
} from "@/lib/api";

interface Props {
  analysis: TenderAnalysisData | null;
  loading: boolean;
  tenderStatus: string;
  tenderFilename?: string;
  tenderId: number;
  criteria?: Criterion[];        // raw criteria from DB (Eligibility fallback)
  onReanalyze?: () => void;      // trigger re-analysis
}

const TABS = [
  { id: "overview",    label: "Overview",       icon: LayoutDashboard },
  { id: "documents",   label: "Documents",      icon: FileText },
  { id: "items",       label: "Items & Qty",    icon: Package },
  { id: "scope",       label: "Scope of Work",  icon: Target },
  { id: "eligibility", label: "Eligibility",    icon: Shield },
  { id: "contacts",    label: "Contacts",       icon: Phone },
  { id: "followup",    label: "Follow-up",      icon: MessageSquare },
] as const;

type TabId = typeof TABS[number]["id"];

const TYPE_COLORS: Record<string, string> = {
  financial:     "bg-blue-50  text-blue-700  border-blue-200",
  technical:     "bg-green-50 text-green-700 border-green-200",
  compliance:    "bg-amber-50 text-amber-700 border-amber-200",
  documentation: "bg-purple-50 text-purple-700 border-purple-200",
};

// ── PRIMITIVES ──────────────────────────────────────────────────────────────

function Citation({ text }: { text: string }) {
  return (
    <div className="border-l-2 border-slate-300 pl-3 py-0.5 my-1">
      <p className="text-xs text-slate-500 leading-relaxed italic">{text}</p>
    </div>
  );
}

function SourceChip({ filename }: { filename?: string }) {
  if (!filename) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded border border-slate-200 mt-2">
      <FileText className="w-3 h-3" />{filename}
    </span>
  );
}

function SectionCard({ title, icon: Icon, children, action }: {
  title: string; icon: React.ElementType; children: React.ReactNode; action?: React.ReactNode;
}) {
  return (
    <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        </div>
        {action}
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}

function InfoGrid({ items }: { items: { label: string; value: string | null | undefined }[] }) {
  const visible = items.filter(i => i.value);
  if (!visible.length) return null;
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3">
      {visible.map(({ label, value }) => (
        <div key={label}>
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-0.5">{label}</p>
          <p className="text-sm font-medium text-slate-700">{value}</p>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ tab, onReanalyze }: { tab: string; onReanalyze?: () => void }) {
  return (
    <div className="text-center py-10 text-slate-400 text-sm border border-slate-200 rounded-xl bg-white">
      <Info className="w-7 h-7 mx-auto mb-2 text-slate-300" />
      <p>No {tab} items extracted yet.</p>
      {onReanalyze && (
        <button
          onClick={onReanalyze}
          className="mt-3 flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 mx-auto border border-blue-200 bg-blue-50 px-3 py-1.5 rounded-full transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Re-analyse with AI
        </button>
      )}
    </div>
  );
}

// ── OVERVIEW TAB ─────────────────────────────────────────────────────────────

function WorkDescriptionCard({ ov }: { ov: TenderOverview }) {
  return (
    <SectionCard title="Work Description" icon={FileText}>
      {ov.work_description && (
        <p className="text-sm font-semibold text-slate-800 mb-4">{ov.work_description}</p>
      )}
      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-3">Tender Information</p>
      <InfoGrid items={[
        { label: "Tender Type",       value: ov.tender_type },
        { label: "Evaluation Method", value: ov.evaluation_method },
        { label: "Location",          value: ov.location },
        { label: "Bid Type",          value: ov.bid_type },
      ]} />
      {ov.beneficiary && (
        <div className="mt-4 pt-3 border-t border-slate-100">
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1">Beneficiary</p>
          <p className="text-xs text-slate-600 leading-relaxed">{ov.beneficiary}</p>
        </div>
      )}
    </SectionCard>
  );
}

function EligibilityChipsCard({ eligibility }: { eligibility: EligibilityItem[] }) {
  const chips = eligibility.filter(e => e.threshold_value);
  if (!chips.length) return null;
  return (
    <SectionCard title="Eligibility Criteria" icon={Shield}>
      <div className="flex flex-wrap gap-2">
        {chips.map((e, i) => (
          <div key={i} className="flex flex-col items-center bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 min-w-[90px]">
            <span className="text-[10px] text-slate-400 uppercase tracking-wide truncate max-w-[120px] text-center">{e.title}</span>
            <span className="text-sm font-bold text-slate-800 mt-0.5">{e.threshold_value}</span>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function PurchasePreferencesCard({ preferences }: { preferences: string[] }) {
  if (!preferences?.length) return null;
  return (
    <SectionCard title="Purchase Preferences" icon={CheckCircle2}>
      <div className="flex flex-wrap gap-2">
        {preferences.map((p, i) => (
          <span key={i} className="flex items-center gap-1.5 text-xs bg-green-50 text-green-700 border border-green-200 px-3 py-1.5 rounded-full font-medium">
            <CheckCircle2 className="w-3 h-3" />{p}
          </span>
        ))}
      </div>
    </SectionCard>
  );
}

function FeeDetailsCard({ ov }: { ov: TenderOverview }) {
  const hasAny = ov.tender_fee_amount || ov.emd_fee_amount || ov.tender_fee_exemption_allowed || ov.emd_fee_exemption_allowed;
  if (!hasAny) return null;
  return (
    <SectionCard title="Fee & Financial Details" icon={IndianRupee}>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        {ov.tender_fee_amount && (
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Tender Fee Amount</p>
            <p className="text-sm font-semibold text-slate-700">{ov.tender_fee_amount}</p>
          </div>
        )}
        {ov.tender_fee_exemption_allowed && (
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">Tender Fee Exemption</p>
            <p className={`text-sm font-semibold ${ov.tender_fee_exemption_allowed === "Yes" ? "text-blue-600" : "text-slate-700"}`}>
              {ov.tender_fee_exemption_allowed}
            </p>
          </div>
        )}
        {ov.emd_fee_amount && (
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">EMD Fee Amount</p>
            <p className="text-sm font-semibold text-slate-700">{ov.emd_fee_amount}</p>
          </div>
        )}
        {ov.emd_fee_exemption_allowed && (
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-0.5">EMD Exemption Allowed</p>
            <p className={`text-sm font-semibold ${ov.emd_fee_exemption_allowed === "Yes" ? "text-blue-600" : "text-slate-700"}`}>
              {ov.emd_fee_exemption_allowed}
            </p>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

function ImportantDatesCard({ ov }: { ov: TenderOverview }) {
  const hasDates = ov.published_date || ov.bid_opening_date || ov.last_activity_date;
  if (!hasDates) return null;
  return (
    <SectionCard title="Important Dates" icon={Calendar}>
      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
        {ov.published_date && (
          <div className="flex items-start gap-2">
            <Calendar className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-[10px] text-slate-400 uppercase tracking-wider">Published</p>
              <p className="text-sm font-semibold text-slate-700">{ov.published_date}</p>
            </div>
          </div>
        )}
        {ov.bid_opening_date && (
          <div className="flex items-start gap-2">
            <Calendar className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-[10px] text-slate-400 uppercase tracking-wider">Bid Opening</p>
              <p className="text-sm font-semibold text-slate-700">{ov.bid_opening_date}</p>
            </div>
          </div>
        )}
        {ov.last_activity_date && (
          <div className="flex items-start gap-2">
            <Calendar className="w-3.5 h-3.5 text-slate-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-[10px] text-slate-400 uppercase tracking-wider">Last Activity</p>
              <p className="text-sm font-semibold text-slate-700">{ov.last_activity_date}</p>
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

function OverviewTab({ analysis, onReanalyze }: { analysis: TenderAnalysisData; onReanalyze?: () => void }) {
  const ov: TenderOverview = analysis.overview ?? {};
  const hasData = ov.work_description || ov.tender_type || ov.location || ov.bid_opening_date;

  if (!hasData) {
    return (
      <div className="flex flex-col gap-4">
        {/* Show eligibility chips even if overview failed */}
        {(analysis.eligibility?.length ?? 0) > 0 && (
          <EligibilityChipsCard eligibility={analysis.eligibility} />
        )}
        <div className="text-center py-10 text-slate-400 text-sm border border-slate-200 rounded-xl bg-white">
          <Info className="w-7 h-7 mx-auto mb-2 text-slate-300" />
          <p>Tender overview not yet extracted.</p>
          {onReanalyze && (
            <button
              onClick={onReanalyze}
              className="mt-3 flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 mx-auto border border-blue-200 bg-blue-50 px-3 py-1.5 rounded-full transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Re-analyse with AI
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <WorkDescriptionCard ov={ov} />
      <EligibilityChipsCard eligibility={analysis.eligibility || []} />
      {(ov.purchase_preferences?.length ?? 0) > 0 && (
        <PurchasePreferencesCard preferences={ov.purchase_preferences!} />
      )}
      <FeeDetailsCard ov={ov} />
      <ImportantDatesCard ov={ov} />
    </div>
  );
}

// ── DOCUMENTS TAB ─────────────────────────────────────────────────────────────

function DocumentRow({ doc }: { doc: AnalysisDocument }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-slate-100 last:border-0">
      <div
        className="flex items-center gap-3 py-3 cursor-pointer hover:bg-slate-50/80 px-1 rounded transition-colors"
        onClick={() => setOpen(!open)}
      >
        <span className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded border ${
          doc.is_mandatory
            ? "bg-red-50 text-red-600 border-red-200"
            : "bg-slate-50 text-slate-500 border-slate-200"
        }`}>
          {doc.is_mandatory ? "Required" : "Optional"}
        </span>
        <p className="flex-1 text-sm text-slate-700 font-medium">{doc.title}</p>
        <div className="flex items-center gap-2 shrink-0">
          {doc.format_available && (
            <span className="text-[10px] bg-green-50 text-green-600 border border-green-200 px-1.5 py-0.5 rounded">Format</span>
          )}
          {open ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
        </div>
      </div>
      {open && (
        <div className="ml-4 mb-3 pl-3 border-l border-slate-200 flex flex-col gap-2">
          {doc.summary && <p className="text-xs text-slate-500">{doc.summary}</p>}
          {doc.how_to_submit && (
            <div>
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">How to submit: </span>
              <span className="text-xs text-slate-600">{doc.how_to_submit}</span>
            </div>
          )}
          {doc.details && <Citation text={doc.details} />}
          {doc.format_notes && <p className="text-xs text-slate-500 italic">{doc.format_notes}</p>}
        </div>
      )}
    </div>
  );
}

function DocumentsTab({ documents, filename, onReanalyze }: {
  documents: AnalysisDocument[]; filename?: string; onReanalyze?: () => void;
}) {
  if (!documents.length) return <EmptyState tab="documents" onReanalyze={onReanalyze} />;
  const mandatory = documents.filter(d => d.is_mandatory).length;
  return (
    <div className="border border-slate-200 rounded-xl bg-white overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-slate-700">Documents Required</h3>
        </div>
        <p className="text-xs text-slate-400">
          {documents.length} documents · <span className="text-red-500 font-medium">{mandatory} mandatory</span>
        </p>
      </div>
      <div className="px-4 max-h-[500px] overflow-y-auto">
        {documents.map((doc, i) => <DocumentRow key={i} doc={doc} />)}
      </div>
      {filename && (
        <div className="px-5 py-2.5 border-t border-slate-100">
          <SourceChip filename={filename} />
        </div>
      )}
    </div>
  );
}

// ── ITEMS TAB ─────────────────────────────────────────────────────────────────

function ItemCard({ item }: { item: ItemEntry }) {
  const [expanded, setExpanded] = useState(false);
  const specs = item.specifications ?? [];
  const hasSpecs = specs.length > 0;

  return (
    <div className="border border-slate-200 rounded-xl bg-white overflow-hidden hover:shadow-sm transition-shadow">
      <div
        className={`flex items-start gap-4 px-5 py-4 ${hasSpecs ? "cursor-pointer" : ""}`}
        onClick={() => hasSpecs && setExpanded(!expanded)}
      >
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-800 font-semibold leading-snug">{item.item_name}</p>
          <div className="flex flex-wrap items-center gap-3 mt-1.5">
            {item.specifications_ref && (
              <span className="text-[10px] bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded font-medium">
                {item.specifications_ref}
              </span>
            )}
            {item.consignee && (
              <span className="text-xs text-slate-500">{item.consignee}</span>
            )}
            {item.delivery_location && (
              <span className="text-xs text-slate-400">{item.delivery_location}</span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className="text-lg font-bold text-slate-800 tabular-nums">
            {item.quantity}
            {item.quantity_unit && <span className="text-xs font-normal text-slate-400 ml-1">{item.quantity_unit}</span>}
          </span>
          {item.delivery_period && (
            <span className="text-[10px] text-slate-400">{item.delivery_period}</span>
          )}
        </div>
        {hasSpecs && (
          <div className="shrink-0 self-center">
            {expanded
              ? <ChevronUp className="w-4 h-4 text-slate-400" />
              : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </div>
        )}
      </div>
      {expanded && hasSpecs && (
        <div className="px-5 pb-4 pt-0 border-t border-slate-100">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 mt-3">Technical Specifications</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            {specs.map((spec, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-slate-600 bg-slate-50 rounded px-2.5 py-1.5 border border-slate-100">
                <span className="text-blue-500 font-bold mt-px shrink-0">•</span>
                <span>{spec}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ItemsTab({ items, filename, onReanalyze }: {
  items: ItemEntry[]; filename?: string; onReanalyze?: () => void;
}) {
  if (!items.length) return <EmptyState tab="items" onReanalyze={onReanalyze} />;
  const totalQty = items.reduce((acc, it) => {
    const n = parseInt((it.quantity || "0").replace(/,/g, ""), 10);
    return acc + (isNaN(n) ? 0 : n);
  }, 0);
  const specsCount = items.filter(it => (it.specifications ?? []).length > 0).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Package className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-slate-700">Items & Quantities</h3>
          <span className="text-xs text-slate-400">
            {items.length} item{items.length !== 1 ? "s" : ""}
            {totalQty > 0 && <> · Total qty: <strong className="text-slate-600">{totalQty.toLocaleString("en-IN")}</strong></>}
            {specsCount > 0 && <> · {specsCount} with specs</>}
          </span>
        </div>
        {filename && <SourceChip filename={filename} />}
      </div>
      {items.map((item, i) => (
        <ItemCard key={i} item={item} />
      ))}
    </div>
  );
}

// ── ELIGIBILITY TAB (with criteria fallback) ──────────────────────────────────

function EligibilityCard({ item, filename }: { item: EligibilityItem; filename?: string }) {
  return (
    <div className="border border-slate-200 rounded-xl bg-white px-4 py-3.5">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <p className="text-sm font-semibold text-slate-800">{item.title}</p>
        <div className="flex items-center gap-1.5 shrink-0">
          {item.threshold_value && (
            <span className="text-xs bg-blue-50 border border-blue-200 text-blue-700 px-2 py-0.5 rounded-full font-medium">
              {item.threshold_value}
            </span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${
            item.is_mandatory ? "bg-red-50 border-red-200 text-red-600" : "bg-slate-50 border-slate-200 text-slate-500"
          }`}>
            {item.is_mandatory ? "Mandatory" : "Optional"}
          </span>
        </div>
      </div>
      <p className="text-xs text-slate-500 mb-2">{item.summary}</p>
      <div className="flex flex-col gap-1">
        {(item.citations || []).map((c, i) => <Citation key={i} text={c} />)}
      </div>
      <SourceChip filename={filename} />
    </div>
  );
}

function CriterionFallbackCard({ c }: { c: Criterion }) {
  const colorClass = TYPE_COLORS[c.criterion_type] ?? "bg-slate-50 text-slate-600 border-slate-200";
  return (
    <div className="border border-slate-200 rounded-xl bg-white px-4 py-3 flex flex-col gap-1.5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-slate-700 leading-snug flex-1">{c.description}</p>
        <div className="flex items-center gap-1.5 shrink-0">
          {c.threshold_value && (
            <span className="text-xs bg-blue-50 border border-blue-200 text-blue-700 px-2 py-0.5 rounded-full font-medium">
              {c.threshold_value}
            </span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${
            c.is_mandatory ? "bg-red-50 border-red-200 text-red-600" : "bg-slate-50 border-slate-200 text-slate-500"
          }`}>
            {c.is_mandatory ? "Mandatory" : "Optional"}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium capitalize ${colorClass}`}>
            {c.criterion_type}
          </span>
        </div>
      </div>
      {c.raw_source_text && <Citation text={c.raw_source_text} />}
    </div>
  );
}

const TYPE_ORDER = ["financial", "technical", "compliance", "documentation"] as const;

function EligibilityTabContent({ analysisItems, criteria, filename, onReanalyze }: {
  analysisItems: EligibilityItem[];
  criteria: Criterion[];
  filename?: string;
  onReanalyze?: () => void;
}) {
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"analysis" | "criteria">(
    // Default to criteria view when it has significantly more items
    criteria.length > analysisItems.length * 2 ? "criteria" : "analysis"
  );

  const hasBothSources = analysisItems.length > 0 && criteria.length > 0;

  // ---------- Raw criteria view ----------
  const renderCriteria = () => {
    if (criteria.length === 0) return <EmptyState tab="eligibility criteria" onReanalyze={onReanalyze} />;

    const typeCounts = TYPE_ORDER.reduce((acc, t) => {
      acc[t] = criteria.filter(c => c.criterion_type === t).length;
      return acc;
    }, {} as Record<string, number>);

    const filtered = typeFilter === "all" ? criteria : criteria.filter(c => c.criterion_type === typeFilter);
    const mandatoryFirst = [...filtered].sort((a, b) => Number(b.is_mandatory) - Number(a.is_mandatory));

    return (
      <>
        {/* Type filter */}
        <div className="flex flex-wrap gap-1 mb-2">
          <button
            onClick={() => setTypeFilter("all")}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
              typeFilter === "all" ? "bg-[#1e3a5f] text-white border-[#1e3a5f]" : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
            }`}
          >
            All ({criteria.length})
          </button>
          {TYPE_ORDER.filter(t => typeCounts[t] > 0).map(t => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors capitalize ${
                typeFilter === t ? "bg-[#1e3a5f] text-white border-[#1e3a5f]" : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
              }`}
            >
              {t} ({typeCounts[t]})
            </button>
          ))}
        </div>

        {mandatoryFirst.map((c) => (
          <CriterionFallbackCard key={c.id} c={c} />
        ))}
      </>
    );
  };

  // ---------- Rich analysis view ----------
  const renderAnalysis = () => {
    if (analysisItems.length === 0) return <EmptyState tab="eligibility analysis" onReanalyze={onReanalyze} />;
    return (
      <>
        {analysisItems.map((item, i) => (
          <EligibilityCard key={i} item={item} filename={filename} />
        ))}
      </>
    );
  };

  if (!analysisItems.length && !criteria.length) {
    return <EmptyState tab="eligibility" onReanalyze={onReanalyze} />;
  }

  return (
    <>
      {/* View switcher when both sources available */}
      {hasBothSources && (
        <div className="flex items-center gap-2 mb-2">
          <div className="flex bg-slate-100 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode("criteria")}
              className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                viewMode === "criteria" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              All Criteria ({criteria.length})
            </button>
            <button
              onClick={() => setViewMode("analysis")}
              className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                viewMode === "analysis" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              AI Summary ({analysisItems.length})
            </button>
          </div>
          {onReanalyze && (
            <button onClick={onReanalyze} className="flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-800 ml-auto">
              <RefreshCw className="w-3 h-3" /> Re-analyse
            </button>
          )}
        </div>
      )}

      {/* Note when showing criteria */}
      {(!hasBothSources && criteria.length > 0) && (
        <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5 mb-1">
          <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>Showing {criteria.length} AI-extracted eligibility criteria. {onReanalyze && <button onClick={onReanalyze} className="font-medium underline hover:no-underline">Re-analyse</button>} for rich citations.</span>
        </div>
      )}

      {hasBothSources
        ? (viewMode === "criteria" ? renderCriteria() : renderAnalysis())
        : (criteria.length > 0 ? renderCriteria() : renderAnalysis())}
    </>
  );
}

// ── SCOPE TAB ─────────────────────────────────────────────────────────────────

function ScopeCard({ item, filename }: { item: ScopeItem; filename?: string }) {
  return (
    <div className="border border-slate-200 rounded-xl bg-white px-4 py-3.5">
      <p className="text-sm font-semibold text-slate-800 mb-1">{item.title}</p>
      <p className="text-xs text-slate-500 mb-2">{item.summary}</p>
      <div className="flex flex-col gap-1">
        {(item.citations || []).map((c, i) => <Citation key={i} text={c} />)}
      </div>
      <SourceChip filename={filename} />
    </div>
  );
}

// ── CONTACTS TAB ──────────────────────────────────────────────────────────────

function ContactCard({ item, filename }: { item: ContactItem; filename?: string }) {
  return (
    <div className="border border-slate-200 rounded-xl bg-white px-4 py-4">
      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">{item.role}</p>
      {item.name && <p className="text-sm font-bold text-slate-800 mb-2">{item.name}</p>}
      <div className="flex flex-col gap-1.5 mb-3">
        {item.organisation && (
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <Building2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />{item.organisation}
          </div>
        )}
        {item.address && (
          <div className="flex items-start gap-1.5 text-xs text-slate-600">
            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />{item.address}
          </div>
        )}
        {item.phone && (
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />{item.phone}
          </div>
        )}
        {item.email && (
          <div className="flex items-center gap-1.5 text-xs text-slate-600">
            <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <a href={`mailto:${item.email}`} className="text-blue-600 hover:underline">{item.email}</a>
          </div>
        )}
      </div>
      {(item.citations || []).length > 0 && (
        <div className="flex flex-col gap-1 mb-2">
          {item.citations.map((c, i) => <Citation key={i} text={c} />)}
        </div>
      )}
      <SourceChip filename={filename} />
    </div>
  );
}

// ── FOLLOW-UP TAB ─────────────────────────────────────────────────────────────

interface QAEntry { question: string; answer: string; }

function FollowUpTab({ tenderId }: { tenderId: number }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QAEntry[]>([]);

  const handleSubmit = async () => {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setQuestion("");
    try {
      const res = await askTender(tenderId, q);
      setHistory(prev => [...prev, { question: q, answer: res.data.answer }]);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Failed to get an answer. Please try again.";
      setError(msg);
      setQuestion(q); // restore question so user doesn't lose it
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border border-slate-200 rounded-xl bg-white px-5 py-5">
      <div className="flex items-center gap-2 mb-1">
        <MessageSquare className="w-5 h-5 text-blue-600" />
        <h3 className="text-lg font-semibold text-slate-800">Ask the tender</h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Ask any question about this tender and get an AI-generated answer grounded in the document.
      </p>

      {/* Conversation history */}
      {history.length > 0 && (
        <div className="flex flex-col gap-4 mb-5 max-h-80 overflow-y-auto pr-1">
          {history.map((entry, i) => (
            <div key={i} className="flex flex-col gap-2">
              <div className="self-end bg-[#1e3a5f] text-white text-sm rounded-xl px-4 py-2 max-w-[85%]">
                {entry.question}
              </div>
              <div className="self-start bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-xl px-4 py-3 max-w-[95%] whitespace-pre-wrap leading-relaxed">
                {entry.answer}
              </div>
            </div>
          ))}
          {loading && (
            <div className="self-start flex items-center gap-2 text-sm text-slate-400 px-4 py-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
            </div>
          )}
        </div>
      )}

      {!history.length && loading && (
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-4">
          <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <textarea
          rows={3}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
          placeholder="e.g. What is the last date to submit queries?  ·  Is MSME EMD exemption available?"
          disabled={loading}
          className="flex-1 text-sm border border-slate-300 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 bg-slate-50 placeholder:text-slate-400 disabled:opacity-60"
        />
        <button
          onClick={handleSubmit}
          disabled={!question.trim() || loading}
          className="self-end flex items-center gap-1.5 bg-[#1e3a5f] text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} Ask
        </button>
      </div>
      <p className="text-xs text-slate-400 mt-2">Powered by AI • answers grounded in uploaded documents • Press Enter to send</p>
    </div>
  );
}

// ── MAIN COMPONENT ────────────────────────────────────────────────────────────

export default function TenderAnalysisView({
  analysis, loading, tenderStatus, tenderFilename, tenderId, criteria = [], onReanalyze,
}: Props) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const fname = tenderFilename
    ? tenderFilename.replace(/^[0-9a-f-]+_/, "")
    : undefined;

  const counts: Record<TabId, number> = {
    overview:    0,
    documents:   analysis?.documents?.length    ?? 0,
    items:       analysis?.items?.length        ?? 0,
    scope:       analysis?.scope_of_work?.length ?? 0,
    eligibility: Math.max(analysis?.eligibility?.length ?? 0, criteria.length),
    contacts:    analysis?.contacts?.length      ?? 0,
    followup:    0,
  };

  const isLoading = loading || tenderStatus === "processing";

  // Show re-analyse banner if all main sections are empty but criteria exist
  const allSectionsEmpty = analysis && !isLoading &&
    !analysis.documents?.length && !analysis.scope_of_work?.length &&
    !analysis.contacts?.length && !analysis.items?.length;

  return (
    <div>
      {/* Tab bar */}
      <div className="flex items-center gap-1 mb-4 flex-wrap">
        {TABS.map(({ id, label, icon: Icon }) => {
          const isActive = activeTab === id;
          const count = counts[id];
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                isActive
                  ? "bg-[#1e3a5f] text-white border-[#1e3a5f]"
                  : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
              {count > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  isActive ? "bg-white/20 text-white" : "bg-slate-100 text-slate-500"
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Re-analyse banner */}
      {allSectionsEmpty && onReanalyze && (
        <div className="flex items-center justify-between gap-3 text-sm bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 mb-3">
          <div className="flex items-center gap-2 text-blue-700">
            <Info className="w-4 h-4 shrink-0" />
            <span>AI sections are empty — this tender may have been uploaded before the latest analysis version.</span>
          </div>
          <button
            onClick={onReanalyze}
            className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 bg-white border border-blue-300 px-3 py-1.5 rounded-full hover:bg-blue-100 transition-colors shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Re-analyse
          </button>
        </div>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-3 border border-slate-200 rounded-xl bg-white">
          <Loader2 className="w-7 h-7 animate-spin" />
          <p className="text-sm font-medium">Analysing tender document...</p>
          <p className="text-xs">Overview · Documents · Eligibility · Contacts · Items</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 h-[calc(100vh-250px)] min-h-[500px] overflow-y-auto pr-2">

          {activeTab === "overview" && (
            analysis
              ? <OverviewTab analysis={analysis} onReanalyze={onReanalyze} />
              : <EmptyState tab="overview" onReanalyze={onReanalyze} />
          )}

          {activeTab === "documents" && (
            <DocumentsTab documents={analysis?.documents ?? []} filename={fname} onReanalyze={onReanalyze} />
          )}

          {activeTab === "items" && (
            <ItemsTab items={analysis?.items ?? []} filename={fname} onReanalyze={onReanalyze} />
          )}

          {activeTab === "scope" && (
            <>
              <div className="mb-0.5">
                <h3 className="text-sm font-bold text-slate-700">Scope of Work</h3>
              </div>
              {(analysis?.scope_of_work?.length ?? 0) === 0
                ? <EmptyState tab="scope" onReanalyze={onReanalyze} />
                : analysis!.scope_of_work.map((item, i) => (
                    <ScopeCard key={i} item={item} filename={fname} />
                  ))}
            </>
          )}

          {activeTab === "eligibility" && (
            <>
              <div className="mb-0.5">
                <h3 className="text-sm font-bold text-slate-700">Eligibility Requirements</h3>
              </div>
              <EligibilityTabContent
                analysisItems={analysis?.eligibility ?? []}
                criteria={criteria}
                filename={fname}
                onReanalyze={onReanalyze}
              />
            </>
          )}

          {activeTab === "contacts" && (
            <>
              <div className="mb-0.5">
                <h3 className="text-sm font-bold text-slate-700">Authority & Contact Details</h3>
              </div>
              {(analysis?.contacts?.length ?? 0) === 0
                ? <EmptyState tab="contacts" onReanalyze={onReanalyze} />
                : analysis!.contacts.map((item, i) => (
                    <ContactCard key={i} item={item} filename={fname} />
                  ))}
            </>
          )}

          {activeTab === "followup" && <FollowUpTab tenderId={tenderId} />}
        </div>
      )}
    </div>
  );
}
