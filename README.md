# RealSight

> Passive AI-generated-video detection for YouTube and Instagram Reels — a Chrome extension backed by a Google ADK + Gemini agent that caches verdicts in MongoDB Atlas through the official MongoDB MCP Server.

Built for the **Google Cloud Rapid Agent Hackathon** (MongoDB partner bucket). MIT licensed.

## How it works

1. A content script extracts 3–4 frames from the playing `<video>` via canvas.
2. The extension's service worker POSTs `{url, frames}` to the backend `/analyze` endpoint.
3. A Google ADK agent (Gemini) first checks the MongoDB Atlas cache via the MongoDB MCP Server's `find` tool; on a miss it forensically classifies the frames and writes the verdict back with `insert-many`.
4. A badge appears on the player: 🤖 AI Generated (87%) / ✅ Likely Real (91%).

## Quick start (local)

```bash
# Backend
cd apps/backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy ..\..\.env.example .env                     # fill in GOOGLE_API_KEY + MDB_MCP_CONNECTION_STRING
uvicorn app.main:app --reload --port 8000
```

Extension: open `chrome://extensions` → enable Developer mode → **Load unpacked** → select `apps/extension/`.

Requires Node.js on PATH (the agent spawns `npx -y mongodb-mcp-server@latest` over stdio).

## Honest detection note

Verdicts are Gemini-based visual heuristics (artifacts, lighting/physics inconsistencies, texture smearing), not watermark forensics. Google's SynthID Content Detection API is the proper upgrade path once publicly available.

## Repo map

See [PROJECT.md](PROJECT.md) for the living architecture/status tracker and [PLAN.md](PLAN.md) for the build plan.
