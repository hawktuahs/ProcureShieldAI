"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listTenders, uploadTender, Tender } from "@/lib/api";
import FileUpload from "@/components/FileUpload";
import OllamaAlert from "@/components/OllamaAlert";
import { PlusCircle, FileText, ChevronRight, Loader2, X, CheckCircle2, AlertCircle } from "lucide-react";

export default function HomePage() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const fetchTenders = useCallback(async () => {
    try {
      const res = await listTenders();
      setTenders(res.data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchTenders().finally(() => setLoading(false));
    // Poll every 4 seconds to pick up processing completions
    const interval = setInterval(fetchTenders, 4000);
    return () => clearInterval(interval);
  }, [fetchTenders]);

  const handleUpload = async (file: File) => {
    const res = await uploadTender(file);
    setUploadSuccess(res.data.name);
    setShowUpload(false);
    await fetchTenders();
    setTimeout(() => setUploadSuccess(null), 5000);
  };

  const statusBadge = (status: string) => {
    if (status === "processing") return (
      <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
        <Loader2 className="w-3 h-3 animate-spin" /> Processing
      </span>
    );
    if (status === "ready") return (
      <span className="flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">
        <CheckCircle2 className="w-3 h-3" /> Ready
      </span>
    );
    return (
      <span className="flex items-center gap-1 text-xs text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
        <AlertCircle className="w-3 h-3" /> Error
      </span>
    );
  };

  return (
    <div>
      <OllamaAlert />

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Tender Dashboard</h2>
          <p className="text-sm text-slate-500 mt-0.5">Upload tender documents to begin AI-powered eligibility evaluation</p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 bg-[#1e3a5f] text-white px-4 py-2.5 rounded-lg hover:bg-blue-800 transition-colors text-sm font-medium shadow-sm"
        >
          <PlusCircle className="w-4 h-4" /> Upload New Tender
        </button>
      </div>

      {uploadSuccess && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-green-600" />
          <p className="text-sm text-green-700">
            <span className="font-medium">{uploadSuccess}</span> uploaded. Extracting criteria in background...
          </p>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      ) : tenders.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-slate-200 rounded-xl">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 font-medium">No tenders yet</p>
          <p className="text-sm text-slate-400 mt-1">Upload a tender PDF to get started</p>
          <button
            onClick={() => setShowUpload(true)}
            className="mt-4 bg-[#1e3a5f] text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-800"
          >
            Upload Tender
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tenders.map((tender) => (
            <div key={tender.id} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col">
              <div className="flex items-start justify-between mb-3">
                <FileText className="w-8 h-8 text-blue-400 shrink-0" />
                {statusBadge(tender.status)}
              </div>
              <h3 className="font-semibold text-slate-800 text-sm leading-snug mb-1 line-clamp-2">{tender.name}</h3>
              <p className="text-xs text-slate-400 mb-3">
                {new Date(tender.upload_time).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
              </p>
              <div className="flex gap-4 text-xs text-slate-500 mb-4">
                <div><span className="font-semibold text-slate-700">{tender.criterion_count}</span> criteria</div>
                <div><span className="font-semibold text-slate-700">{tender.bidder_count}</span> bidders</div>
              </div>
              <div className="mt-auto">
                {tender.status === "ready" ? (
                  <Link
                    href={`/tender/${tender.id}`}
                    className="flex items-center justify-center gap-1 w-full bg-[#1e3a5f] text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors"
                  >
                    View Tender <ChevronRight className="w-4 h-4" />
                  </Link>
                ) : (
                  <div className="flex items-center justify-center gap-1 w-full bg-slate-100 text-slate-400 py-2 rounded-lg text-sm">
                    <Loader2 className="w-3 h-3 animate-spin" /> Processing...
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800">Upload Tender Document</h3>
              <button onClick={() => setShowUpload(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Upload the tender PDF. The system will automatically extract all eligibility criteria using AI.
              This may take 30–60 seconds.
            </p>
            <FileUpload onUpload={handleUpload} label="Drop tender PDF here" />
          </div>
        </div>
      )}
    </div>
  );
}
