"use client";
import { createContext, useContext, useState, useCallback } from "react";
import { ExternalLink, FileText, BookOpen, X, Quote, AlertCircle } from "lucide-react";

// ── Provenance Context ────────────────────────────────────────────────────────
interface ProvenanceCtx {
  openProvenance: (page: number, quote?: string) => void;
}

const ProvenanceContext = createContext<ProvenanceCtx>({ openProvenance: () => {} });
export const useProvenance = () => useContext(ProvenanceContext);
export default SplitWorkspace;

// ── SplitWorkspace ────────────────────────────────────────────────────────────
interface Props {
  fileUrl: string;
  children: React.ReactNode;
}

function SplitWorkspace({ fileUrl, children }: Props) {
  const [currentPage, setCurrentPage] = useState(1);
  const [evidenceQuote, setEvidenceQuote] = useState<string | undefined>(undefined);
  const [iframeKey, setIframeKey] = useState(0);

  const openProvenance = useCallback((page: number, quote?: string) => {
    setCurrentPage(page);
    setEvidenceQuote(quote || undefined);
    // Bump key to force embed to re-navigate to the new page
    setIframeKey(prev => prev + 1);
  }, []);

  const iframeSrc = `${fileUrl}#page=${currentPage}`;

  return (
    <ProvenanceContext.Provider value={{ openProvenance }}>
      <div className="flex h-[calc(100vh-145px)] gap-4">
        {/* Left Pane */}
        <div className="w-[58%] overflow-y-auto pr-1 custom-scrollbar">
          {children}
        </div>

        {/* Right Pane — Perpetual PDF Viewer */}
        <div className="w-[42%] bg-[#0f172a] rounded-xl shadow-2xl overflow-hidden flex flex-col border border-slate-700/60">
          {/* Header bar */}
          <div className="bg-[#1e293b] px-4 py-2.5 flex items-center justify-between shrink-0 border-b border-slate-700/60">
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
              </div>
              <span className="text-xs font-semibold text-slate-300 ml-1">Document Viewer</span>
              {currentPage > 1 && (
                <span className="bg-blue-500/20 text-blue-300 text-[10px] font-bold px-2 py-0.5 rounded-full border border-blue-500/30">
                  Page {currentPage}
                </span>
              )}
            </div>
            <a
              href={iframeSrc}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-white/10"
              title="Open in new tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          {/* Evidence quote banner */}
          {evidenceQuote && (
            <div className="bg-amber-500/15 border-b border-amber-500/25 px-4 py-2.5 flex items-start gap-2.5 shrink-0">
              <Quote className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-0.5">AI Evidence Source</p>
                <p className="text-xs text-amber-100/90 leading-relaxed italic line-clamp-3">&ldquo;{evidenceQuote}&rdquo;</p>
              </div>
              <button
                onClick={() => setEvidenceQuote(undefined)}
                className="text-amber-400/60 hover:text-amber-300 shrink-0 mt-0.5"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* No file state */}
          {!fileUrl ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-500">
              <FileText className="w-12 h-12 text-slate-700" />
              <p className="text-sm">No document loaded</p>
            </div>
          ) : (
            <div className="flex-1 bg-slate-100 overflow-hidden">
              <embed
                key={iframeKey}
                src={iframeSrc}
                type="application/pdf"
                className="w-full h-full border-none"
                title="PDF Document Viewer"
              />
            </div>
          )}

          {/* Footer */}
          <div className="bg-[#1e293b] px-4 py-2 flex items-center gap-2 shrink-0 border-t border-slate-700/60">
            <BookOpen className="w-3 h-3 text-slate-500" />
            <p className="text-[10px] text-slate-500">
              {evidenceQuote
                ? "Click any citation badge on the left to jump to the source page"
                : "Click any 📄 Page badge on the left to navigate the document"}
            </p>
          </div>
        </div>
      </div>
    </ProvenanceContext.Provider>
  );
}
