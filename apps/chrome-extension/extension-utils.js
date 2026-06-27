(function defineJobReachExtensionUtils(globalScope) {
  const LINKEDIN_PEOPLE_SEARCH_BASE = "https://www.linkedin.com/search/results/people/";

  function roleSearchTerms(jobTitle = "") {
    const title = jobTitle.toLowerCase();
    if (title.includes("product")) return "product manager";
    if (title.includes("design")) return "designer design lead";
    if (title.includes("data")) return "data engineer data scientist";
    if (title.includes("sales")) return "sales account executive";
    if (title.includes("marketing")) return "marketing growth";
    return "engineer engineering manager";
  }

  function buildLinkedInPeopleSearchUrl(companyName, jobTitle = "") {
    const query = `"${companyName}" ${roleSearchTerms(jobTitle)} recruiter "hiring manager"`;
    return `${LINKEDIN_PEOPLE_SEARCH_BASE}?keywords=${encodeURIComponent(query)}`;
  }

  function normalizeLinkedInUrl(url) {
    if (!url) return null;
    try {
      const parsed = new URL(url);
      parsed.search = "";
      parsed.hash = "";
      return parsed.toString();
    } catch {
      return null;
    }
  }

  function inferCompany(title) {
    if (!title) return null;
    const atMatch = title.match(/\bat\s+(.+)$/i);
    return atMatch?.[1]?.trim() || null;
  }

  function isSecurityCheckpointText(text = "") {
    const lowered = text.toLowerCase();
    return (
      lowered.includes("security verification") ||
      lowered.includes("captcha") ||
      lowered.includes("verify your identity") ||
      lowered.includes("two-step verification") ||
      (lowered.includes("login") || lowered.includes("log in")) && lowered.includes("linkedin")
    );
  }

  function matchesButtonLabel(text, labels) {
    const normalizedText = text?.replace(/\s+/g, " ").trim().toLowerCase();
    if (!normalizedText) return false;
    return labels.some((label) => {
      const normalizedLabel = label.toLowerCase();
      return normalizedText === normalizedLabel || normalizedText.includes(normalizedLabel);
    });
  }

  function hasSendCapacity(session) {
    return Number(session?.remaining || 0) > 0;
  }

  function sendCapacitySummary(session) {
    const remaining = Number(session?.remaining || 0);
    const limit = Number(session?.daily_send_limit || 0);
    return `${Math.max(remaining, 0)}/${Math.max(limit, 0)} LinkedIn sends remaining`;
  }

  function shouldKeepSendTabOpen(status) {
    return status === "manual_required";
  }

  function candidateRelevance(candidate = {}, context = {}) {
    const text = [candidate.title, candidate.company, candidate.text].filter(Boolean).join(" ").toLowerCase();
    const company = (context.companyName || "").toLowerCase();
    const jobTitle = (context.jobTitle || "").toLowerCase();

    if (company && text.includes(company)) return "company_match";
    if (text.includes("recruiter") || text.includes("talent") || text.includes("hiring")) return "recruiting_match";
    for (const token of ["engineer", "product", "design", "data", "sales", "marketing"]) {
      if (jobTitle.includes(token) && text.includes(token)) return "function_match";
    }
    return "weak";
  }

  const api = {
    buildLinkedInPeopleSearchUrl,
    candidateRelevance,
    hasSendCapacity,
    inferCompany,
    isSecurityCheckpointText,
    matchesButtonLabel,
    normalizeLinkedInUrl,
    roleSearchTerms,
    sendCapacitySummary,
    shouldKeepSendTabOpen,
  };

  globalScope.JobReachExtensionUtils = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
