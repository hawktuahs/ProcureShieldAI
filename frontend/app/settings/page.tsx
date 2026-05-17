"use client";
import { useState } from "react";
import { Settings2, Database, Cpu, Shield, Save, CheckCircle2, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const [geminiKey, setGeminiKey] = useState("");

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">Configure the ProcureShield AI platform</p>
      </div>

      {/* AI Provider */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">AI Provider</h2>
        <Card className="border border-slate-200">
          <CardHeader className="pb-3 px-5 pt-4">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-slate-700">LLM Configuration</h3>
            </div>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col gap-5">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex-1">
                <p className="text-sm font-semibold text-slate-700">Local Ollama</p>
                <p className="text-xs text-slate-500 mt-0.5">Runs on <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px]">localhost:11434</code> — no API key required. Set <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px]">LLM_PROVIDER=ollama</code> in your environment.</p>
              </div>
            </div>

            <div className="flex items-start justify-between gap-4 p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <div className="flex-1">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">Google Gemini</p>
                    <p className="text-xs text-slate-500 mt-0.5">Cloud-based provider (Default). Key is pre-configured for this session.</p>
                  </div>
                  <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-blue-600 hover:underline">
                    Get key <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="flex gap-2">
                  <Input
                    type="password"
                    placeholder="AIza..."
                    value={geminiKey || "••••••••••••••••••••••••••••••••••••••"}
                    disabled
                    className="font-mono text-sm"
                  />
                  <Badge variant="outline" className="text-emerald-600 bg-emerald-50 border-emerald-200 shrink-0 h-9 flex items-center px-3">Active</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Database */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Database</h2>
        <Card className="border border-slate-200">
          <CardContent className="px-5 py-4 flex items-center gap-4">
            <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center">
              <Database className="w-4 h-4 text-slate-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-700">SQLite (Local)</p>
              <p className="text-xs text-slate-500 mt-0.5">
                File: <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px]">backend/tendereval.db</code> — All tender extractions, criteria, bidder evaluations, and audit logs are stored here.
              </p>
            </div>
            <Badge variant="outline" className="text-emerald-600 bg-emerald-50 border-emerald-200">Connected</Badge>
          </CardContent>
        </Card>
      </section>

      {/* Security */}
      <section className="mb-6">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Security & Compliance</h2>
        <Card className="border border-slate-200">
          <CardContent className="px-5 py-4 flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <Shield className="w-4 h-4 text-blue-600 shrink-0" />
              <p className="text-xs text-slate-600">All AI verdicts are stored with cryptographic audit trail. Human overrides are tracked separately.</p>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <p className="text-xs text-slate-600">Confidence thresholds are configurable via <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px]">CONFIDENCE_REVIEW_THRESHOLD</code> env variable (default: 0.75).</p>
            </div>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <p className="text-xs text-slate-600">No data is sent to external services unless Gemini/OpenAI provider is explicitly configured.</p>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Version */}
      <div className="text-xs text-slate-400 text-center">
        ProcureShield AI v1.0 · CRPF / AI for Bharat · For official use only
      </div>
    </div>
  );
}
