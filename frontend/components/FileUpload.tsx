"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface Props {
  onUpload: (file: File) => Promise<void>;
  label?: string;
  accept?: string;
  disabled?: boolean;
}

export default function FileUpload({ onUpload, label = "Upload PDF", accept = ".pdf", disabled = false }: Props) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return;
      const file = accepted[0];
      setFileName(file.name);
      setError(null);
      setDone(false);
      setUploading(true);
      try {
        await onUpload(file);
        setDone(true);
      } catch (e: any) {
        setError(e?.response?.data?.detail || e?.message || "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: disabled || uploading,
  });

  return (
    <div
      {...getRootProps()}
      className={`
        relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
        ${isDragActive
          ? "border-blue-500 bg-blue-50/80 scale-[1.01]"
          : done
          ? "border-emerald-400 bg-emerald-50/60"
          : error
          ? "border-red-300 bg-red-50/40"
          : "border-slate-300 bg-slate-50/50 hover:border-blue-400 hover:bg-blue-50/30"
        }
        ${disabled || uploading ? "opacity-60 cursor-not-allowed" : ""}
      `}
    >
      <input {...getInputProps()} />

      {/* Icon */}
      <div className="flex justify-center mb-3">
        {uploading ? (
          <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center">
            <Loader2 className="w-7 h-7 text-blue-500 animate-spin" />
          </div>
        ) : done ? (
          <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center">
            <CheckCircle2 className="w-7 h-7 text-emerald-500" />
          </div>
        ) : error ? (
          <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
            <AlertCircle className="w-7 h-7 text-red-400" />
          </div>
        ) : (
          <div className={`w-14 h-14 rounded-full flex items-center justify-center transition-colors ${isDragActive ? "bg-blue-100" : "bg-white border border-slate-200 shadow-sm"}`}>
            <UploadCloud className={`w-7 h-7 transition-colors ${isDragActive ? "text-blue-600" : "text-slate-400"}`} />
          </div>
        )}
      </div>

      {/* Primary text */}
      <p className="text-sm font-semibold text-slate-700 mb-1">
        {uploading
          ? "Uploading & processing…"
          : done
          ? "Upload complete!"
          : isDragActive
          ? "Drop your PDF here"
          : "Click to upload or drag & drop"}
      </p>

      {/* Secondary text */}
      {!uploading && !done && (
        <p className="text-xs text-slate-400">PDF files only · max 50 MB</p>
      )}

      {/* File name pill */}
      {fileName && (
        <div className="mt-3 inline-flex items-center gap-1.5 bg-white border border-slate-200 rounded-full px-3 py-1 shadow-sm">
          <FileText className="w-3 h-3 text-blue-500 shrink-0" />
          <span className="text-xs text-slate-600 font-medium max-w-[220px] truncate">{fileName}</span>
        </div>
      )}

      {/* Progress bar */}
      {uploading && (
        <div className="mt-4 h-1 bg-slate-100 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 rounded-full animate-pulse w-2/3" />
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-500 mt-2 font-medium">{error}</p>
      )}
    </div>
  );
}
