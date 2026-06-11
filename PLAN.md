# RealSight

> Chrome extension that passively detects AI-generated video on YouTube and Instagram Reels while you browse, powered by a Gemini agent on Google Cloud with MongoDB Atlas caching — built for the Google Cloud Rapid Agent Hackathon (MongoDB partner bucket).

**⏰ HACKATHON CRUNCH PLAN — submission deadline: June 11, 2026, 2:00 PM PDT (TODAY).**
Milestones are ordered by demo-criticality. If time runs out, everything from Milestone 5 down is cuttable. Milestones 1–4 + 6 are the minimum submittable product.

---

## Viability Summary

| | |
|---|---|
| **Market** | Gap found — existing tools (Hive extension, AI Content Shield, YouTube AI Detector) require manual right-click checks or crowd reports; none offer passive, automatic in-player detection |
| **Feasibility** | Medium — frame extraction from YouTube `<video>` via canvas is proven (same-origin content script avoids tainting); hardest part is Instagram's blob-based player and detection accuracy |
| **Free to build** | Yes — Gemini API free tier / GCP credits, MongoDB Atlas M0 free tier, Cloud Run free tier. (Original Hive AI plan was NOT free: enterprise-gated, payment method required) |
| **Monetization** | Hackathon/portfolio project — prize money is the "monetization" ($5k/3k/2k in MongoDB bucket) |

### Hackathon compliance (non-negotiable requirements)
- ✅ **Agent built with Google Cloud Agent Builder / ADK + Gemini** → backend detection agent
- ✅ **At least one partner MCP server** → official MongoDB MCP Server (`mongodb-js/mongodb-mcp-server`) as the agent's data tool → competes in **MongoDB bucket**
- ✅ **Hosted project URL** → backend on Cloud Run; extension zip + install instructions in repo
- ✅ **Public repo with open-source license** → MIT
- ✅ **~3 minute demo video** → Milestone 6
- Judging: Technological Implementation, Design/UX, Potential Impact, Quality of Idea

---

## Tech Stack

> Versions verified against official docs on 2026-06-11. Re-check before coding.

| Layer | Choice | Version | Reason |
|---|---|---|---|
| Extension | Chrome Manifest V3, vanilla JS | MV3 | No build step = fastest path today; content scripts run same-origin so canvas frame grabs don't taint |
| Backend | FastAPI (Python) | 0.136.3 | Thin HTTP proxy hosting the agent; required anyway to keep credentials out of the extension |
| Agent | Google ADK (Agent Development Kit) + Gemini (latest Flash model) | **fetch current docs at build time** | Hackathon-required; Gemini multimodal classifies extracted frames as AI-generated vs real |
| Partner MCP | MongoDB MCP Server (official) | latest npm | Hackathon partner requirement; agent uses its `find`/`insert-many` tools for the detection cache |
| Database | MongoDB Atlas | M0 free tier | Cache: one document per video URL → repeat visits return instantly without re-analysis |
| Hosting | Google Cloud Run | n/a | Hackathon expects Google Cloud; free tier; one-command deploy from Dockerfile |
| Auth | None | n/a | Out of scope for hackathon demo |

**Detection approach note:** Gemini is prompted as a forensic frame analyst (artifacts, lighting/physics inconsistencies, texture smearing, anatomy errors) returning structured JSON `{verdict, confidence, reasons}`. This is honest "AI-assisted heuristic detection" — Google's SynthID Content Detection API is the proper tool but is partner-preview only; cite it as future work in README/demo.

---

## Project Structure

```
RealSight/
├─ apps/
│  ├─ extension/              # Chrome MV3 extension (no build step)
│  │  ├─ manifest.json
│  │  ├─ content/
│  │  │  ├─ youtube.js        # video-load detection, frame capture, badge injection
│  │  │  ├─ instagram.js      # IntersectionObserver on Reels, same capture path
│  │  │  ├─ capture.js        # shared canvas frame extraction (3-4 JPEG frames)
│  │  │  └─ badge.css         # overlay badge styles
│  │  ├─ background.js        # service worker: fetch() to backend (avoids page CSP/CORS)
│  │  ├─ popup/               # popup.html/js/css — status + confidence for current tab
│  │  └─ config.js            # BACKEND_URL constant
│  └─ backend/                # FastAPI + ADK agent — own pyproject/requirements
│     ├─ app/
│     │  ├─ main.py           # FastAPI app, POST /analyze, GET /healthz
│     │  ├─ agent.py          # ADK agent: Gemini + MongoDB MCP toolset
│     │  └─ schemas.py        # Pydantic request/response models
│     ├─ Dockerfile
│     └─ requirements.txt
├─ docs/
│  └─ 01-devpost-submission.md  # submission checklist + demo video script
├─ PROJECT.md
├─ PLAN.md
├─ .env.example
├─ LICENSE                    # MIT (hackathon requires OSS license)
└─ README.md
```

**Conventions**
- Extension stays vanilla JS, zero dependencies, zero build step — load unpacked from `apps/extension/`.
- **Before coding against any library, fetch its latest official docs** (Google ADK especially — its API moves fast; also MongoDB MCP Server README, Gemini model IDs). Never code framework APIs from memory.
- Keep `PROJECT.md` in sync whenever structure, stack, or status changes.
- `docs/` filenames: zero-padded kebab-case.

---

## Environment Variables

```
# Required (backend — .env locally, set on Cloud Run for deploy)
GOOGLE_API_KEY=               # Gemini API key (aistudio.google.com) OR use Vertex AI:
GOOGLE_CLOUD_PROJECT=         # GCP project id (if using Vertex AI auth instead of API key)
GOOGLE_GENAI_USE_VERTEXAI=    # "true" if Vertex, omit for API-key mode
MDB_MCP_CONNECTION_STRING=    # MongoDB Atlas connection string (Atlas → Connect → Drivers)

# Extension (apps/extension/config.js — not a real env var)
BACKEND_URL=                  # http://localhost:8000 locally, Cloud Run URL after deploy
```

---

## Milestones

### Milestone 1: Scaffold (~30 min)
**Goal:** Repo structure in place, backend boots, extension loads unpacked in Chrome.

Tasks:
- [ ] Create structure per Project Structure section; add MIT `LICENSE`, `.env.example`, stub `README.md` — Done when: tree matches plan
- [ ] Backend: `requirements.txt` (fastapi 0.136.3, uvicorn, google-adk — verify names/versions in current docs), `main.py` with `GET /healthz` — Done when: `uvicorn app.main:app` responds 200 on /healthz
- [ ] Extension: minimal `manifest.json` (MV3; content scripts on `*://*.youtube.com/*` and `*://*.instagram.com/*`; host permission for backend URL; service worker; popup) — Done when: loads unpacked with no errors at `chrome://extensions`
- [ ] Create `PROJECT.md` (done at planning time) and root `CLAUDE.md` pointing to it — Done when: committed
- [ ] Create MongoDB Atlas M0 cluster + database `realsight`, collection `detections`; get connection string — Done when: connection string in local `.env` (USER ACTION — do in parallel with coding)
- [ ] Get Gemini API key from AI Studio — Done when: key in local `.env` (USER ACTION)

---

### Milestone 2: Detection agent backend (~1.5 h)
**Goal:** `POST /analyze` with `{url, frames[]}` returns `{verdict, confidence, reasons, cached}` end-to-end through ADK agent → MongoDB MCP cache → Gemini.

Tasks:
- [ ] **Fetch current Google ADK docs + MongoDB MCP Server README first** (model IDs, `MCPToolset`/`StdioServerParameters` API, MCP server env config) — Done when: agent.py written against verified current APIs
- [ ] ADK agent with Gemini (latest Flash) wired to MongoDB MCP server (`npx -y mongodb-mcp-server` via stdio, `MDB_MCP_CONNECTION_STRING`) — Done when: agent can run a `find` against Atlas from a test script
- [ ] Detection prompt: agent receives 3-4 frames (base64 JPEG) + video URL; instruction: (1) `find` cache by normalized URL → return cached if hit; (2) else analyze frames forensically, output strict JSON `{verdict: "ai_generated"|"likely_real"|"uncertain", confidence: 0-100, reasons: [..]}`; (3) `insert` result into cache — Done when: same URL twice → second response has `cached: true` and returns in <1s
- [ ] `POST /analyze` endpoint: Pydantic validation (≤5 frames, ≤1MB each), runs agent, returns JSON; CORS middleware allowing extension origin; graceful 502 with `verdict: "error"` on agent failure — Done when: `curl` with a real screenshot of an AI video and of a real video returns sensible differing verdicts
- [ ] Fallback guard: if MCP tool calls prove flaky under time pressure, keep MCP as the agent's cache-read tool (compliance ✅) and do the cache-write directly in FastAPI after agent response — Done when: decision recorded in PROJECT.md Notes

---

### Milestone 3: YouTube extension flow (~1.5 h)
**Goal:** Browse YouTube → badge appears on player within ~5 s: "🤖 AI Generated (87%)" or "✅ Likely Real (91%)".

Tasks:
- [ ] `capture.js`: grab `document.querySelector('video')`, wait for `readyState >= 2`, draw to canvas at 512px width at current time + after small seeks (or just capture on `timeupdate` over ~3 s to avoid seeking UX jank), export 3-4 JPEGs (quality 0.7) — Done when: console test logs 3-4 base64 strings on a watch page
- [ ] `youtube.js`: detect navigation (`yt-navigate-finish` event — YouTube is an SPA, plain load events miss in-app navigation), debounce, send `{url: canonical watch URL, frames}` to `background.js` via `chrome.runtime.sendMessage`; background calls backend — Done when: network tab shows one /analyze call per video, including SPA navigations
- [ ] Badge overlay: inject pill into player container (top-right), pending → result states, colors red/green/gray, dismissable, `badge.css` with high z-index — Done when: badge visibly correct on an AI-generated video and a normal video
- [ ] Popup UI: queries background for current tab's last result; shows status, verdict, confidence bar, "reasons" list from Gemini, cached indicator — Done when: popup reflects current video state

---

### Milestone 4: Cloud Run deploy (~45 min)
**Goal:** Hosted project URL (hackathon requirement); extension works against production backend.

Tasks:
- [ ] Dockerfile (python slim + **node/npx for the MongoDB MCP subprocess** — easy to forget), port 8080 — Done when: `docker build` + local run serves /healthz
- [ ] `gcloud run deploy realsight-backend` with env vars set; min-instances 1 if cold-start kills the demo — Done when: hosted /analyze works via curl
- [ ] Point `config.js` BACKEND_URL + manifest host permission at Cloud Run URL — Done when: extension works with local server stopped

---

### Milestone 5 (STRETCH — cut first): Instagram Reels (~45 min)
**Goal:** Reels get the same badge as they scroll into view.

Tasks:
- [ ] `instagram.js`: IntersectionObserver (threshold 0.5) on Reel `<video>` elements, capture via shared `capture.js`, URL = closest `/reels/<id>/` permalink — Done when: scrolling Reels triggers one analysis each, badge overlays correctly
- [ ] Verify IG `blob:` video doesn't taint canvas (MSE blob is same-origin — should pass; if it fails, demo YouTube-only and note Reels as in-progress) — Done when: tested in real session

---

### Milestone 6: Devpost submission (~1 h — HARD STOP 2:00 PM PDT, start by 12:45 PM regardless of feature state)
**Goal:** Submitted, complete, in the MongoDB bucket.

Tasks:
- [ ] README: what/why, architecture diagram (extension → Cloud Run agent → Gemini + MongoDB MCP → Atlas), local setup, extension install steps, screenshots — Done when: a stranger could run it
- [ ] Push public repo to GitHub with MIT license — Done when: public URL live
- [ ] Record ~3 min demo: (1) the problem, 20s; (2) live YouTube detection on AI video + real video, 60s; (3) cached repeat visit returning instantly — *the MongoDB moment, linger here*, 30s; (4) architecture: ADK + Gemini + MongoDB MCP server, 45s; (5) impact, 15s — Done when: uploaded (YouTube unlisted is fine)
- [ ] Devpost form: hosted URL (Cloud Run /healthz or simple landing route), repo, video, MongoDB partner bucket, write-up emphasizing judging criteria — Done when: submission confirmed before 2:00 PM PDT

---

### Milestone 7 (POST-HACKATHON): Polish
- [ ] Frame-hash dedup (same video re-uploaded under new URL)
- [ ] SynthID Content Detection API when publicly available; Hive adapter behind a detector interface
- [ ] Settings page (sensitivity, per-site toggle), error toasts, rate limiting on backend
- [ ] Chrome Web Store listing

---

## Claude Code Commands

> In every session, fetch the latest official docs for any library before coding against it, and keep `PROJECT.md` in sync with what you build.

**Start (crunch mode — run milestones back-to-back):**
```
claude "Read PLAN.md and PROJECT.md. This is a same-day hackathon deadline. Complete Milestones 1 and 2, fetching the latest official docs for google-adk and mongodb-mcp-server before using them. Update PROJECT.md as you go. Commit after each milestone. Flag immediately if you're blocked on the USER ACTION tasks (Atlas connection string, Gemini API key)."
```

**Resume:**
```
claude "Read PLAN.md and PROJECT.md. Find the first incomplete task and continue, fetching the latest official docs for any library before using it. Keep PROJECT.md in sync. Commit when a milestone is complete."
```

**Test current state:**
```
claude "Read PLAN.md and PROJECT.md. Without building anything new, test everything that's marked done. Report what works and what's broken."
```

---

## Notes & Decisions

- **2026-06-11 — Pivoted off Hive AI + plain FastAPI** to Google ADK + Gemini + MongoDB MCP server: hackathon rules require Agent Builder/Gemini + a partner MCP server, and Hive's detection API is enterprise-gated (payment method + sales contact). FastAPI retained as the hosting shell. MongoDB partner bucket chosen.
- **Detection honesty:** Gemini frame analysis is heuristic, not forensic watermark detection. Present confidence as such in UI and demo; cite SynthID Content Detection API (partner preview) as the upgrade path.
- **Time-pressure fallback:** if ADK↔MCP wiring is flaky, MCP stays as the agent's cache-read tool (keeps compliance) and writes go direct via pymongo.
