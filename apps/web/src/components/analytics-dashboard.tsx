"use client";

import { useQuery } from "@tanstack/react-query";
import { jobApi } from "@/lib/api";
import { Loader2, Briefcase, Building2, Globe, BadgeCheck } from "lucide-react";

export function AnalyticsDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: jobApi.getAnalytics,
    refetchInterval: 60_000,
  });

  if (isLoading || !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-5">
      <h2 className="text-sm font-medium text-primary">Market Analytics</h2>

      <div className="grid grid-cols-4 gap-3">
        <StatCard icon={Briefcase} label="Active Jobs" value={data.total_jobs.toLocaleString()} />
        <StatCard icon={Building2} label="Companies" value={data.total_companies.toLocaleString()} />
        <StatCard icon={Globe} label="Remote" value={`${data.remote_job_pct}%`} />
        <StatCard icon={BadgeCheck} label="Visa Sponsorship" value={`${data.visa_sponsorship_pct}%`} />
      </div>

      <Section title="Most In-Demand Skills">
        <div className="space-y-2">
          {data.skills_demand.slice(0, 20).map((s) => {
            const maxCount = data.skills_demand[0]?.count || 1;
            const pct = (s.count / maxCount) * 100;
            return (
              <div key={s.skill} className="flex items-center gap-3 text-sm">
                <span className="w-28 shrink-0 text-secondary truncate text-right">{s.skill}</span>
                <div className="flex-1 h-5 bg-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent/60 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-12 text-xs text-muted text-right">{s.count}</span>
              </div>
            );
          })}
        </div>
      </Section>

      {data.salary_by_experience.length > 0 && (
        <Section title="Salary by Experience Level">
          <div className="grid grid-cols-3 gap-3">
            {data.salary_by_experience.map((s) => (
              <div key={s.level} className="meta-card">
                <div className="text-xs text-muted capitalize">{s.level}</div>
                <div className="text-sm text-primary font-medium mt-1">
                  ${(s.avg_min / 1000).toFixed(0)}k – ${(s.avg_max / 1000).toFixed(0)}k
                </div>
                <div className="text-[11px] text-muted mt-0.5">{s.count} jobs</div>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="Top Hiring Companies">
        <div className="grid grid-cols-2 gap-2">
          {data.top_hiring_companies.map((c) => (
            <div key={c.slug} className="meta-card flex items-center justify-between">
              <span className="text-sm text-primary">{c.name}</span>
              <span className="text-xs text-muted">{c.active_jobs} jobs</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Jobs by Source">
        <div className="space-y-2">
          {data.jobs_by_source.map((s) => {
            const total = data.jobs_by_source.reduce((a, b) => a + b.count, 0);
            const pct = total > 0 ? Math.round((s.count / total) * 100) : 0;
            return (
              <div key={s.source} className="flex items-center gap-3 text-sm">
                <span className="w-24 shrink-0 text-secondary capitalize">{s.source}</span>
                <div className="flex-1 h-5 bg-subtle rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--accent)]/40 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-16 text-xs text-muted text-right">{s.count} ({pct}%)</span>
              </div>
            );
          })}
        </div>
      </Section>
    </div>
  );
}

function StatCard({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) {
  return (
    <div className="meta-card">
      <Icon className="w-4 h-4 text-muted" />
      <div className="text-lg font-semibold text-primary mt-1">{value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted mb-3">{title}</h3>
      {children}
    </div>
  );
}
