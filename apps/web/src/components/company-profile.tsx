"use client";

import { useEffect, useState } from "react";
import { CompanyProfile, jobApi } from "@/lib/api";
import { Building2, Globe, TrendingUp, Users, X } from "lucide-react";

interface Props {
  companyId: string | null;
  onClose: () => void;
}

export function CompanyProfilePanel({ companyId, onClose }: Props) {
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);
    jobApi.getCompany(companyId).then(setCompany).finally(() => setLoading(false));
  }, [companyId]);

  if (!companyId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <h2 className="text-lg font-semibold text-zinc-100">{loading ? "Loading..." : company?.name}</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        {company && (
          <div className="space-y-4 text-sm">
            {company.website && (
              <a href={company.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-emerald-400 hover:underline">
                <Globe className="w-4 h-4" />
                {company.website.replace(/^https?:\/\//, "")}
              </a>
            )}
            <div className="grid grid-cols-2 gap-3">
              <Stat icon={TrendingUp} label="Hiring velocity" value={`${company.hiring_velocity ?? 0} open roles`} />
              <Stat icon={Users} label="Est. employees" value={company.employee_count?.toLocaleString() ?? "—"} />
              <Stat icon={Building2} label="Interview difficulty" value={`${company.interview_difficulty?.toFixed(1) ?? "—"} / 5`} />
              <Stat icon={Building2} label="Visa sponsorship" value={company.visa_sponsorship ? "Yes" : "Not listed"} />
            </div>
            <p className="text-zinc-400">{company.active_jobs} active jobs · ATS: {company.ats_type}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800">
      <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-1">
        <Icon className="w-3 h-3" />
        {label}
      </div>
      <div className="text-zinc-200">{value}</div>
    </div>
  );
}
