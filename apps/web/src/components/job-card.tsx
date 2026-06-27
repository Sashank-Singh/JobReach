"use client";

import { Building2, MapPin, Sparkles } from "lucide-react";
import { Job } from "@/lib/api";

interface Props {
  job: Job;
  selected: boolean;
  onClick: () => void;
}

export function JobCard({ job, selected, onClick }: Props) {
  const location = job.locations[0]?.city || job.remote_type || "—";

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 border-b border-zinc-800/80 transition-colors hover:bg-zinc-900/60 ${
        selected ? "bg-zinc-900 border-l-2 border-l-emerald-500" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-medium text-zinc-100 truncate">{job.title}</h3>
          <div className="flex items-center gap-1.5 mt-1 text-sm text-zinc-400">
            <Building2 className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">{job.company.name}</span>
          </div>
          <div className="flex items-center gap-1.5 mt-0.5 text-xs text-zinc-500">
            <MapPin className="w-3 h-3 shrink-0" />
            <span>{location}</span>
            {job.remote_type && (
              <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 capitalize">{job.remote_type}</span>
            )}
          </div>
        </div>
        {job.match_score != null && (
          <div className="flex items-center gap-1 shrink-0 px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold">
            <Sparkles className="w-3 h-3" />
            {job.match_score}%
          </div>
        )}
      </div>
      {job.skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {job.skills.slice(0, 4).map((s) => (
            <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
              {s}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}
