"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { JobFiltersPanel } from "@/components/job-filters";
import { JobCard } from "@/components/job-card";
import { JobDetailPanel } from "@/components/job-detail";
import { ResumeUploader } from "@/components/resume-uploader";
import { CompanyProfilePanel } from "@/components/company-profile";
import { NotificationsPanel } from "@/components/notifications-panel";
import { Job, JobFilters, jobApi, ResumeData } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Briefcase, LogOut } from "lucide-react";

export function JobDashboard() {
  const { user, logout } = useAuth();
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

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, refetch } = useInfiniteQuery({
    queryKey: ["jobs", filters],
    queryFn: ({ pageParam = 1 }) => jobApi.listJobs({ ...filters, page: pageParam }),
    getNextPageParam: (last) => (last.has_more ? last.page + 1 : undefined),
    initialPageParam: 1,
  });

  const jobs = useMemo(() => data?.pages.flatMap((p) => p.jobs) ?? [], [data]);
  const total = data?.pages[0]?.total ?? 0;

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

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      <div className="w-72 shrink-0 flex flex-col border-r border-zinc-800">
        <div className="p-4 border-b border-zinc-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-emerald-500" />
              <span className="font-bold">JobReach</span>
            </div>
            <button onClick={logout} title="Sign out" className="text-zinc-500 hover:text-zinc-300">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-zinc-500 mt-1 truncate">{user?.name || user?.email}</p>
        </div>
        <ResumeUploader
          latestResume={latestResume}
          onResumeUploaded={(r) => {
            setLatestResume(r);
            refetch();
          }}
        />
        <JobFiltersPanel filters={filters} onChange={setFilters} />
        <NotificationsPanel />
      </div>

      <div className="w-96 shrink-0 flex flex-col border-r border-zinc-800">
        <div className="p-3 border-b border-zinc-800 text-sm text-zinc-400">
          {isLoading ? "Loading..." : `${total.toLocaleString()} jobs`}
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
            <div className="p-4 text-center text-xs text-zinc-500">Loading more...</div>
          )}
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <JobDetailPanel
          job={selectedJob}
          savedJobIds={savedIds}
          appliedJobIds={appliedIds}
          onSaved={(id) => setSavedIds((s) => new Set(s).add(id))}
          onApplied={(id) => setAppliedIds((s) => new Set(s).add(id))}
          onReferralStart={setReferralJobId}
          onCompanyClick={setCompanyId}
        />
      </div>

      <div className="w-80 shrink-0 border-l border-zinc-800 bg-zinc-950/50 flex flex-col">
        <div className="p-4 border-b border-zinc-800">
          <span className="text-sm font-semibold text-zinc-400">Referral Pipeline</span>
          <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400">Dev 2</span>
        </div>
        <div className="flex-1 flex items-center justify-center p-6 text-center">
          {referralJobId ? (
            <div className="space-y-2">
              <p className="text-sm text-violet-300">Referral handoff sent</p>
              <p className="text-xs text-zinc-500">
                Job ID <code className="text-zinc-400">{referralJobId.slice(0, 8)}...</code>
              </p>
              <p className="text-xs text-zinc-600">User: {user?.id.slice(0, 8)}...</p>
            </div>
          ) : (
            <p className="text-xs text-zinc-600">
              Click &quot;Add Referral&quot; to hand off to Developer 2
            </p>
          )}
        </div>
      </div>

      <CompanyProfilePanel companyId={companyId} onClose={() => setCompanyId(null)} />
    </div>
  );
}
