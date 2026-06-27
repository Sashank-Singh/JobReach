"use client";

import { BadgeCheck, MapPin } from "lucide-react";
import { Job } from "@/lib/api";

interface Props {
  job: Job;
  selected: boolean;
  onClick: () => void;
}

export function JobCard({ job, selected, onClick }: Props) {
  const loc = job.locations[0];
  const location =
    loc?.country && loc?.city && !loc.city.toLowerCase().includes(loc.country.toLowerCase())
      ? `${loc.city}, ${loc.country}`
      : loc?.country || loc?.city || job.remote_type || "—";
  const verified = Boolean(job.apply_url);

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3.5 border-b border-default transition-colors hover-surface ${
        selected ? "bg-muted border-l-2 border-l-[var(--accent)]" : "border-l-2 border-l-transparent"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-medium text-primary truncate leading-snug">{job.title}</h3>
          <p className="mt-1 text-sm text-secondary truncate">
            {job.company.name}
            {verified && (
              <span title="Verified listing" className="inline-flex align-middle ml-1 -mt-0.5">
                <BadgeCheck className="w-3.5 h-3.5 text-accent" />
              </span>
            )}
          </p>
          <div className="flex items-center gap-1.5 mt-1 text-xs text-muted">
            <MapPin className="w-3 h-3 shrink-0" />
            <span className="truncate">{location}</span>
            {job.remote_type && (
              <span className="chip capitalize shrink-0">{job.remote_type}</span>
            )}
          </div>
        </div>
        {job.match_score != null && (
          <span className="match-badge shrink-0">{Math.round(job.match_score)}%</span>
        )}
      </div>
      {job.skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2.5">
          {job.skills.slice(0, 4).map((s) => (
            <span key={s} className="chip">
              {s}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}
