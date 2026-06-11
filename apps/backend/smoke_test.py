"""Smoke test: verifies the ADK agent can reach Atlas through the MongoDB MCP
server and produce a verdict for a tiny synthetic frame.

Run from apps/backend with .env populated:
    .venv\\Scripts\\python smoke_test.py
Expected: first run prints cached: False, second run prints cached: True (<1s).
"""

import asyncio
import base64
import time

from dotenv import load_dotenv

load_dotenv()

from app.agent import build_runner, run_detection  # noqa: E402

TEST_URL = "https://www.youtube.com/watch?v=smoketest123"


def tiny_jpeg_b64() -> str:
    # A 1x1 white JPEG, smallest valid multimodal input
    jpeg = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
        "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
        "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AVN//2Q=="
    )
    return base64.b64encode(jpeg).decode()


async def main():
    runner = build_runner()
    frames = [tiny_jpeg_b64()]

    for attempt in (1, 2):
        start = time.perf_counter()
        result = await run_detection(runner, TEST_URL, frames)
        elapsed = time.perf_counter() - start
        print(f"run {attempt}: {result} ({elapsed:.2f}s)")


if __name__ == "__main__":
    asyncio.run(main())
