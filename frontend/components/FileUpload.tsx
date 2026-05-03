"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Loader2 } from "lucide-react";

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

  const onDrop = useCallback(
    async (accepted: File[]) => {
      if (!accepted.length) return;
      const file = accepted[0];
      setFileName(file.name);
      setError(null);
      setUploading(true);
      try {
        await onUpload(file);
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
        border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
        ${isDragActive ? "border-blue-500 bg-blue-50" : "border-slate-300 hover:border-blue-400 hover:bg-slate-50"}
        ${disabled || uploading ? "opacity-60 cursor-not-allowed" : ""}
      `}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2">
        {uploading ? (
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        ) : (
          <Upload className="w-8 h-8 text-slate-400" />
        )}
        <p className="text-sm font-medium text-slate-600">
          {uploading ? "Uploading..." : isDragActive ? "Drop file here" : label}
        </p>
        {fileName && !uploading && (
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <FileText className="w-3 h-3" /> {fileName}
          </div>
        )}
        {!uploading && <p className="text-xs text-slate-400">PDF files only · drag & drop or click</p>}
        {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
      </div>
    </div>
  );
}
