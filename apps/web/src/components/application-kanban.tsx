"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobApi, ApplicationDetail } from "@/lib/api";
import { useState } from "react";
import { Loader2, Calendar } from "lucide-react";

const PIPELINE_STAGES = [
  { key: "applied", label: "Applied", color: "bg-blue-500/10 text-blue-400" },
  { key: "screening", label: "Screening", color: "bg-purple-500/10 text-purple-400" },
  { key: "interview", label: "Interview", color: "bg-amber-500/10 text-amber-400" },
  { key: "offer", label: "Offer", color: "bg-green-500/10 text-green-400" },
  { key: "rejected", label: "Rejected", color: "bg-red-500/10 text-red-400" },
];

const NEXT_STATUS: Record<string, string> = {
  applied: "screening",
  screening: "interview",
  interview: "offer",
  offer: "rejected",
};

export function ApplicationKanban() {
  const queryClient = useQueryClient();
  const [editingNotes, setEditingNotes] = useState<string | null>(null);

  const { data: applications = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: jobApi.getApplications,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<{ status: string; notes: string; interview_date: string }> }) =>
      jobApi.updateApplication(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      setEditingNotes(null);
    },
  });

  const moveStage = (app: ApplicationDetail, newStatus: string) => {
    updateMutation.mutate({ id: app.id, data: { status: newStatus } });
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-accent animate-spin" />
      </div>
    );
  }

  const grouped = Object.fromEntries(PIPELINE_STAGES.map((s) => [s.key, []])) as Record<string, ApplicationDetail[]>;
  applications.forEach((app) => {
    if (grouped[app.status]) grouped[app.status].push(app);
  });

  return (
    <div className="h-full overflow-y-auto p-4">
      <h2 className="text-sm font-medium text-primary mb-4">Application Pipeline</h2>
      <div className="grid grid-cols-5 gap-3 min-h-0">
        {PIPELINE_STAGES.map((stage) => {
          const apps = grouped[stage.key] || [];
          return (
            <div key={stage.key} className="bg-subtle rounded-lg border border-default flex flex-col">
              <div className="px-3 py-2 border-b border-default flex items-center justify-between">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${stage.color}`}>
                  {stage.label}
                </span>
                <span className="text-xs text-muted">{apps.length}</span>
              </div>
              <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[calc(100vh-12rem)]">
                {apps.length === 0 && (
                  <p className="text-xs text-muted text-center py-4">No jobs</p>
                )}
                {apps.map((app) => (
                  <div key={app.id} className="bg-surface rounded-md border border-default p-2.5 space-y-1.5 text-sm">
                    <div className="flex items-start justify-between gap-1">
                      <div className="min-w-0">
                        <p className="text-primary font-medium truncate text-xs">
                          {app.job?.title || "Unknown role"}
                        </p>
                        <p className="text-muted truncate text-[11px]">
                          {app.job?.company_name || "—"}
                        </p>
                      </div>
                    </div>

                    {app.interview_date && (
                      <p className="text-[11px] text-amber-400 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(app.interview_date).toLocaleDateString()}
                      </p>
                    )}

                    {editingNotes === app.id ? (
                      <textarea
                        className="w-full text-xs input-field p-1.5 h-16 resize-none"
                        defaultValue={app.notes || ""}
                        onBlur={(e) => {
                          updateMutation.mutate({ id: app.id, data: { notes: e.target.value || "" } });
                        }}
                        placeholder="Add notes…"
                        autoFocus
                      />
                    ) : (
                      <button
                        onClick={() => setEditingNotes(app.id)}
                        className="w-full text-left text-[11px] text-muted hover:text-secondary transition-colors line-clamp-2"
                      >
                        {app.notes || "Add notes..."}
                      </button>
                    )}

                    <div className="flex gap-1 pt-0.5">
                      {stage.key !== "rejected" && (
                        <button
                          onClick={() => moveStage(app, NEXT_STATUS[stage.key])}
                          className="flex-1 text-[11px] py-1 rounded btn-primary"
                        >
                          Move to {NEXT_STATUS[stage.key]}
                        </button>
                      )}
                      {stage.key !== "applied" && stage.key !== "rejected" && (
                        <button
                          onClick={() => moveStage(app, "rejected")}
                          className="text-[11px] py-1 px-2 rounded btn-secondary text-red-400"
                        >
                          X
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
