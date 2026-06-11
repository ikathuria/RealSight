"""RealSight detection agent.

Google ADK (2.x) LlmAgent: Gemini classifies video frames as AI-generated vs
real, using the official MongoDB MCP Server (stdio via npx) as its cache tool
against Atlas `realsight.detections`.

API surface verified against https://adk.dev docs on 2026-06-11.
"""

import base64
import json
import logging
import os
import re
import shutil
import sys
from urllib.parse import parse_qs, urlparse

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

logger = logging.getLogger("realsight.agent")

APP_NAME = "realsight"
MODEL = os.environ.get("REALSIGHT_MODEL", "gemini-flash-latest")
DB_NAME = "realsight"
COLLECTION = "detections"

INSTRUCTION = f"""You are RealSight, a forensic video-frame analyst that detects AI-generated video.

You receive a message containing a normalized video URL and 1-5 JPEG frames extracted from that video.

Follow this exact procedure:

1. CACHE CHECK: call the `find` tool with database "{DB_NAME}", collection "{COLLECTION}",
   and filter {{"url": "<the normalized URL from the message>"}} with a limit of 1.
   - If a document is found, respond immediately with its stored verdict/confidence/reasons
     and "cached": true. Do NOT analyze the frames and do NOT insert anything.

2. ANALYZE (cache miss only): examine the frames for evidence of AI generation:
   - texture smearing, over-smooth or plastic-looking skin, garbled text/logos
   - anatomy errors (hands, teeth, eyes), object boundaries that melt or warp
   - lighting/shadow physics inconsistencies, impossible reflections
   - temporal inconsistencies between frames (objects changing identity)
   - the telltale hyper-saturated, dreamlike quality of current video generators
   Weigh evidence honestly: compression artifacts alone do NOT mean AI-generated.
   Pick verdict "ai_generated" or "likely_real"; use "uncertain" when evidence is weak.
   Confidence is 0-100.

3. CACHE WRITE (cache miss only): call the `insert-many` tool with database "{DB_NAME}",
   collection "{COLLECTION}", and a single document:
   {{"url": <normalized URL>, "verdict": <verdict>, "confidence": <confidence>,
     "reasons": [<reasons>]}}

4. RESPOND with ONLY a raw JSON object, no markdown fences, no prose:
   {{"verdict": "ai_generated"|"likely_real"|"uncertain", "confidence": 0-100,
     "reasons": ["short human-readable reason", ...], "cached": true|false}}
"""


def normalize_url(raw_url: str) -> str:
    """Canonicalize video URLs so cache keys are stable across query-param noise."""
    parsed = urlparse(raw_url)
    host = parsed.netloc.lower().removeprefix("www.")

    if host in ("youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        match = re.match(r"^/(shorts|embed)/([\w-]{6,})", parsed.path)
        if match:
            return f"https://www.youtube.com/watch?v={match.group(2)}"
    elif host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    elif host == "instagram.com":
        match = re.match(r"^/(reels?|p)/([\w-]+)", parsed.path)
        if match:
            return f"https://www.instagram.com/reel/{match.group(2)}/"

    return raw_url.split("#")[0]


def _npx_command() -> str:
    """Resolve npx to a concrete path — bare 'npx' fails on Windows (npx.cmd)."""
    resolved = shutil.which("npx")
    if resolved:
        return resolved
    return "npx.cmd" if sys.platform == "win32" else "npx"


def build_agent() -> LlmAgent:
    connection_string = os.environ.get("MDB_MCP_CONNECTION_STRING", "")
    if not connection_string:
        raise RuntimeError("MDB_MCP_CONNECTION_STRING is not set")

    mongodb_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_npx_command(),
                args=["-y", "mongodb-mcp-server@latest", "--telemetry", "disabled"],
                env={
                    "MDB_MCP_CONNECTION_STRING": connection_string,
                    # npx needs PATH to find node
                    "PATH": os.environ.get("PATH", ""),
                },
            ),
            timeout=30,
        ),
        tool_filter=["find", "insert-many"],
    )

    return LlmAgent(
        model=MODEL,
        name="realsight_detector",
        description="Detects AI-generated video from extracted frames, with a MongoDB Atlas cache.",
        instruction=INSTRUCTION,
        tools=[mongodb_toolset],
    )


def build_runner() -> InMemoryRunner:
    return InMemoryRunner(agent=build_agent(), app_name=APP_NAME)


def _decode_frame(frame_b64: str) -> bytes:
    # Accept both raw base64 and data URLs ("data:image/jpeg;base64,...")
    if frame_b64.startswith("data:"):
        frame_b64 = frame_b64.split(",", 1)[-1]
    return base64.b64decode(frame_b64)


def _parse_verdict(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in agent response: {text[:200]!r}")
    result = json.loads(text[start : end + 1])
    if result.get("verdict") not in ("ai_generated", "likely_real", "uncertain"):
        raise ValueError(f"invalid verdict in agent response: {result!r}")
    return {
        "verdict": result["verdict"],
        "confidence": max(0, min(100, int(result.get("confidence", 0)))),
        "reasons": [str(r) for r in result.get("reasons", [])][:10],
        "cached": bool(result.get("cached", False)),
    }


async def run_detection(runner: InMemoryRunner, url: str, frames_b64: list[str]) -> dict:
    """Run one detection through the agent. Returns verdict dict (see schemas)."""
    normalized = normalize_url(url)

    parts = [
        types.Part(
            text=f"Video URL (normalized cache key): {normalized}\n"
            f"Attached: {len(frames_b64)} frames extracted from this video."
        )
    ]
    for frame in frames_b64:
        parts.append(types.Part.from_bytes(data=_decode_frame(frame), mime_type="image/jpeg"))

    session = await runner.session_service.create_session(app_name=APP_NAME, user_id="extension")

    final_text = ""
    async for event in runner.run_async(
        user_id="extension",
        session_id=session.id,
        new_message=types.Content(role="user", parts=parts),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(p.text or "" for p in event.content.parts)

    logger.info("agent response for %s: %s", normalized, final_text[:500])
    return _parse_verdict(final_text)
