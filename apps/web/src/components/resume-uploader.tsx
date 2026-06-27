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
    <div className="px-4 py-3 border-b border-default space-y-2.5">
      <button
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm btn-secondary disabled:opacity-50"
      >
        <Upload className="w-4 h-4 text-muted" />
        {uploading ? "Uploading…" : "Upload resume"}
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
          <p className="text-xs text-muted mb-1.5">Skills from resume</p>
          <div className="flex flex-wrap gap-1">
            {skills.slice(0, 8).map((s) => (
              <span key={s} className="chip">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
