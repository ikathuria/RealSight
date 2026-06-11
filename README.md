# RealSight 🔍

> **Passive AI-generated-video detection while you browse.** A Chrome extension that badges YouTube videos, Shorts, and Instagram Reels as 🤖 AI Generated or ✅ Likely Real — powered by a Google ADK + Gemini agent with a MongoDB Atlas verdict cache accessed through the official MongoDB MCP Server.

Built for the **Google Cloud Rapid Agent Hackathon** (MongoDB partner bucket). MIT licensed.

## Why

AI video is flooding feeds, and existing detectors make *you* do the work — right-click checks, copy-paste into web tools, crowd reports. RealSight inverts that: detection happens automatically as you browse, with the verdict overlaid on the player within seconds. Media literacy as ambient infrastructure.

## How it works

```
┌────────────────────┐        ┌──────────────────────────────────────────────┐
│  Chrome extension  │        │  Cloud Run (FastAPI)                         │
│  (Manifest V3)     │        │  ┌────────────────────────────────────────┐  │
│                    │  POST  │  │  Google ADK agent (gemini-2.5-flash)   │  │
│  content script    │ /analyze  │                                        │  │
│  grabs 3-4 frames ─┼────────┼─▶│  1. find cache via MongoDB MCP ────────┼──┼──▶ MongoDB
│  from <video> via  │        │  │     hit → instant verdict ⚡           │  │    Atlas
│  canvas            │        │  │  2. miss → Gemini frame forensics      │  │   (M0 free)
│                    │◀───────┼──│  3. insert-many verdict via MCP ───────┼──┼──▶
│  badge on player   │ verdict│  └────────────────────────────────────────┘  │
└────────────────────┘        │   MongoDB MCP Server (stdio subprocess)      │
                              └──────────────────────────────────────────────┘
```

1. A content script detects the playing video (YouTube SPA navigation events; IntersectionObserver on Reels) and extracts 3–4 JPEG frames via canvas — content scripts run same-origin, so the canvas never taints.
2. The extension's service worker POSTs `{url, frames}` to the backend.
3. The ADK agent first calls the MongoDB MCP Server's `find` tool against the `realsight.detections` collection (cache key = normalized video URL). A hit returns instantly without touching Gemini.
4. On a miss, Gemini analyzes the frames forensically (texture smearing, anatomy errors, lighting physics, temporal inconsistencies) and the agent writes the verdict back with `insert-many`.
5. The player gets a badge: 🤖 AI Generated (87%) / ✅ Likely Real (91%) / ❓ Uncertain — with ⚡ marking cached verdicts. The popup shows Gemini's reasoning.

## Run it yourself

### Backend (local)

Prereqs: Python 3.12+, Node.js 20+ (the agent spawns `npx -y mongodb-mcp-server` over stdio).

```bash
cd apps/backend
python -m venv .venv && .venv\Scripts\activate    # Windows; use source .venv/bin/activate elsewhere
pip install -r requirements.txt
copy ..\..\.env.example .env
# fill in GOOGLE_API_KEY (aistudio.google.com) and MDB_MCP_CONNECTION_STRING (Atlas → Connect → Drivers)
uvicorn app.main:app --reload --port 8000
```

Verify with `python smoke_test.py` — the second run of the same URL should return `cached: True` in under a second.

### Extension

1. `chrome://extensions` → enable **Developer mode** → **Load unpacked** → select `apps/extension/`.
2. For local dev, flip `BACKEND_URL` in `apps/extension/config.js` to `http://localhost:8000` (the deployed Cloud Run URL is the default).
3. Browse YouTube. Badges appear on the player within ~5 s.

### Deploy (Cloud Run)

```bash
cd apps/backend
gcloud run deploy realsight-backend --source . --region us-central1 --allow-unauthenticated --memory 1Gi
gcloud run services update realsight-backend --region us-central1 \
  --set-env-vars "GOOGLE_API_KEY=...,MDB_MCP_CONNECTION_STRING=..."
```

The Dockerfile bakes Node 22 + `mongodb-mcp-server` into the image so cold starts never hit the npm registry. Remember to allowlist Cloud Run egress in Atlas Network Access (0.0.0.0/0 for demo purposes).

## Honest detection note

Verdicts are **Gemini-based visual heuristics**, not watermark forensics — confidence numbers reflect a vision model's judgment of artifacts, not cryptographic proof. Google's SynthID Content Detection API (partner preview) is the proper upgrade path and is cited as future work, behind the same detector interface.

## Hackathon compliance

- ✅ Agent built with Google ADK 2.x + Gemini on Google Cloud (Cloud Run)
- ✅ Partner MCP server: official [mongodb-mcp-server](https://github.com/mongodb-js/mongodb-mcp-server) as the agent's cache tool → **MongoDB bucket**
- ✅ Hosted project URL (Cloud Run), public repo, MIT license, ~3 min demo video

## Repo map

| Path | What |
|---|---|
| `apps/extension/` | MV3 extension — content scripts, capture, badge, popup (vanilla JS, zero build) |
| `apps/backend/` | FastAPI + ADK agent + Dockerfile |
| `PROJECT.md` | Living architecture/status tracker |
| `PLAN.md` | Crunch-ordered build plan |
| `docs/` | Devpost checklist + demo script |
