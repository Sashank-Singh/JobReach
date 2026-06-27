"use client";

import { Upload } from "lucide-react";
import { jobApi } from "@/lib/api";
import { useRef, useState } from "react";

interface Props {
  onResumeUploaded: (resumeId: string) => void;
}

export function ResumeUploader({ onResumeUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const resume = await jobApi.uploadResume(file);
      onResumeUploaded(resume.id);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-3 border-b border-zinc-800">
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm rounded-lg border border-dashed border-zinc-700 text-zinc-400 hover:border-emerald-600 hover:text-emerald-400 transition-colors"
      >
        <Upload className="w-4 h-4" />
        {uploading ? "Parsing resume..." : "Upload resume for AI matching"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.doc,.docx"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
      />
    </div>
  );
}
