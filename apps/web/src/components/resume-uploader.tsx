"use client";

import { Upload } from "lucide-react";
import { jobApi, ResumeData } from "@/lib/api";
import { useRef, useState } from "react";

interface Props {
  onResumeUploaded: (resume: ResumeData) => void;
  latestResume?: ResumeData | null;
}

export function ResumeUploader({ onResumeUploaded, latestResume }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const resume = await jobApi.uploadResume(file);
      onResumeUploaded(resume);
    } finally {
      setUploading(false);
    }
  };

  const skills = latestResume?.parsed_data?.skills ?? [];

  return (
    <div className="p-3 border-b border-zinc-800 space-y-2">
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
      {skills.length > 0 && (
        <div>
          <p className="text-[10px] text-zinc-500 mb-1">Your skills</p>
          <div className="flex flex-wrap gap-1">
            {skills.slice(0, 8).map((s) => (
              <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
