"use client";

import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { JobFiltersPanel } from "@/components/job-filters";
import { JobCard } from "@/components/job-card";
import { JobDetailPanel } from "@/components/job-detail";
import { ResumeUploader } from "@/components/resume-uploader";
import { CompanyProfilePanel } from "@/components/company-profile";
import { NotificationsPanel } from "@/components/notifications-panel";
import { ApplicationKanban } from "@/components/application-kanban";
import { AnalyticsDashboard } from "@/components/analytics-dashboard";
import { ReferralPipelinePanel } from "@/components/referral-pipeline";
import { ThemeToggle } from "@/components/theme-toggle";
import { Job, JobFilters, jobApi, ResumeData } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { LogOut, Columns3, BarChart3, Briefcase } from "lucide-react";

type View = "jobs" | "pipeline" | "analytics";

export function JobDashboard() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const [view, setView] = useState<View>("jobs");
  const [filters, setFilters] = useState<JobFilters>({ page_size: 20 });
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [referralJobId, setReferralJobId] = useState<string | null>(null);
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [latestResume, setLatestResume] = useState<ResumeData | null>(null);

  const { data: savedJobs } = useQuery({
    queryKey: ["saved-jobs"],
    queryFn: jobApi.getSavedJobs,
  });

  const { data: applications } = useQuery({
    queryKey: ["applications"],
    queryFn: jobApi.getApplications,
  });

  const { data: resume } = useQuery({
    queryKey: ["resume"],
    queryFn: jobApi.getLatestResume,
  });

  useEffect(() => {
    if (savedJobs) setSavedIds(new Set(savedJobs.map((s) => s.job_id)));
  }, [savedJobs]);

  useEffect(() => {
    if (applications) setAppliedIds(new Set(applications.map((a) => a.job_id)));
  }, [applications]);

  useEffect(() => {
    if (resume) setLatestResume(resume);
  }, [resume]);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } = useInfiniteQuery({
    queryKey: ["jobs", filters],
    queryFn: ({ pageParam = 1 }) => jobApi.listJobs({ ...filters, page: pageParam }),
    getNextPageParam: (last) => (last.has_more ? last.page + 1 : undefined),
    initialPageParam: 1,
    enabled: view === "jobs",
  });

  const jobs = useMemo(() => {
    const seen = new Set<string>();
    return (data?.pages.flatMap((p) => p.jobs) ?? []).filter((job) => {
      if (seen.has(job.id)) return false;
      seen.add(job.id);
      return true;
    });
  }, [data]);
  const total = data?.pages[0]?.total ?? 0;
  const sortedByMatch = data?.pages[0]?.sorted_by_match ?? false;

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget;
      if (el.scrollHeight - el.scrollTop - el.clientHeight < 200 && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage]
  );

  useEffect(() => {
    if (jobs.length && !selectedJob) setSelectedJob(jobs[0]);
  }, [jobs, selectedJob]);

  // Listen for "select-job" custom event from job-detail "similar roles" clicks
  useEffect(() => {
    const handler = (e: Event) => {
      const jobId = (e as CustomEvent).detail;
      const found = jobs.find((j) => j.id === jobId);
      if (found) { setSelectedJob(found); setView("jobs"); }
    };
    window.addEventListener("select-job", handler);
    return () => window.removeEventListener("select-job", handler);
  }, [jobs]);

  return (
    <div className="flex h-screen app-shell">
      <aside className="w-72 shrink-0 flex flex-col border-r border-default bg-subtle">
        <header className="px-4 py-3 border-b border-default">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-primary tracking-tight">JobReach</p>
              <p className="text-xs text-muted mt-0.5 truncate">{user?.name || user?.email}</p>
            </div>
            <div className="flex items-center gap-0.5">
              <ThemeToggle />
              <button onClick={logout} title="Sign out" className="p-1.5 rounded-md text-muted hover:text-primary hover:bg-muted transition-colors">
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        <nav className="flex border-b border-default">
          <button
            onClick={() => setView("jobs")}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${
              view === "jobs" ? "text-primary border-b-2 border-[var(--accent)]" : "text-muted hover:text-secondary"
            }`}
          >
            <Briefcase className="w-3.5 h-3.5" />
            Jobs
          </button>
          <button
            onClick={() => setView("pipeline")}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${
              view === "pipeline" ? "text-primary border-b-2 border-[var(--accent)]" : "text-muted hover:text-secondary"
            }`}
          >
            <Columns3 className="w-3.5 h-3.5" />
            Pipeline
          </button>
          <button
            onClick={() => setView("analytics")}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-colors ${
              view === "analytics" ? "text-primary border-b-2 border-[var(--accent)]" : "text-muted hover:text-secondary"
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Insights
          </button>
        </nav>

        {view === "jobs" && (
          <>
            <ResumeUploader
              latestResume={latestResume}
              onResumeUploaded={(r) => {
                setLatestResume(r);
                queryClient.invalidateQueries({ queryKey: ["resume"] });
                queryClient.invalidateQueries({ queryKey: ["jobs"] });
              }}
            />
            <JobFiltersPanel filters={filters} onChange={setFilters} />
            <NotificationsPanel />
          </>
        )}
      </aside>

      {view === "jobs" && (
        <>
          <section className="w-[22rem] shrink-0 flex flex-col border-r border-default bg-surface">
            <div className="px-4 py-3 border-b border-default flex items-center justify-between gap-2">
              <span className="text-sm text-secondary">
                {isLoading ? "Loading…" : `${total.toLocaleString()} openings`}
              </span>
              {sortedByMatch && latestResume && (
                <span className="text-xs text-muted shrink-0">Best matches first</span>
              )}
            </div>
            <div className="flex-1 overflow-y-auto" onScroll={handleScroll}>
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  selected={selectedJob?.id === job.id}
                  onClick={() => setSelectedJob(job)}
                />
              ))}
              {isFetchingNextPage && (
                <div className="p-4 text-center text-xs text-muted">Loading more…</div>
              )}
            </div>
          </section>

          <main className="flex-1 min-w-0 bg-surface">
            <JobDetailPanel
              job={selectedJob}
              savedJobIds={savedIds}
              appliedJobIds={appliedIds}
              onSaved={(id) => setSavedIds((s) => new Set(s).add(id))}
              onApplied={(id) => setAppliedIds((s) => new Set(s).add(id))}
              onReferralStart={setReferralJobId}
              onCompanyClick={setCompanyId}
            />
          </main>
        </>
      )}

      {view === "pipeline" && (
        <main className="flex-1 min-w-0 bg-surface">
          <ApplicationKanban />
        </main>
      )}

      {view === "analytics" && (
        <main className="flex-1 min-w-0 bg-surface">
          <AnalyticsDashboard />
        </main>
      )}

      <aside className="w-72 shrink-0 border-l border-default bg-subtle flex flex-col">
        <div className="px-4 py-3 border-b border-default">
          <p className="text-sm font-medium text-secondary">Referrals</p>
          <p className="text-xs text-muted mt-0.5">Warm introductions</p>
        </div>
        <ReferralPipelinePanel jobId={referralJobId} />
      </aside>

      <CompanyProfilePanel companyId={companyId} onClose={() => setCompanyId(null)} />
    </div>
  );
}
