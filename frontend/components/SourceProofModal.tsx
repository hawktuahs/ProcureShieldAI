"use client";
import { useState, useEffect, useCallback } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, FileText, Loader2, ExternalLink, ZoomIn, ZoomOut, AlertCircle } from "lucide-react";
import { getSourceProof, getPageImageUrl, SourceProofResult } from "@/lib/api";

interface SourceProofModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenderId: number;
  sourceText: string;
  pageHint?: number | null;
  title?: string;
}

export default function SourceProofModal({
  open,
  onOpenChange,
  tenderId,
  sourceText,
  pageHint,
  title,
}: SourceProofModalProps) {
  const [loading, setLoading] = useState(false);
  const [proof, setProof] = useState<SourceProofResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const fetchProof = useCallback(async () => {
    if (!sourceText || !tenderId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getSourceProof(tenderId, sourceText, pageHint);
      setProof(res.data);
      // Build full image URL
      const url = getPageImageUrl(tenderId, res.data.page, res.data.bbox);
      setImageUrl(url);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to locate source in document");
    } finally {
      setLoading(false);
    }
  }, [tenderId, sourceText, pageHint]);

  useEffect(() => {
    if (open) {
      setZoom(1);
      setProof(null);
      setImageUrl(null);
      fetchProof();
    }
  }, [open, fetchProof]);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-[50%] top-[50%] z-50 translate-x-[-50%] translate-y-[-50%] w-[95vw] max-w-[900px] max-h-[90vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-gradient-to-r from-[#1e3a5f] to-[#2d5a8e]">
            <div className="flex items-center gap-2.5 text-white min-w-0">
              <FileText className="w-4.5 h-4.5 shrink-0" />
              <div className="min-w-0">
                <Dialog.Title className="text-sm font-semibold truncate">
                  {title || "Source Evidence"}
                </Dialog.Title>
                {proof && (
                  <p className="text-xs text-blue-200 mt-0.5">
                    Page {proof.page} of {proof.page_count} &middot; Confidence: {Math.round(proof.confidence * 100)}%
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              {/* Zoom controls */}
              <button onClick={handleZoomOut} className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors" title="Zoom out">
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-xs text-white/70 w-10 text-center">{Math.round(zoom * 100)}%</span>
              <button onClick={handleZoomIn} className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors" title="Zoom in">
                <ZoomIn className="w-4 h-4" />
              </button>
              <Dialog.Close className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors ml-1">
                <X className="w-4 h-4" />
              </Dialog.Close>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin" />
                <p className="text-sm font-medium">Locating source in document...</p>
                <p className="text-xs">Searching for matching text region</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3 text-red-400">
                <AlertCircle className="w-8 h-8" />
                <p className="text-sm font-medium">{error}</p>
              </div>
            ) : imageUrl ? (
              <div className="p-4 flex justify-center bg-slate-100 min-h-[400px]">
                <div style={{ transform: `scale(${zoom})`, transformOrigin: "top center", transition: "transform 0.2s ease" }}>
                  <img
                    src={imageUrl}
                    alt={`Tender page ${proof?.page || ""} with highlighted source region`}
                    className="max-w-full rounded-lg shadow-lg border border-slate-300"
                    style={{ imageRendering: "auto" }}
                  />
                </div>
              </div>
            ) : null}
          </div>

          {/* Footer — Source text preview */}
          <div className="px-5 py-3 border-t border-slate-200 bg-slate-50">
            <div className="flex items-start gap-2">
              <div className="shrink-0 mt-0.5">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-slate-500 mb-1">Extracted Source Text</p>
                <p className="text-xs text-slate-700 leading-relaxed line-clamp-3 italic">
                  &ldquo;{sourceText}&rdquo;
                </p>
              </div>
            </div>
            {proof && !proof.found && (
              <div className="mt-2 flex items-center gap-1.5 text-amber-600 text-xs">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>Exact match not found — showing best estimated page location</span>
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
