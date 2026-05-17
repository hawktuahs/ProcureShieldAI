"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getTender, uploadBidder, listBidders,
  getTenderAnalysis, reanalyzeTender, getTenderFileUrl,
  Bidder, TenderAnalysisData, Criterion,
} from "@/lib/api";
import TenderAnalysisView from "@/components/TenderAnalysisView";
import BidderSummaryCard from "@/components/BidderSummaryCard";
import FileUpload from "@/components/FileUpload";
import SplitWorkspace from "@/components/SplitWorkspace";
import { ArrowLeft, BarChart2, Loader2, CheckCircle2 } from "lucide-react";

export default function TenderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const tenderId = parseInt(id);

  const [tender, setTender]             = useState<any>(null);
  const [criteria, setCriteria]         = useState<Criterion[]>([]);
  const [bidders, setBidders]           = useState<Bidder[]>([]);
  const [tenderStatus, setTenderStatus] = useState<string>("processing");
  const [analysis, setAnalysis]         = useState<TenderAnalysisData | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(true);
  const [loading, setLoading]           = useState(true);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [tenderRes, biddersRes] = await Promise.all([
        getTender(tenderId),
        listBidders(tenderId),
      ]);
      setTender(tenderRes.data);
      setTenderStatus(tenderRes.data.status);
      setCriteria(tenderRes.data.criteria || []);
      setBidders(biddersRes.data);

      if (tenderRes.data.status === "ready") {
        try {
          const analysisRes = await getTenderAnalysis(tenderId);
          setAnalysis(analysisRes.data);
          setAnalysisLoading(false);
        } catch {
          // analysis not yet available — keep polling
        }
      } else {
        // processing / error — keep spinner
        setAnalysisLoading(true);
      }
    } catch {}
  }, [tenderId]);

  useEffect(() => {
    fetchAll().finally(() => setLoading(false));
    const interval = setInterval(fetchAll, 4000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleBidderUpload = async (file: File) => {
    const res = await uploadBidder(tenderId, file);
    setUploadSuccess(res.data.name);
    await fetchAll();
    setTimeout(() => setUploadSuccess(null), 5000);
  };

  const handleReanalyze = async () => {
    setAnalysisLoading(true);
    setAnalysis(null);
    try {
      await reanalyzeTender(tenderId);
      // polling (4 s interval) will pick up status → processing → ready
    } catch (e: any) {
      setAnalysisLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4">
        <Link href="/" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft className="w-4 h-4" /> Dashboard
        </Link>
        <span className="text-slate-300">/</span>
        <span className="text-sm text-slate-700 font-medium truncate">{tender?.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">{tender?.name}</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {criteria.length > 0 && <><span className="font-medium text-slate-600">{criteria.length}</span> criteria extracted · </>}
            {bidders.length} bidder{bidders.length !== 1 ? "s" : ""} uploaded
          </p>
        </div>
        <Link
          href={`/tender/${tenderId}/compare`}
          className="flex items-center gap-2 border border-[#1e3a5f] text-[#1e3a5f] px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors"
        >
          <BarChart2 className="w-4 h-4" /> Compare All
        </Link>
      </div>

      <SplitWorkspace fileUrl={getTenderFileUrl(tenderId)}>
        <div className="flex flex-col gap-8 w-full">
          {/* TOP/LEFT: Tender Analysis */}
          <div>
            <TenderAnalysisView
              analysis={analysis}
              loading={analysisLoading}
              tenderStatus={tenderStatus}
              tenderFilename={tender?.name}
              tenderId={tenderId}
              criteria={criteria}
              onReanalyze={handleReanalyze}
            />
          </div>

        </div>
      </SplitWorkspace>

      {/* BOTTOM (Below Workspace): Bidder Submissions */}
      <div className="mt-12 mb-10 border-t border-slate-200 pt-8">
        <h3 className="font-bold text-xl text-slate-800 mb-4 font-serif">Bidder Submissions & Evaluation</h3>

        {tenderStatus !== "ready" ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4 text-sm text-amber-700 flex items-center gap-2 max-w-xl">
            <Loader2 className="w-4 h-4 animate-spin shrink-0" />
            Criteria extraction in progress. You can upload bidders once the tender is ready.
          </div>
        ) : (
          <div className="mb-6 max-w-xl">
            <FileUpload
              onUpload={handleBidderUpload}
              label="Upload Bidder Document"
            />
            {uploadSuccess && (
              <div className="mt-2 flex items-center gap-2 text-xs text-green-600 bg-green-50 p-2 rounded-md border border-green-200">
                <CheckCircle2 className="w-4 h-4" />
                <span><strong>{uploadSuccess}</strong> uploaded successfully. Evaluating in background...</span>
              </div>
            )}
          </div>
        )}

        {bidders.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-slate-200 rounded-xl text-slate-400 text-sm bg-slate-50 max-w-4xl">
            No bidders uploaded yet
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {bidders.map((b) => (
              <BidderSummaryCard key={b.id} bidder={b} tenderId={tenderId} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
