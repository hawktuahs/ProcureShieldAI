"use client";
import { useEffect, useState } from "react";
import { getAuditTrail, verifyAuditTrail, AuditEvent } from "@/lib/api";
import { ShieldCheck, ShieldAlert, Key, Clock, User, ChevronRight, Loader2, GitCommit } from "lucide-react";

interface Props {
  tenderId: number;
}

export default function AuditLogViewer({ tenderId }: Props) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [verification, setVerification] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getAuditTrail(tenderId),
      verifyAuditTrail(tenderId)
    ])
    .then(([evRes, verRes]) => {
      setEvents(evRes.data);
      setVerification(verRes.data);
    })
    .finally(() => setLoading(false));
  }, [tenderId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
        <p>Verifying cryptographic hash chain...</p>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-xl text-slate-400 text-sm">
        No audit events recorded yet.
      </div>
    );
  }

  const isValid = verification?.valid;

  return (
    <div className="space-y-6">
      {/* Verification Status Banner */}
      <div className={`p-4 rounded-xl border flex items-start gap-4 ${
        isValid 
          ? "bg-green-50 border-green-200" 
          : "bg-red-50 border-red-200"
      }`}>
        {isValid ? (
          <ShieldCheck className="w-6 h-6 text-green-600 shrink-0 mt-0.5" />
        ) : (
          <ShieldAlert className="w-6 h-6 text-red-600 shrink-0 mt-0.5" />
        )}
        <div>
          <h3 className={`font-bold ${isValid ? "text-green-800" : "text-red-800"}`}>
            {isValid ? "Cryptographic Chain Verified" : "Chain Integrity Broken!"}
          </h3>
          <p className={`text-sm mt-1 ${isValid ? "text-green-700" : "text-red-700"}`}>
            {isValid 
              ? `All ${verification.event_count} events have been cryptographically verified against their SHA-256 signatures. The ledger has not been tampered with.`
              : `Tampering detected at event ID ${verification.broken_at}. The SHA-256 hashes no longer match.`
            }
          </p>
        </div>
      </div>

      {/* Hash Chain Timeline */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center gap-2">
          <Key className="w-4 h-4 text-slate-500" />
          <h3 className="font-semibold text-slate-700">Immutable Event Ledger</h3>
        </div>
        
        <div className="p-6">
          <div className="relative border-l-2 border-slate-200 ml-3 space-y-8 pb-4">
            {events.map((ev, idx) => (
              <div key={ev.id} className="relative pl-8">
                {/* Timeline Dot */}
                <div className="absolute -left-[11px] top-1 w-5 h-5 rounded-full bg-white border-2 border-blue-500 flex items-center justify-center shadow-sm">
                  <div className="w-2 h-2 bg-blue-500 rounded-full" />
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-slate-100 border border-slate-200 text-slate-700 text-xs font-bold rounded">
                        {ev.event_type}
                      </span>
                      <span className="text-xs text-slate-400 font-mono">ID: {ev.id}</span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <User className="w-3.5 h-3.5" />
                        {ev.actor} ({ev.actor_type})
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {new Date(ev.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* Payload Data */}
                  <div className="bg-slate-50 rounded border border-slate-100 p-3 mb-3 font-mono text-[11px] text-slate-600 overflow-x-auto">
                    {JSON.stringify(ev.payload, null, 2)}
                  </div>

                  {/* Hash Visualizer */}
                  <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono bg-slate-800 p-2 rounded">
                    <GitCommit className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400">SHA-256:</span>
                    <span className="truncate" title={ev.hash}>{ev.hash}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
