# Devpost submission checklist

**Deadline: 2026-06-11 2:00 PM PDT. Start submitting by 12:45 PM regardless of feature state.**

## Checklist

- [ ] README complete (what/why, architecture diagram, setup, screenshots)
- [ ] Public GitHub repo, MIT license
- [ ] Hosted URL live (Cloud Run `/healthz` or landing route)
- [ ] ~3 min demo video uploaded (YouTube unlisted OK)
- [ ] Devpost form: hosted URL, repo URL, video, **MongoDB partner bucket** selected
- [ ] Write-up hits judging criteria: Technological Implementation, Design/UX, Potential Impact, Quality of Idea

## Devpost description (paste into the form)

### Tagline (under 60 chars)

> Passive AI-video detection, right on the player, as you browse.

### Inspiration

AI-generated video is flooding YouTube and Instagram, and every existing detector makes the *viewer* do the work: right-click a thumbnail, paste a URL into a web tool, hope someone crowd-flagged it. Detection that requires effort protects nobody at scale. We asked: what if checking were as passive as watching?

### What it does

RealSight is a Chrome extension that automatically analyzes every video you watch on YouTube (including Shorts) and Instagram Reels. Within ~5 seconds of playback, a badge appears on the player: **🤖 AI Generated (87%)**, **✅ Likely Real (95%)**, or **❓ Uncertain** — with the model's specific visual reasoning (e.g., "over-smooth, plastic-looking skin", "repetitive, unnatural patterns on clothing") one click away in the popup. No clicks, no copy-paste, no manual checks. The toolbar icon mirrors state in real time: gray off-page, pulsing blue while analyzing, verdict-colored when done.

### How we built it (Technological Implementation)

- **Google ADK 2.x agent + Gemini (`gemini-2.5-flash`) hosted on Google Cloud Run.** The agent receives 3–4 JPEG frames extracted client-side from the playing `<video>` via canvas (content scripts run same-origin, so the canvas never taints — this also works on Instagram's MSE blob streams).
- **Official MongoDB MCP Server (`mongodb-mcp-server`) as the agent's tool — the partner integration.** The agent's first action on every request is a `find` against the `realsight.detections` collection in **MongoDB Atlas**, keyed on a normalized video URL (watch pages, Shorts, youtu.be links, and Reels permalinks all canonicalize to one key). A cache hit returns the verdict in under a second without invoking Gemini at all — cheaper, faster, and verdicts are consistent for every user who watches the same video. On a miss, Gemini performs forensic frame analysis (texture smearing, anatomy errors, lighting/shadow physics, temporal inconsistency between frames) and the agent writes the verdict back through the MCP server's `insert-many` tool.
- **Engineering details judges can check in the repo:** strict-JSON agent output with validation and clamping; Pydantic request limits (≤5 frames, ≤1MB each); 503-retry with exponential backoff to survive Gemini load spikes; the Docker image pre-bakes Node + the MCP server so Cloud Run cold starts never hit the npm registry; the extension is vanilla MV3 JavaScript with zero dependencies and zero build step.

### Design / UX

The product goal was *zero-interaction* detection: the verdict appears where your eyes already are (the player), in glanceable color (red/green/gray), with confidence stated as a percentage and reasons in plain language. Failures degrade gracefully — an unreachable backend yields a dismissable "analysis failed" badge, never a broken page. The animated toolbar icon communicates state even when the badge is dismissed.

### Potential Impact

Deepfake detection tools today serve journalists and researchers — people who already suspect something. RealSight targets the other 99%: passive viewers who never think to check. Ambient, automatic labeling is how media literacy scales. The MongoDB cache makes this economically viable: each video is analyzed once globally, then served from Atlas for every subsequent viewer.

### Honest limitations & what's next

Verdicts are Gemini-based **visual heuristics**, not watermark forensics, and we present them as confidence levels, not facts. The detector sits behind an interface designed for Google's **SynthID Content Detection API** (currently partner-preview) to slot in when publicly available. Also next: frame-hash dedup to catch re-uploads under new URLs, sensitivity settings, and a Chrome Web Store listing.

### Hackathon compliance checklist (for judges)

- ✅ Agent built with **Google ADK** + **Gemini**, hosted on **Google Cloud Run**
- ✅ Partner MCP server: **official MongoDB MCP Server** wired into the agent as its data tool → **MongoDB partner bucket**
- ✅ Public repo, **MIT license** · hosted URL · ~3 min demo video

---

## Demo video script (~3 min)

1. **The problem** (20s) — AI video is flooding feeds; existing detectors need manual checks.
2. **Live detection** (60s) — browse YouTube: AI-generated video gets 🤖 badge, real video gets ✅, popup shows Gemini's reasons.
3. **The MongoDB moment** (30s) — revisit the same video: instant cached verdict via MongoDB MCP Server `find` against Atlas. Linger here.
4. **Architecture** (45s) — Chrome MV3 extension → Cloud Run → Google ADK agent → Gemini (frame forensics) + MongoDB MCP Server (cache) → Atlas.
5. **Impact** (15s) — passive media literacy for everyone; SynthID Content Detection API as the upgrade path.
