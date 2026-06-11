// Service worker: proxies analysis requests from content scripts to the
// backend (keeps fetch out of page CSP/CORS) and remembers the last result
// per tab for the popup.

importScripts("config.js");

const lastResultByTab = new Map();

// ---- toolbar icon states ----
// off = not a supported video page, scan1-3 = analyzing (pulse animation),
// ai/real/uncertain = verdict.

const scanTimers = new Map(); // tabId -> interval id

function iconPaths(state) {
  return {
    16: `icons/${state}-16.png`,
    32: `icons/${state}-32.png`,
    48: `icons/${state}-48.png`,
    128: `icons/${state}-128.png`,
  };
}

function setIcon(tabId, state) {
  stopScanAnimation(tabId);
  chrome.action.setIcon({ tabId, path: iconPaths(state) }, () => chrome.runtime.lastError);
}

function startScanAnimation(tabId) {
  stopScanAnimation(tabId);
  const frames = ["scan1", "scan2", "scan3", "scan2"];
  let i = 0;
  const tick = () =>
    chrome.action.setIcon({ tabId, path: iconPaths(frames[i++ % frames.length]) }, () =>
      chrome.runtime.lastError
    );
  tick();
  scanTimers.set(tabId, setInterval(tick, 350));
}

function stopScanAnimation(tabId) {
  const timer = scanTimers.get(tabId);
  if (timer) {
    clearInterval(timer);
    scanTimers.delete(tabId);
  }
}

const VERDICT_ICON = { ai_generated: "ai", likely_real: "real", uncertain: "uncertain" };

// gray out the icon on pages we don't run on
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== "loading" || !tab.url) return;
  const supported = /https?:\/\/([\w-]+\.)?(youtube|instagram)\.com\//.test(tab.url);
  if (!supported) setIcon(tabId, "off");
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "ANALYZE") {
    const tabId = sender.tab?.id;
    lastResultByTab.set(tabId, { status: "pending", url: message.url });
    if (tabId != null) startScanAnimation(tabId);

    fetch(`${BACKEND_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: message.url, frames: message.frames }),
    })
      .then((res) => res.json())
      .then((result) => {
        lastResultByTab.set(tabId, { status: "done", url: message.url, result });
        if (tabId != null) setIcon(tabId, VERDICT_ICON[result.verdict] ?? "uncertain");
        sendResponse({ ok: true, result });
      })
      .catch((err) => {
        lastResultByTab.set(tabId, { status: "error", url: message.url });
        if (tabId != null) setIcon(tabId, "uncertain");
        sendResponse({ ok: false, error: String(err) });
      });
    return true; // keep sendResponse alive for the async fetch
  }

  if (message.type === "GET_LAST_RESULT") {
    sendResponse(lastResultByTab.get(message.tabId) ?? null);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  lastResultByTab.delete(tabId);
  stopScanAnimation(tabId);
});
