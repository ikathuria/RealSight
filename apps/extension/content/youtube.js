// YouTube flow: on each watch-page navigation, capture frames from the player
// and ask the backend for a verdict, rendering a badge on the player.
// YouTube is an SPA — 'yt-navigate-finish' fires on in-app navigation where
// plain load events don't.

(() => {
  const DEBOUNCE_MS = 800;
  let debounceTimer = null;
  let currentVideoId = null;
  let runToken = 0;

  function getVideoId() {
    const params = new URLSearchParams(location.search);
    if (location.pathname === "/watch") return params.get("v");
    const shorts = location.pathname.match(/^\/shorts\/([\w-]+)/);
    return shorts ? shorts[1] : null;
  }

  function canonicalUrl(videoId) {
    return `https://www.youtube.com/watch?v=${videoId}`;
  }

  // ---- badge ----

  function isShorts() {
    return location.pathname.startsWith("/shorts/");
  }

  function getActiveVideo() {
    if (isShorts()) {
      // Shorts keeps several stacked <video> elements; only the active reel's one counts
      return (
        document.querySelector("ytd-reel-video-renderer[is-active] video") ??
        document.querySelector("#shorts-player video") ??
        document.querySelector("video")
      );
    }
    return document.querySelector("video");
  }

  function getPlayerContainer() {
    if (isShorts()) {
      const shortsPlayer =
        document.querySelector("ytd-reel-video-renderer[is-active] #shorts-player") ??
        document.querySelector("#shorts-player");
      if (shortsPlayer) return shortsPlayer;
    }
    return document.querySelector("#movie_player") ?? getActiveVideo()?.parentElement;
  }

  function renderBadge(state, data = {}) {
    document.querySelector(".realsight-badge")?.remove();
    const container = getPlayerContainer();
    if (!container) return;

    const badge = document.createElement("div");
    badge.className = "realsight-badge";
    badge.title = "RealSight — click to dismiss";
    badge.addEventListener("click", (e) => {
      e.stopPropagation();
      badge.remove();
    });

    if (state === "pending") {
      badge.classList.add("realsight-badge--pending");
      badge.textContent = "🔍 RealSight: analyzing…";
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
      badge.textContent = "⚠️ RealSight: analysis failed";
    }
    container.appendChild(badge);
  }

  // ---- analysis ----

  async function analyzeCurrentVideo() {
    const videoId = getVideoId();
    if (!videoId) {
      document.querySelector(".realsight-badge")?.remove();
      currentVideoId = null;
      return;
    }
    if (videoId === currentVideoId) return; // same video, keep existing badge
    currentVideoId = videoId;
    const token = ++runToken;

    const video = getActiveVideo();
    if (!video) return;

    renderBadge("pending");
    try {
      const frames = await captureFrames(video);
      if (token !== runToken) return; // user navigated away mid-capture

      chrome.runtime.sendMessage(
        { type: "ANALYZE", url: canonicalUrl(videoId), frames },
        (response) => {
          if (token !== runToken) return;
          if (chrome.runtime.lastError || !response?.ok) {
            renderBadge("error");
            return;
          }
          renderBadge("result", response.result);
        }
      );
    } catch (err) {
      console.debug("[RealSight] capture failed", err);
      if (token === runToken) renderBadge("error");
    }
  }

  function scheduleAnalysis() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(analyzeCurrentVideo, DEBOUNCE_MS);
  }

  window.addEventListener("yt-navigate-finish", scheduleAnalysis);
  scheduleAnalysis(); // initial page load lands directly on a watch page
})();
