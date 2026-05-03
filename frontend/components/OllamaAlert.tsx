"use client";
import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";
import { AlertTriangle, X, Info } from "lucide-react";

interface Alert {
  type: "error" | "warn";
  title: string;
  message: string;
  hint?: string;
}

export default function OllamaAlert() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  useEffect(() => {
    checkHealth()
      .then((r) => {
        const d = r.data;
        const found: Alert[] = [];

        if (!d.ollama_ready) {
          found.push({
            type: "error",
            title: "LLM Service Unavailable",
            message: d.ollama_error || "Ollama is not running",
            hint: "ollama serve   (then: ollama pull llama3.1:8b)",
          });
        }

        if (d.ocr_issues && d.ocr_issues.length > 0) {
          found.push({
            type: "warn",
            title: "OCR Not Available — Scanned PDFs Will Fail",
            message: d.ocr_issues[0],
            hint: d.fitz_available === false
              ? "pip install pymupdf pytesseract Pillow"
              : "Windows: install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki  |  Linux: sudo apt install tesseract-ocr",
          });
        }

        setAlerts(found);
      })
      .catch(() => {
        setAlerts([{
          type: "error",
          title: "Backend Unreachable",
          message: "Cannot connect to the FastAPI backend on port 8000.",
          hint: "cd backend && python main.py",
        }]);
      });
  }, []);

  const visible = alerts.filter((_, i) => !dismissed.has(i));
  if (visible.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 mb-4">
      {alerts.map((alert, i) => {
        if (dismissed.has(i)) return null;
        const isError = alert.type === "error";
        return (
          <div
            key={i}
            className={`border rounded-lg p-4 flex items-start gap-3 ${
              isError
                ? "bg-red-50 border-red-200"
                : "bg-amber-50 border-amber-200"
            }`}
          >
            {isError
              ? <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              : <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            }
            <div className="flex-1">
              <p className={`text-sm font-semibold ${isError ? "text-red-800" : "text-amber-800"}`}>
                {alert.title}
              </p>
              <p className={`text-xs mt-0.5 ${isError ? "text-red-700" : "text-amber-700"}`}>
                {alert.message}
              </p>
              {alert.hint && (
                <p className={`text-xs mt-1 font-mono ${isError ? "text-red-600" : "text-amber-600"}`}>
                  <code className={`px-1 rounded ${isError ? "bg-red-100" : "bg-amber-100"}`}>
                    {alert.hint}
                  </code>
                </p>
              )}
            </div>
            <button
              onClick={() => setDismissed((p) => new Set(Array.from(p).concat(i)))}
              className={`shrink-0 ${isError ? "text-red-400 hover:text-red-600" : "text-amber-400 hover:text-amber-600"}`}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
