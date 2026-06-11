// Service worker: proxies analysis requests from content scripts to the
// backend (keeps fetch out of page CSP/CORS) and remembers the last result
// per tab for the popup.

importScripts("config.js");

const lastResultByTab = new Map();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE") {
    const tabId = sender.tab?.id;
    lastResultByTab.set(tabId, { status: "pending", url: message.url });

    fetch(`${BACKEND_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: message.url, frames: message.frames }),
    })
      .then((res) => res.json())
      .then((result) => {
        lastResultByTab.set(tabId, { status: "done", url: message.url, result });
        sendResponse({ ok: true, result });
      })
      .catch((err) => {
        lastResultByTab.set(tabId, { status: "error", url: message.url });
        sendResponse({ ok: false, error: String(err) });
      });
    return true; // keep sendResponse alive for the async fetch
  }

  if (message.type === "GET_LAST_RESULT") {
    sendResponse(lastResultByTab.get(message.tabId) ?? null);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => lastResultByTab.delete(tabId));
