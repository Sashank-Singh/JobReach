const TOKEN_KEY = "jobreach_token";

announceReady();

window.addEventListener("message", (event) => {
  if (event.source !== window || event.data?.source !== "jobreach-web") return;

  if (event.data.type === "JOBREACH_PING_EXTENSION") {
    announceReady();
  }

  if (event.data.type === "JOBREACH_REFERRAL_START") {
    const token = window.localStorage.getItem(TOKEN_KEY);
    chrome.runtime.sendMessage(
      {
        type: "JOBREACH_START_REFERRAL",
        payload: {
          ...event.data.payload,
          token,
        },
      },
      (response) => {
        window.postMessage(
          {
            source: "jobreach-extension",
            type: "JOBREACH_EXTENSION_STATUS",
            payload: {
              message: response?.ok
                ? "Opened LinkedIn people search."
                : response?.error || "Could not open LinkedIn search.",
            },
          },
          window.location.origin
        );
      }
    );
  }
});

function announceReady() {
  const token = window.localStorage.getItem(TOKEN_KEY);
  window.postMessage({ source: "jobreach-extension", type: "JOBREACH_EXTENSION_READY" }, window.location.origin);
  chrome.runtime.sendMessage({
    type: "JOBREACH_EXTENSION_CONNECTED",
    payload: { token },
  });
}

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type !== "JOBREACH_BACKGROUND_STATUS") return false;
  window.postMessage(
    {
      source: "jobreach-extension",
      type: "JOBREACH_EXTENSION_STATUS",
      payload: message.payload,
    },
    window.location.origin
  );
  return false;
});
