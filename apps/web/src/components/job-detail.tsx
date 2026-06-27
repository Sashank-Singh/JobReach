"use client";

import { ExternalLink, Heart, Send, UserPlus, BadgeCheck } from "lucide-react";
import { Job, jobApi } from "@/lib/api";
import { JobDescription } from "@/components/job-description";
import { useEffect, useState } from "react";

interface Props {
  job: Job | null;
  onReferralStart: (jobId: string) => void;
  onCompanyClick: (companyId: string) => void;
  savedJobIds: Set<string>;
  appliedJobIds: Set<string>;
  onSaved: (jobId: string) => void;
  onApplied: (jobId: string) => void;
}

export function JobDetailPanel({
  job,
  onReferralStart,
  onCompanyClick,
  savedJobIds,
  appliedJobIds,
  onSaved,
  onApplied,
}: Props) {
  const [loading, setLoading] = useState<string | null>(null);
  const [detail, setDetail] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job) {
      setDetail(null);
      return;
    }
    setDetail(job);
    jobApi
      .getJob(job.id)
      .then((d) => setDetail({ ...d, match_score: d.match_score ?? job.match_score }))
      .catch(() => setDetail(job));
  }, [job]);

  if (!job || !detail) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        Select a job to view details
      </div>
    );
  }

  const isSaved = savedJobIds.has(job.id);
  const isApplied = appliedJobIds.has(job.id);

  const action = async (type: "save" | "apply" | "referral") => {
    setLoading(type);
    setError(null);
    try {
      if (type === "save") {
        await jobApi.saveJob(job.id);
        onSaved(job.id);
      }
      if (type === "apply") {
        await jobApi.applyJob(job.id);
        onApplied(job.id);
      }
      if (type === "referral") {
        await jobApi.referralHandoff(job.id);
        onReferralStart(job.id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setLoading(null);
    }
  };

  const salary = detail.salary
    ? `$${(detail.salary.min_salary || 0).toLocaleString()} – $${(detail.salary.max_salary || 0).toLocaleString()}`
    : null;

  const posted = detail.posted_at
    ? new Date(detail.posted_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
    : null;

  return (
    <div className="h-full overflow-y-auto p-6">
      <div>
        <h1 className="text-xl font-semibold text-primary leading-tight">{detail.title}</h1>
        <button
          onClick={() => onCompanyClick(detail.company.id)}
          className="text-secondary text-sm mt-1 hover:text-accent transition-colors"
        >
          {detail.company.name}
        </button>
        {detail.match_score != null && (
          <p className="text-sm mt-2 text-secondary">
            Match score: <span className="font-semibold text-primary">{Math.round(detail.match_score)}%</span>
          </p>
        )}
        {posted && <p className="text-xs text-muted mt-1">Posted {posted}</p>}
        {detail.apply_url && (
          <p className="flex items-center gap-1 text-xs text-muted mt-1">
            <BadgeCheck className="w-3.5 h-3.5 text-accent" />
            Verified listing on {detail.company.name}&apos;s careers site
          </p>
        )}
      </div>

      {error && <p className="text-sm text-red-400 mt-3">{error}</p>}

      <div className="flex flex-wrap gap-2 mt-4">
        <ActionButton
          icon={Heart}
          label={isSaved ? "Saved" : "Save"}
          loading={loading === "save"}
          onClick={() => action("save")}
          disabled={isSaved}
        />
        <ActionButton
          icon={Send}
          label={isApplied ? "Applied" : "Apply"}
          loading={loading === "apply"}
          onClick={() => action("apply")}
          primary
          disabled={isApplied}
        />
        <ActionButton
          icon={UserPlus}
          label="Request referral"
          loading={loading === "referral"}
          onClick={() => action("referral")}
          accent
        />
        {detail.apply_url && (
          <a
            href={detail.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md btn-secondary"
          >
            <ExternalLink className="w-4 h-4" />
            External Apply
          </a>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-6 text-sm">
        {detail.department && <Meta label="Department" value={detail.department} />}
        {detail.experience_level && <Meta label="Experience" value={detail.experience_level} />}
        {detail.remote_type && <Meta label="Work type" value={detail.remote_type} />}
        {salary && <Meta label="Salary" value={salary} />}
        {detail.visa_sponsorship != null && (
          <Meta label="Visa" value={detail.visa_sponsorship ? "Sponsored" : "Not listed"} />
        )}
        <Meta label="Source" value={detail.source} />
      </div>

      {detail.skills.length > 0 && (
        <div className="mt-6">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted mb-2">Skills</h3>
          <div className="flex flex-wrap gap-1.5">
            {detail.skills.map((s) => (
              <span key={s} className="chip">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {detail.description && (
        <div className="mt-6">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted mb-3">Description</h3>
          <JobDescription html={detail.description} />
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
  disabled,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  loading: boolean;
  onClick: () => void;
  primary?: boolean;
  accent?: boolean;
  disabled?: boolean;
}) {
  const cls = accent
    ? "btn-primary bg-[var(--accent)]"
    : primary
      ? "btn-primary"
      : "btn-secondary";

  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors disabled:opacity-50 ${cls}`}
    >
      <Icon className="w-4 h-4" />
      {loading ? "..." : label}
    </button>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-card">
      <div className="text-xs text-muted">{label}</div>
      <div className="text-sm text-primary capitalize mt-0.5">{value}</div>
    </div>
  );
}
