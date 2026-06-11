# RealSight — Project Tracker

> Living context map. Any LLM or human should be able to read this file alone and understand
> what the project is, how it's built, and where things are. **Keep it in sync** — update it
> whenever the stack, structure, conventions, or status changes.

_Last updated: 2026-06-11_

---

## What it is

RealSight is a Chrome extension (Manifest V3) that passively detects AI-generated video while you browse YouTube and Instagram Reels — no manual clicks. A content script extracts 3-4 frames from the playing video via canvas and sends them to a backend agent (Google ADK + Gemini on Cloud Run), which checks a MongoDB Atlas cache through the official MongoDB MCP server and, on a miss, has Gemini forensically classify the frames. The verdict ("AI Generated" / "Likely Real" + confidence) is overlaid as a badge on the player. Built for the Google Cloud Rapid Agent Hackathon (deadline 2026-06-11 2pm PDT), competing in the **MongoDB partner bucket**.

---

## Stack

| Layer | Choice | Version | Notes |
|---|---|---|---|
| Extension | Chrome MV3, vanilla JS | MV3 | No build step; load unpacked from `apps/extension/` |
| Backend | FastAPI | ≥0.136.3 | Hosts POST /analyze; keeps credentials server-side |
| Agent | Google ADK + Gemini | google-adk 2.0 GA, model `gemini-flash-latest` | Docs now at adk.dev (google.github.io redirects); `LlmAgent` + `McpToolset` + `StdioConnectionParams` + `StdioServerParameters`, run via `InMemoryRunner` |
| Partner MCP | MongoDB MCP Server (official, npx) | `npx -y mongodb-mcp-server@latest` | Agent's cache tool; env `MDB_MCP_CONNECTION_STRING`, tools `find`/`insert-many`, `--telemetry disabled` |
| Database | MongoDB Atlas | M0 free | `realsight.detections` — one doc per normalized video URL |
| Hosting | Google Cloud Run | n/a | Hosted URL required by hackathon |
| Auth | none | | Out of scope for hackathon |

> Versions re-verified against official docs (adk.dev, github.com/mongodb-js/mongodb-mcp-server) on 2026-06-11 at build time. ADK Python is 2.0 GA with breaking changes vs 1.x — code targets the 2.0 API.

---

## Architecture

1. Content script (`youtube.js` / `instagram.js`) detects a video (YouTube SPA navigation event / IntersectionObserver on Reels).
2. `capture.js` draws the `<video>` element to canvas 3-4 times → base64 JPEGs (same-origin content script → no canvas tainting).
3. Message to `background.js` service worker → `POST {url, frames}` to backend `/analyze`.
4. ADK agent: MongoDB MCP `find` by normalized URL → cache hit returns instantly; miss → Gemini classifies frames → result written to Atlas → response `{verdict, confidence, reasons, cached}`.
5. Content script renders badge on the player; popup shows detail for the current tab.

---

## Project structure

```
RealSight/
├─ apps/
│  ├─ extension/      # MV3 extension: manifest, content/ (youtube, instagram, capture, badge.css),
│  │                  #   background.js, popup/, config.js (BACKEND_URL)
│  └─ backend/        # FastAPI + ADK agent: app/ (main, agent, schemas), Dockerfile, requirements.txt
├─ docs/              # 01-devpost-submission.md — checklist + demo script
├─ PROJECT.md         # this file
├─ PLAN.md            # build plan (crunch-ordered milestones)
├─ .env.example
├─ LICENSE            # MIT (hackathon requires OSS license)
└─ README.md
```

---

## Conventions

- **Extension:** vanilla JS only, zero dependencies, zero build step.
- **New backend code:** goes in `apps/backend/app/`; keep agent logic in `agent.py`, HTTP in `main.py`.
- **Before coding any library:** fetch its latest official docs — never code APIs from memory.
- **Docs:** `docs/` filenames are zero-padded kebab-case.
- **Testing (crunch mode):** manual verification per task "Done when" conditions; curl for backend, real browsing for extension.

---

## Current status

| Milestone | Status | Notes |
|---|---|---|
| 1. Scaffold | ✅ done | Backend boots, /healthz 200; extension loads unpacked (user-verified) |
| 2. Detection agent backend | ✅ done, verified live | End-to-end confirmed in real browsing: real video → likely_real 95%, AI video → ai_generated 75% **with MongoDB cache hit shown** |
| 3. YouTube extension flow | ✅ done, verified live | Badge + popup confirmed on watch pages (user screenshots); Shorts support added (active-reel video/container targeting) — Shorts pending a live check |
| 4. Cloud Run deploy | ✅ done, verified live | `https://realsight-backend-2bwv4ch3yq-uc.a.run.app` — /health ok with agent_ready, /analyze 200 confirmed from real extension traffic, / serves a landing card. Health endpoint is **/health, not /healthz** (GFE reserves /healthz on run.app and 404s it at the edge — never name Cloud Run health checks /healthz). |
| 5. Instagram Reels (stretch) | ✅ done (code) | IntersectionObserver (0.5) + MutationObserver on Reel videos, shared capture, `/reels/<id>/` cache key; **needs live check — esp. that blob: video doesn't taint canvas**; if it fails, demo YouTube-only |
| 6. Devpost submission | ☐ todo | HARD STOP 2:00 PM PDT today |
| 7. Polish (post-hackathon) | ☐ todo | |

**In progress now:** Milestones 1–3 done and verified live (keys configured in `apps/backend/.env`)
**Next up:** Milestone 4 (Cloud Run deploy), then Devpost submission prep (M6 hard stop 2:00 PM PDT)

### Build notes (2026-06-11)
- **ADK 2.x API drift vs docs:** `McpToolset` imports from `google.adk.tools` (not `google.adk.tools.mcp_tool` as adk.dev shows); the `mcp` pip package is NOT pulled in by `google-adk` — it's a separate requirement. Both fixed in requirements.txt/agent.py against installed google-adk 2.2.0.
- **Windows npx:** stdio MCP spawn resolves `npx` via `shutil.which` (bare `npx` fails on Windows — it's `npx.cmd`).
- **MCP fallback decision (PLAN M2):** full-MCP path implemented (agent does both `find` and `insert-many`); pymongo direct-write fallback NOT yet needed — revisit only if live testing shows flakiness.
- Installed versions: fastapi 0.136.3, google-adk 2.2.0, uvicorn 0.49.0.
- **Gemini 503 high-demand bursts (2026-06-11):** `gemini-flash-latest` and `gemini-3.5-flash` were intermittently 503-overloaded; pinned **`gemini-2.5-flash`** (GA, responsive — override via `REALSIGHT_MODEL`) and added 3-attempt backoff (0/3/8s) on 503 in `run_detection`. Protects the live demo.

---

## Glossary

- **Verdict** — agent output: `ai_generated` | `likely_real` | `uncertain` (+ confidence 0-100, reasons[]).
- **Cache hit** — detection doc already exists in Atlas for the normalized video URL; returned without calling Gemini. The headline MongoDB demo moment.
- **Partner bucket** — hackathon scoring group; we compete only against other MongoDB-track entries.
- **Tainted canvas** — browser security state blocking pixel reads from cross-origin media; avoided because content scripts run same-origin with the page's `<video>`.
- **SynthID** — Google's invisible AI watermark; its Content Detection API is partner-preview only, cited as future work.
