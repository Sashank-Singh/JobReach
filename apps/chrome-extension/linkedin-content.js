const CARD_SELECTORS = [
  "li.reusable-search__result-container",
  ".reusable-search__result-container",
  ".entity-result",
];

const NAME_SELECTORS = [
  ".entity-result__title-text a span[aria-hidden='true']",
  ".entity-result__title-text span[aria-hidden='true']",
  "span[dir='ltr'] span[aria-hidden='true']",
];

const TITLE_SELECTORS = [
  ".entity-result__primary-subtitle",
  ".entity-result__summary",
  ".t-14.t-black.t-normal",
];

const LOCATION_SELECTORS = [
  ".entity-result__secondary-subtitle",
  ".t-14.t-normal",
];

const MAX_COLLECTION_ROUNDS = 5;
const MIN_CANDIDATES_BEFORE_SYNC = 10;

setTimeout(() => {
  collectWithRetries();
}, 1800);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "JOBREACH_COLLECT_CANDIDATES") {
    collectWithRetries(message.payload)
      .then((result) => sendResponse({ ok: true, ...result }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type !== "JOBREACH_SEND_OUTREACH") return false;
  sendOutreach(message.payload)
    .then((result) => sendResponse({ ok: true, ...result }))
    .catch((error) =>
      sendResponse({
        ok: false,
        status: error.manualRequired ? "manual_required" : "failed",
        error: error.message,
      })
    );
  return true;
});

async function collectWithRetries(context = {}) {
  if (!location.href.includes("/search/results/people")) return;

  let candidates = [];
  for (let round = 0; round < MAX_COLLECTION_ROUNDS; round += 1) {
    candidates = collectCandidates(context);
    if (candidates.length >= MIN_CANDIDATES_BEFORE_SYNC) break;
    window.scrollBy({ top: Math.round(window.innerHeight * 0.8), behavior: "smooth" });
    await sleep(1200);
  }

  if (candidates.length === 0) return { count: 0 };

  chrome.runtime.sendMessage(
    {
      type: "JOBREACH_LINKEDIN_CANDIDATES",
      payload: { candidates },
    },
    () => {}
  );
  return { count: candidates.length };
}

function collectCandidates(context = {}) {
  const cards = CARD_SELECTORS.flatMap((selector) => Array.from(document.querySelectorAll(selector)));
  const uniqueCards = [...new Set(cards)].slice(0, 30);
  const seen = new Set();
  return uniqueCards
    .map(candidateFromCard)
    .filter((candidate) => candidate.name && candidate.profile_url)
    .map((candidate) => annotateCandidate(candidate, context))
    .filter((candidate) => candidate.relevance !== "weak")
    .filter((candidate) => {
      if (seen.has(candidate.profile_url)) return false;
      seen.add(candidate.profile_url);
      return true;
    });
}

function candidateFromCard(card) {
  const link = card.querySelector("a[href*='/in/']");
  const title = textFromSelectors(card, TITLE_SELECTORS);
  return {
    name: textFromSelectors(card, NAME_SELECTORS),
    title,
    location: textFromSelectors(card, LOCATION_SELECTORS),
    company: JobReachExtensionUtils.inferCompany(title),
    profile_url: JobReachExtensionUtils.normalizeLinkedInUrl(link?.href),
    source: "linkedin_search_ui",
  };
}

function annotateCandidate(candidate, context = {}) {
  const text = [candidate.title, candidate.company, candidate.location].filter(Boolean).join(" ");
  const relevance = JobReachExtensionUtils.candidateRelevance(
    {
      title: candidate.title,
      company: candidate.company,
      text,
    },
    {
      companyName: context.companyName,
      jobTitle: context.jobTitle,
    }
  );
  return {
    ...candidate,
    source: `linkedin_search_ui:${relevance}`,
    relevance,
  };
}

function textFromSelectors(root, selectors) {
  for (const selector of selectors) {
    const node = root.querySelector(selector);
    const text = node?.textContent?.replace(/\s+/g, " ").trim();
    if (text) return text;
  }
  return null;
}

async function sendOutreach(payload) {
  const body = payload?.message?.body;
  if (!body) throw new Error("Missing outreach body");
  if (isSecurityCheckpoint()) throw manualRequired("LinkedIn security checkpoint or login prompt detected");

  if (await tryDirectMessage(body)) {
    return { method: "message" };
  }
  if (await tryConnectWithNote(body)) {
    return { method: "connect_note" };
  }

  throw manualRequired("No usable Message or Connect flow found");
}

async function tryDirectMessage(body) {
  const messageButton = findButtonByText(["Message"]);
  if (!messageButton) return false;
  messageButton.click();
  await sleep(1200);

  const box = findTextBox();
  if (!box) return false;
  setEditableText(box, body);
  await sleep(400);

  const sendButton = findButtonByText(["Send"]);
  if (!sendButton || sendButton.disabled) return false;
  sendButton.click();
  await sleep(800);
  return true;
}

async function tryConnectWithNote(body) {
  const connectButton = findButtonByText(["Connect"]);
  if (!connectButton) {
    const moreButton = findButtonByText(["More"]);
    moreButton?.click();
    await sleep(500);
  }

  const menuConnect = findButtonByText(["Connect"]);
  if (!menuConnect) return false;
  menuConnect.click();
  await sleep(1000);

  const addNoteButton = findButtonByText(["Add a note", "Add note"]);
  if (addNoteButton) {
    addNoteButton.click();
    await sleep(700);
  }

  const noteBox = findTextBox() || document.querySelector("textarea[name='message']");
  if (noteBox) {
    setEditableText(noteBox, body.slice(0, 295));
    await sleep(400);
  }

  const sendButton = findButtonByText(["Send", "Send invitation"]);
  if (!sendButton || sendButton.disabled) return false;
  sendButton.click();
  await sleep(800);
  return true;
}

function findButtonByText(labels) {
  const buttons = Array.from(document.querySelectorAll("button, [role='button']"));
  return buttons.find((button) => {
    return JobReachExtensionUtils.matchesButtonLabel(button.textContent, labels);
  });
}

function findTextBox() {
  return (
    document.querySelector("[contenteditable='true'][role='textbox']") ||
    document.querySelector("[contenteditable='true']") ||
    document.querySelector("textarea")
  );
}

function setEditableText(node, text) {
  node.focus();
  if (node.tagName === "TEXTAREA" || node.tagName === "INPUT") {
    node.value = text;
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
    return;
  }
  document.execCommand("selectAll", false);
  document.execCommand("insertText", false, text);
  node.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }));
}

function isSecurityCheckpoint() {
  return JobReachExtensionUtils.isSecurityCheckpointText(document.body?.textContent || "");
}

function manualRequired(message) {
  const error = new Error(message);
  error.manualRequired = true;
  return error;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
