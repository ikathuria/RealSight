// Shared frame extraction: draws the given <video> to a canvas several times
// over ~3s of playback and returns base64 JPEG strings (no data: prefix).
// Same-origin content script context, so the canvas is never tainted.
// Milestone 3 wires this into youtube.js / instagram.js.

async function captureFrames(video, { count = 4, intervalMs = 900, width = 512 } = {}) {
  if (!video || video.readyState < 2) {
    await new Promise((resolve) => {
      const onReady = () => {
        video.removeEventListener("loadeddata", onReady);
        resolve();
      };
      video.addEventListener("loadeddata", onReady);
    });
  }

  const canvas = document.createElement("canvas");
  const scale = width / video.videoWidth;
  canvas.width = width;
  canvas.height = Math.round(video.videoHeight * scale);
  const ctx = canvas.getContext("2d");

  const frames = [];
  for (let i = 0; i < count; i++) {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
    frames.push(dataUrl.split(",")[1]);
    if (i < count - 1) await new Promise((r) => setTimeout(r, intervalMs));
  }
  return frames;
}
