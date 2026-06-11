// Instagram Reels flow: badge each Reel as it scrolls into view.
// Reel <video> elements are MSE blob: URLs — same-origin, so canvas capture
// works exactly like YouTube. Instagram updates location to /reels/<id>/ as
// you scroll, which is our cache key.

(() => {
  const analyzed = new Set(); // reel ids already sent this session
  let runToken = 0;

  function getReelId() {
    const match = location.pathname.match(/^\/reels?\/([\w-]+)/);
    return match ? match[1] : null;
  }

  function canonicalUrl(reelId) {
    return `https://www.instagram.com/reel/${reelId}/`;
  }

  function badgeContainerFor(video) {
    const container = video.parentElement;
    if (container && getComputedStyle(container).position === "static") {
      container.style.position = "relative";
    }
    return container;
  }

  function renderBadge(video, state, data = {}) {
    const container = badgeContainerFor(video);
    if (!container) return;
    container.querySelector(".realsight-badge")?.remove();

    const badge = document.createElement("div");
    badge.className = "realsight-badge";
    badge.title = "RealSight — click to dismiss";
    badge.addEventListener("click", (e) => {
      e.stopPropagation();
      badge.remove();
    });

    if (state === "pending") {
      badge.classList.add("realsight-badge--pending");
      badge.textContent = "🔍 analyzing…";
    } else if (state === "result") {
      const { verdict, confidence } = data;
      if (verdict === "ai_generated") {
        badge.classList.add("realsight-badge--ai");
        badge.textContent = `🤖 AI Generated (${confidence}%)`;
      } else if (verdict === "likely_real") {
        badge.classList.add("realsight-badge--real");
        badge.textContent = `✅ Likely Real (${confidence}%)`;
      } else {
        badge.classList.add("realsight-badge--uncertain");
        badge.textContent = `❓ Uncertain (${confidence}%)`;
      }
      if (data.cached) badge.textContent += " ⚡";
    } else {
      badge.classList.add("realsight-badge--uncertain");
      badge.textContent = "⚠️ failed";
    }
    container.appendChild(badge);
  }

  async function analyzeReel(video) {
    const reelId = getReelId();
    if (!reelId || analyzed.has(reelId)) return;
    analyzed.add(reelId);
    const token = ++runToken;

    renderBadge(video, "pending");
    try {
      const frames = await captureFrames(video);
      if (token !== runToken) return; // user scrolled on mid-capture

      chrome.runtime.sendMessage(
        { type: "ANALYZE", url: canonicalUrl(reelId), frames },
        (response) => {
          if (token !== runToken) return;
          if (chrome.runtime.lastError || !response?.ok) {
            analyzed.delete(reelId); // allow retry on scroll-back
            renderBadge(video, "error");
            return;
          }
          renderBadge(video, "result", response.result);
        }
      );
    } catch (err) {
      console.debug("[RealSight] reel capture failed", err);
      analyzed.delete(reelId);
      if (token === runToken) renderBadge(video, "error");
    }
  }

  const intersection = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) analyzeReel(entry.target);
      }
    },
    { threshold: 0.5 }
  );

  function observeVideos(root) {
    root.querySelectorAll?.("video").forEach((v) => intersection.observe(v));
  }

  observeVideos(document);
  new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        if (node.tagName === "VIDEO") intersection.observe(node);
        else observeVideos(node);
      }
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
