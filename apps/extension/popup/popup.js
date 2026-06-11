// Popup: shows the last analysis result for the active tab.

const VERDICT_LABEL = {
  ai_generated: "🤖 AI Generated",
  likely_real: "✅ Likely Real",
  uncertain: "❓ Uncertain",
  error: "⚠️ Analysis failed",
};

const VERDICT_COLOR = {
  ai_generated: "#c62828",
  likely_real: "#2e7d32",
  uncertain: "#888",
  error: "#888",
};

chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  chrome.runtime.sendMessage({ type: "GET_LAST_RESULT", tabId: tab.id }, (entry) => {
    const status = document.getElementById("status");
    if (!entry) return;

    if (entry.status === "pending") {
      status.textContent = "Analyzing current video…";
      return;
    }
    if (entry.status === "error" || !entry.result) {
      status.textContent = "Could not reach the RealSight backend.";
      return;
    }

    const { verdict, confidence, reasons, cached } = entry.result;
    status.hidden = true;
    document.getElementById("result").hidden = false;
    document.getElementById("verdict").textContent =
      `${VERDICT_LABEL[verdict] ?? verdict} (${confidence}%)`;
    const fill = document.getElementById("confidence-fill");
    fill.style.width = `${confidence}%`;
    fill.style.background = VERDICT_COLOR[verdict] ?? "#888";
    const list = document.getElementById("reasons");
    list.replaceChildren(
      ...(reasons ?? []).map((r) => {
        const li = document.createElement("li");
        li.textContent = r;
        return li;
      })
    );
    document.getElementById("cached").hidden = !cached;
  });
});
