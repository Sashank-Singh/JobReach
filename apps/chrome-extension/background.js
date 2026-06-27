importScripts("extension-utils.js");

const REFERRAL_API_URL = "https://referrals.yourdomain.com";

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ referralApiUrl: REFERRAL_API_URL });
  chrome.alarms.create("jobreach-followups", { periodInMinutes: 30 });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("jobreach-followups", { periodInMinutes: 30 });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name !== "jobreach-followups") return;
  runDueFollowups().catch(() => {});
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "JOBREACH_EXTENSION_CONNECTED") {
    chrome.storage.local.set({ authToken: message.payload?.token }).then(() => {
      reportExtensionEvent("connected", { url: sender.tab?.url }).catch(() => {});
    });
    sendResponse({ ok: true });
    return false;
  }

  if (message?.type === "JOBREACH_START_REFERRAL") {
    startReferralFlow(message.payload)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === "JOBREACH_LINKEDIN_CANDIDATES") {
    postCandidates(message.payload)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  return false;
});

async function startReferralFlow(payload) {
  if (!payload?.campaignId || !payload?.companyName) {
    throw new Error("Missing referral campaign payload");
  }

  await chrome.storage.local.set({ activeCampaign: payload, authToken: payload.token });
  await reportExtensionEvent("collecting_candidates", { campaignId: payload.campaignId });
  await notifyWebTabs("Opening LinkedIn people search.");
  const url = JobReachExtensionUtils.buildLinkedInPeopleSearchUrl(payload.companyName, payload.jobTitle);
  const tab = await chrome.tabs.create({ url, active: true });
  await waitForTabComplete(tab.id);
  await chrome.tabs.sendMessage(tab.id, {
    type: "JOBREACH_COLLECT_CANDIDATES",
    payload,
  }).catch(() => {});
  return { tabId: tab.id, url };
}

async function postCandidates(payload) {
  const { activeCampaign, referralApiUrl = REFERRAL_API_URL } = await chrome.storage.local.get([
    "activeCampaign",
    "referralApiUrl",
  ]);
  const token = activeCampaign?.token;
  if (!activeCampaign?.campaignId) throw new Error("No active JobReach campaign");
  if (!token) throw new Error("Missing JobReach auth token");

  const response = await fetch(`${referralApiUrl}/referrals/${activeCampaign.campaignId}/candidates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ candidates: payload.candidates }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Candidate sync failed: ${response.status}`);
  }

  const candidates = await response.json();
  await reportExtensionEvent("candidates_synced", {
    campaignId: activeCampaign.campaignId,
    count: candidates.length,
  });
  await notifyWebTabs(`Synced ${candidates.length} LinkedIn candidates.`);
  const tasks = await createOutreachPlan(referralApiUrl, token, activeCampaign.campaignId);
  await reportExtensionEvent("outreach_plan_created", {
    campaignId: activeCampaign.campaignId,
    count: tasks.length,
  });
  await notifyWebTabs(`Queued ${tasks.length} outreach messages.`);
  await runSendTasks(referralApiUrl, token, tasks);
  return { candidates, tasks: tasks.length };
}

async function createOutreachPlan(referralApiUrl, token, campaignId) {
  const response = await fetch(`${referralApiUrl}/referrals/${campaignId}/outreach-plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ limit: 10, message_type: "referral_request" }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Outreach plan failed: ${response.status}`);
  }
  return response.json();
}

async function runDueFollowups() {
  const { authToken, referralApiUrl = REFERRAL_API_URL } = await chrome.storage.local.get([
    "authToken",
    "referralApiUrl",
  ]);
  if (!authToken) return;

  const response = await fetch(`${referralApiUrl}/followups/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
  });
  if (!response.ok) return;
  const tasks = await response.json();
  await runSendTasks(referralApiUrl, authToken, tasks);
}

async function runSendTasks(referralApiUrl, token, tasks) {
  for (const task of tasks) {
    await sendTask(referralApiUrl, token, task);
    await sleep(2500);
  }
}

async function sendTask(referralApiUrl, token, task) {
  const profileUrl = task?.candidate?.profile_url;
  const messageId = task?.message?.id;
  const campaignId = task?.message?.campaign_id;
  if (!profileUrl || !messageId) return;

  let tab;
  let keepTabOpen = false;
  try {
    const session = await getExtensionSession(referralApiUrl, token);
    if (!JobReachExtensionUtils.hasSendCapacity(session)) {
      await safeReportSendStatus(referralApiUrl, token, messageId, "skipped", {
        reason: "send_limit_reached",
        session,
      }, { campaignId });
      await reportExtensionEvent("send_limit_reached", {
        campaignId,
        messageId,
        candidateId: task?.candidate?.id,
        remaining: session?.remaining,
      });
      await notifyWebTabs(JobReachExtensionUtils.sendCapacitySummary(session));
      return;
    }

    await reportExtensionEvent("send_attempt_started", {
      campaignId,
      messageId,
      candidateId: task?.candidate?.id,
      profileUrl,
    });
    await notifyWebTabs(`Sending outreach to ${task?.candidate?.name || "candidate"}.`);
    tab = await chrome.tabs.create({ url: profileUrl, active: false });
    await waitForTabComplete(tab.id);
    const response = await chrome.tabs.sendMessage(tab.id, {
      type: "JOBREACH_SEND_OUTREACH",
      payload: {
        message: task.message,
        candidate: task.candidate,
      },
    });
    const status = response?.ok ? "sent" : response?.status || "failed";
    keepTabOpen = JobReachExtensionUtils.shouldKeepSendTabOpen(status);
    if (keepTabOpen && tab?.id) {
      await chrome.tabs.update(tab.id, { active: true }).catch(() => {});
    }
    await safeReportSendStatus(referralApiUrl, token, messageId, status, response || {}, { campaignId });
    await reportExtensionEvent(`message_${status}`, {
      campaignId,
      messageId,
      candidateId: task?.candidate?.id,
      method: response?.method,
      error: response?.error,
    });
    await notifyWebTabs(
      status === "sent"
        ? `Sent outreach to ${task?.candidate?.name || "candidate"}.`
        : status === "manual_required"
          ? `Manual action required for ${task?.candidate?.name || "candidate"}.`
          : `Failed outreach to ${task?.candidate?.name || "candidate"}.`
    );
  } catch (error) {
    await safeReportSendStatus(referralApiUrl, token, messageId, "failed", { error: error.message }, { campaignId });
    await reportExtensionEvent("message_failed", {
      campaignId,
      messageId,
      candidateId: task?.candidate?.id,
      error: error.message,
    });
    await notifyWebTabs(`Failed outreach: ${error.message}`);
  } finally {
    if (tab?.id && !keepTabOpen) chrome.tabs.remove(tab.id).catch(() => {});
  }
}

async function safeReportSendStatus(referralApiUrl, token, messageId, status, details, context = {}) {
  try {
    await reportSendStatus(referralApiUrl, token, messageId, status, details);
  } catch (error) {
    await reportExtensionEvent("status_report_failed", {
      campaignId: context.campaignId,
      messageId,
      attemptedStatus: status,
      error: error.message,
    });
  }
}

async function reportSendStatus(referralApiUrl, token, messageId, status, details) {
  const response = await fetch(`${referralApiUrl}/messages/send-status`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message_id: messageId,
      status,
      details,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Send status update failed: ${response.status}`);
  }
}

async function getExtensionSession(referralApiUrl, token) {
  const response = await fetch(`${referralApiUrl}/extension/session`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Could not fetch extension session: ${response.status}`);
  }
  return response.json();
}

function waitForTabComplete(tabId) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("LinkedIn profile load timed out"));
    }, 30000);

    function listener(updatedTabId, changeInfo) {
      if (updatedTabId !== tabId || changeInfo.status !== "complete") return;
      clearTimeout(timeout);
      chrome.tabs.onUpdated.removeListener(listener);
      setTimeout(resolve, 1500);
    }

    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function reportExtensionEvent(status, details = {}) {
  const { authToken, referralApiUrl = REFERRAL_API_URL } = await chrome.storage.local.get([
    "authToken",
    "referralApiUrl",
  ]);
  if (!authToken) return;
  await fetch(`${referralApiUrl}/extension/events`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      status,
      version: chrome.runtime.getManifest().version,
      details,
    }),
  }).catch(() => {});
}

async function notifyWebTabs(message) {
  const tabs = await chrome.tabs.query({});
  const appTabs = tabs.filter((tab) => tab.url && !tab.url.includes("linkedin.com"));
  for (const tab of appTabs) {
    if (!tab.id) continue;
    chrome.tabs.sendMessage(tab.id, {
      type: "JOBREACH_BACKGROUND_STATUS",
      payload: { message },
    }).catch(() => {});
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
