"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Loader2, MessageSquare, Send, UserRoundSearch } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ReferralCampaign, ReferralProfile, referralApi } from "@/lib/api";

interface Props {
  jobId: string | null;
}

const EMPTY_PROFILE: ReferralProfile = {
  headline: "",
  summary: "",
  skills: [],
  schools: [],
  target_roles: [],
};

export function ReferralPipelinePanel({ jobId }: Props) {
  const [campaign, setCampaign] = useState<ReferralCampaign | null>(null);
  const [extensionMessage, setExtensionMessage] = useState<string | null>(null);
  const [profileDraft, setProfileDraft] = useState<ReferralProfile>(EMPTY_PROFILE);

  const profile = useQuery({
    queryKey: ["referral-profile"],
    queryFn: referralApi.getProfile,
  });

  const extension = useQuery({
    queryKey: ["extension-session"],
    queryFn: referralApi.getExtensionSession,
    refetchInterval: 30000,
  });

  const campaignQuery = useQuery({
    queryKey: ["referral-campaign", campaign?.id],
    queryFn: () => referralApi.getReferral(campaign!.id),
    enabled: Boolean(campaign?.id),
    refetchInterval: 5000,
  });

  const saveProfile = useMutation({
    mutationFn: referralApi.saveProfile,
    onSuccess: (saved) => setProfileDraft(saved),
  });

  const startReferral = useMutation({
    mutationFn: referralApi.startReferral,
    onSuccess: (started) => {
      setCampaign(started);
      notifyExtension(started);
    },
  });

  useEffect(() => {
    if (profile.data) setProfileDraft(profile.data);
  }, [profile.data]);

  useEffect(() => {
    if (campaignQuery.data) setCampaign(campaignQuery.data);
  }, [campaignQuery.data]);

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      if (event.source !== window || event.data?.source !== "jobreach-extension") return;
      if (event.data.type === "JOBREACH_EXTENSION_READY") {
        setExtensionMessage("Extension connected");
        extension.refetch();
      }
      if (event.data.type === "JOBREACH_EXTENSION_STATUS") {
        setExtensionMessage(event.data.payload?.message || "Extension updated");
        extension.refetch();
      }
    };
    window.addEventListener("message", listener);
    window.postMessage({ source: "jobreach-web", type: "JOBREACH_PING_EXTENSION" }, window.location.origin);
    return () => window.removeEventListener("message", listener);
  }, [extension]);

  const counts = useMemo(() => {
    const messages = campaign?.messages || [];
    return {
      candidates: campaign?.candidates.length || 0,
      queued: messages.filter((m) => m.status === "queued").length,
      sent: messages.filter((m) => m.status === "sent").length,
      manual: messages.filter((m) => m.status === "manual_required").length,
      failed: messages.filter((m) => m.status === "failed").length,
    };
  }, [campaign]);

  if (!jobId) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-center">
        <p className="text-xs text-muted leading-relaxed">
          Select a role and choose &ldquo;Request referral&rdquo; to start an introduction.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-primary">Referral Profile</p>
          <button
            className="text-xs text-accent hover:underline"
            onClick={() => saveProfile.mutate(profileDraft)}
            disabled={saveProfile.isPending}
          >
            {saveProfile.isPending ? "Saving..." : "Save"}
          </button>
        </div>
        <input
          className="input-field w-full text-xs"
          placeholder="Headline"
          value={profileDraft.headline || ""}
          onChange={(e) => setProfileDraft({ ...profileDraft, headline: e.target.value })}
        />
        <textarea
          className="input-field w-full text-xs min-h-20 resize-none"
          placeholder="Short referral context"
          value={profileDraft.summary || ""}
          onChange={(e) => setProfileDraft({ ...profileDraft, summary: e.target.value })}
        />
        <input
          className="input-field w-full text-xs"
          placeholder="Skills, comma separated"
          value={profileDraft.skills.join(", ")}
          onChange={(e) => setProfileDraft({ ...profileDraft, skills: splitCsv(e.target.value) })}
        />
      </section>

      <section className="rounded-lg border border-default bg-surface p-3 space-y-2">
        <div className="flex items-center gap-2 text-xs">
          {extension.data?.status === "connected" || extensionMessage ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : (
            <AlertCircle className="w-4 h-4 text-amber-500" />
          )}
          <span className="text-secondary">{extensionMessage || extension.data?.status || "Extension not connected"}</span>
        </div>
        <p className="text-[11px] text-muted">
          {extension.data ? `${extension.data.remaining}/${extension.data.daily_send_limit} LinkedIn sends remaining today` : "Load the Chrome extension to send LinkedIn outreach."}
        </p>
      </section>

      <button
        className="w-full btn-primary text-sm"
        onClick={() => startReferral.mutate(jobId)}
        disabled={startReferral.isPending}
      >
        {startReferral.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserRoundSearch className="w-4 h-4" />}
        Find referral contacts
      </button>

      {campaign && (
        <section className="space-y-3">
          <div>
            <p className="text-sm font-medium text-primary">{campaign.company_name}</p>
            <p className="text-xs text-muted">{campaign.job_title} · {campaign.status}</p>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <Metric label="Candidates" value={counts.candidates} />
            <Metric label="Queued" value={counts.queued} />
            <Metric label="Sent" value={counts.sent} />
            <Metric label="Needs manual" value={counts.manual} />
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-secondary">Top contacts</p>
            {campaign.candidates.slice(0, 6).map((candidate) => (
              <div key={candidate.id} className="rounded-md border border-default bg-subtle p-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-primary truncate">{candidate.name}</p>
                    <p className="text-[11px] text-muted truncate">{candidate.title || candidate.company || "LinkedIn contact"}</p>
                  </div>
                  <span className="text-[11px] text-accent">{Math.round(candidate.score)}</span>
                </div>
                <p className="text-[11px] text-muted mt-1">{candidate.reasons[0]}</p>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-secondary">Messages</p>
            {campaign.messages.slice(0, 5).map((message) => (
              <div key={message.id} className="rounded-md border border-default bg-subtle p-2">
                <div className="flex items-center gap-2 text-[11px] text-muted">
                  {message.status === "queued" ? <MessageSquare className="w-3 h-3" /> : <Send className="w-3 h-3" />}
                  <span>{message.message_type}</span>
                  <span className="ml-auto">{message.status}</span>
                </div>
                <p className="text-[11px] text-secondary mt-1 line-clamp-3">{message.body}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-default bg-subtle p-2">
      <p className="text-[11px] text-muted">{label}</p>
      <p className="text-sm font-semibold text-primary">{value}</p>
    </div>
  );
}

function splitCsv(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function notifyExtension(campaign: ReferralCampaign) {
  window.postMessage(
    {
      source: "jobreach-web",
      type: "JOBREACH_REFERRAL_START",
      payload: {
        campaignId: campaign.id,
        companyName: campaign.company_name,
        jobTitle: campaign.job_title,
      },
    },
    window.location.origin
  );
}
