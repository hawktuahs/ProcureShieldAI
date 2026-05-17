"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listTenders, uploadTender, Tender } from "@/lib/api";
import FileUpload from "@/components/FileUpload";
import OllamaAlert from "@/components/OllamaAlert";
import {
  PlusCircle, FileText, ChevronRight, Loader2, X,
  CheckCircle2, AlertCircle, Search, MapPin, Calendar,
  IndianRupee, TrendingUp, Users, Clock, ShieldCheck,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const fetchTenders = useCallback(async () => {
    try {
      const res = await listTenders();
      setTenders(res.data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchTenders().finally(() => setLoading(false));
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

  const filtered = tenders.filter(t =>
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    (t.work_description || "").toLowerCase().includes(search.toLowerCase()) ||
    (t.location || "").toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: tenders.length,
    ready: tenders.filter(t => t.status === "ready").length,
    processing: tenders.filter(t => t.status === "processing").length,
    totalBidders: tenders.reduce((a, t) => a + (t.bidder_count || 0), 0),
  };

  const statusBadge = (status: string) => {
    if (status === "processing") return (
      <Badge variant="outline" className="flex items-center gap-1 text-amber-600 bg-amber-50 border-amber-200 text-[10px]">
        <Loader2 className="w-2.5 h-2.5 animate-spin" /> Processing
      </Badge>
    );
    if (status === "ready") return (
      <Badge variant="outline" className="flex items-center gap-1 text-emerald-700 bg-emerald-50 border-emerald-200 text-[10px]">
        <CheckCircle2 className="w-2.5 h-2.5" /> Ready
      </Badge>
    );
    return (
      <Badge variant="outline" className="flex items-center gap-1 text-red-600 bg-red-50 border-red-200 text-[10px]">
        <AlertCircle className="w-2.5 h-2.5" /> Error
      </Badge>
    );
  };

  return (
    <div>
      <OllamaAlert />

      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Tender Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">AI-powered eligibility evaluation for government procurement</p>
        </div>
        <Button onClick={() => setShowUpload(true)} className="bg-[#1e3a5f] hover:bg-blue-800 gap-2">
          <PlusCircle className="w-4 h-4" /> Upload Tender
        </Button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Tenders", value: stats.total, icon: FileText, color: "text-blue-600", bg: "bg-blue-50" },
          { label: "Ready to Evaluate", value: stats.ready, icon: ShieldCheck, color: "text-emerald-600", bg: "bg-emerald-50" },
          { label: "Processing", value: stats.processing, icon: Clock, color: "text-amber-600", bg: "bg-amber-50" },
          { label: "Total Bidders", value: stats.totalBidders, icon: Users, color: "text-purple-600", bg: "bg-purple-50" },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <Card key={label} className="border border-slate-200">
            <CardContent className="p-4 flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center shrink-0`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{value}</p>
                <p className="text-xs text-slate-500">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Search bar */}
      <div className="relative mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <Input
          placeholder="Search tenders by name, description, or location..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="pl-9 bg-white border-slate-200 text-sm h-10"
        />
        {search && (
          <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {uploadSuccess && (
        <div className="mb-4 bg-emerald-50 border border-emerald-200 rounded-lg p-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <p className="text-sm text-emerald-700">
            <span className="font-medium">{uploadSuccess}</span> uploaded successfully. Extracting criteria in background…
          </p>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-slate-200 rounded-xl bg-white">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 font-medium">
            {search ? "No tenders match your search" : "No tenders yet"}
          </p>
          <p className="text-sm text-slate-400 mt-1">
            {search ? "Try a different keyword" : "Upload a tender PDF to get started"}
          </p>
          {!search && (
            <Button
              onClick={() => setShowUpload(true)}
              className="mt-4 bg-[#1e3a5f] hover:bg-blue-800"
              size="sm"
            >
              Upload Tender
            </Button>
          )}
        </div>
      ) : (
        <>
          <p className="text-xs text-slate-400 mb-3">{filtered.length} tender{filtered.length !== 1 ? "s" : ""} {search ? "matching" : "total"}</p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((tender) => (
              <Card key={tender.id} className="hover:shadow-md transition-all border-slate-200 flex flex-col h-full group">
                <CardHeader className="pb-2 pt-4 px-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-slate-800 text-sm leading-snug line-clamp-2">{tender.name}</h3>
                      {tender.work_description && tender.work_description !== tender.name && (
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{tender.work_description}</p>
                      )}
                    </div>
                    {statusBadge(tender.status)}
                  </div>
                </CardHeader>

                <CardContent className="px-4 pb-3 flex-1">
                  {/* Meta row */}
                  <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 mb-3">
                    {tender.tender_type && (
                      <span className="flex items-center gap-1 text-[10px] text-slate-500 font-medium">
                        <TrendingUp className="w-3 h-3 text-blue-400" />
                        {tender.tender_type}
                      </span>
                    )}
                    {tender.location && (
                      <span className="flex items-center gap-1 text-[10px] text-slate-500">
                        <MapPin className="w-3 h-3 text-rose-400" />
                        {tender.location}
                      </span>
                    )}
                    {tender.bid_opening_date && (
                      <span className="flex items-center gap-1 text-[10px] text-slate-500">
                        <Calendar className="w-3 h-3 text-amber-400" />
                        Bid Opening: {tender.bid_opening_date}
                      </span>
                    )}
                    {tender.emd_fee_amount && (
                      <span className="flex items-center gap-1 text-[10px] text-slate-500">
                        <IndianRupee className="w-3 h-3 text-emerald-500" />
                        EMD {tender.emd_fee_amount}
                      </span>
                    )}
                    {tender.total_quantity && (
                      <span className="flex items-center gap-1 text-[10px] text-slate-500">
                        <Package className="w-3 h-3 text-purple-500" />
                        Qty: {tender.total_quantity} {tender.quantity_unit || ""}
                      </span>
                    )}
                  </div>

                  {/* Stats */}
                  <div className="flex gap-3">
                    <div className={`border rounded-lg px-3 py-1.5 flex-1 text-center ${
                      tender.criterion_count === 0 && tender.status === "ready"
                        ? "bg-amber-50 border-amber-200"
                        : "bg-slate-50 border-slate-100"
                    }`}>
                      <p className={`text-base font-bold ${
                        tender.criterion_count === 0 && tender.status === "ready"
                          ? "text-amber-600"
                          : "text-slate-700"
                      }`}>{tender.criterion_count}</p>
                      <p className="text-[10px] text-slate-400">
                        {tender.criterion_count === 0 && tender.status === "ready" ? "Re-analyze" : "Criteria"}
                      </p>
                    </div>
                    <div className="bg-slate-50 border border-slate-100 rounded-lg px-3 py-1.5 flex-1 text-center">
                      <p className="text-base font-bold text-slate-700">{tender.bidder_count}</p>
                      <p className="text-[10px] text-slate-400">Bidders</p>
                    </div>
                    <div className="bg-slate-50 border border-slate-100 rounded-lg px-3 py-1.5 flex-1 text-center">
                      <p className="text-[10px] font-medium text-slate-500">
                        {new Date(tender.upload_time).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                      </p>
                      <p className="text-[10px] text-slate-400">Uploaded</p>
                    </div>
                  </div>
                </CardContent>

                <CardFooter className="px-4 pb-4 pt-0">
                  {tender.status === "ready" ? (
                    <Link
                      href={`/tender/${tender.id}`}
                      className="flex items-center justify-center gap-1.5 w-full bg-[#1e3a5f] text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-800 transition-colors group-hover:shadow-sm"
                    >
                      View Tender <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                    </Link>
                  ) : (
                    <div className="flex items-center justify-center gap-1.5 w-full bg-slate-100 text-slate-400 py-2 rounded-lg text-sm cursor-not-allowed">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing…
                    </div>
                  )}
                </CardFooter>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={e => e.target === e.currentTarget && setShowUpload(false)}>
          <div className="w-full max-w-[460px] bg-white rounded-2xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-[#0f172a] px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-blue-500 flex items-center justify-center">
                  <PlusCircle className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Upload Tender Document</h3>
                  <p className="text-[10px] text-slate-400">AI extracts all criteria automatically</p>
                </div>
              </div>
              <button
                onClick={() => setShowUpload(false)}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-5">
              <FileUpload onUpload={handleUpload} label="Click to upload or drag & drop" />
              <div className="mt-4 flex items-start gap-2 text-xs text-slate-400 bg-slate-50 border border-slate-100 rounded-lg px-3 py-2.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                <span>The AI will run in background — you can upload more tenders while it processes (30–90 seconds per document).</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
