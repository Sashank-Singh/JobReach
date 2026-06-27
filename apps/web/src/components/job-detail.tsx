"use client";

import { ExternalLink, Heart, Send, UserPlus } from "lucide-react";
import { Job, jobApi } from "@/lib/api";
import { useState } from "react";

interface Props {
  job: Job | null;
  onReferralStart: (jobId: string) => void;
}

export function JobDetailPanel({ job, onReferralStart }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  if (!job) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
        Select a job to view details
      </div>
    );
  }

  const action = async (type: "save" | "apply" | "referral") => {
    setLoading(type);
    try {
      if (type === "save") await jobApi.saveJob(job.id);
      if (type === "apply") await jobApi.applyJob(job.id);
      if (type === "referral") {
        await jobApi.referralHandoff(job.id);
        onReferralStart(job.id);
      }
    } finally {
      setLoading(null);
    }
  };

  const salary = job.salary
    ? `$${(job.salary.min_salary || 0).toLocaleString()} – $${(job.salary.max_salary || 0).toLocaleString()}`
    : null;

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100">{job.title}</h1>
          <p className="text-zinc-400 mt-1">{job.company.name}</p>
          {job.match_score != null && (
            <p className="text-emerald-400 text-sm mt-2 font-medium">{job.match_score}% AI match</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mt-4">
        <ActionButton icon={Heart} label="Save" loading={loading === "save"} onClick={() => action("save")} />
        <ActionButton icon={Send} label="Apply" loading={loading === "apply"} onClick={() => action("apply")} primary />
        <ActionButton
          icon={UserPlus}
          label="Add Referral"
          loading={loading === "referral"}
          onClick={() => action("referral")}
          accent
        />
        {job.apply_url && (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            <ExternalLink className="w-4 h-4" />
            External Apply
          </a>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-6 text-sm">
        {job.department && <Meta label="Department" value={job.department} />}
        {job.experience_level && <Meta label="Experience" value={job.experience_level} />}
        {job.remote_type && <Meta label="Work type" value={job.remote_type} />}
        {salary && <Meta label="Salary" value={salary} />}
        {job.visa_sponsorship != null && (
          <Meta label="Visa" value={job.visa_sponsorship ? "Sponsored" : "Not listed"} />
        )}
        <Meta label="Source" value={job.source} />
      </div>

      {job.skills.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs uppercase tracking-wide text-zinc-500 mb-2">Skills</h3>
          <div className="flex flex-wrap gap-1.5">
            {job.skills.map((s) => (
              <span key={s} className="px-2 py-1 rounded-md bg-zinc-800 text-zinc-300 text-xs">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {job.description && (
        <div className="mt-6 prose prose-invert prose-sm max-w-none">
          <h3 className="text-xs uppercase tracking-wide text-zinc-500 mb-2 not-prose">Description</h3>
          <div
            className="text-zinc-300 text-sm leading-relaxed"
            dangerouslySetInnerHTML={{ __html: job.description.slice(0, 3000) }}
          />
        </div>
      )}
    </div>
  );
}

function ActionButton({
  icon: Icon,
  label,
  loading,
  onClick,
  primary,
  accent,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  loading: boolean;
  onClick: () => void;
  primary?: boolean;
  accent?: boolean;
}) {
  const cls = accent
    ? "bg-violet-600 hover:bg-violet-500 text-white"
    : primary
      ? "bg-emerald-600 hover:bg-emerald-500 text-white"
      : "border border-zinc-700 text-zinc-300 hover:bg-zinc-800";

  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors disabled:opacity-50 ${cls}`}
    >
      <Icon className="w-4 h-4" />
      {loading ? "..." : label}
    </button>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-zinc-900/80 border border-zinc-800">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="text-zinc-200 capitalize mt-0.5">{value}</div>
    </div>
  );
}
