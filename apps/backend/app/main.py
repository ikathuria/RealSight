"""RealSight backend: FastAPI shell hosting the ADK detection agent."""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .schemas import AnalyzeRequest, AnalyzeResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("realsight")

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Built lazily so /healthz works even before env/keys are configured.
    app.state.runner = None
    try:
        from .agent import build_runner

        app.state.runner = build_runner()
        logger.info("ADK runner initialized")
    except Exception:
        logger.exception("ADK runner failed to initialize — /analyze will return 503")
    yield


app = FastAPI(title="RealSight", lifespan=lifespan)

# The extension's service worker calls us from a chrome-extension:// origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "RealSight",
        "description": "AI-generated-video detection agent — Google ADK + Gemini "
        "with a MongoDB Atlas cache via the official MongoDB MCP Server.",
        "endpoints": {"health": "/health", "analyze": "POST /analyze", "docs": "/docs"},
        "repo": "https://github.com/ikathuria/RealSight",
    }


# NOTE: not /healthz — Google Front End reserves that path on run.app and
# returns its own 404 without ever forwarding to the container.
@app.get("/health")
@app.get("/healthz")  # still works locally
async def health():
    return {"status": "ok", "agent_ready": app.state.runner is not None}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    if app.state.runner is None:
        return JSONResponse(
            status_code=503,
            content=AnalyzeResponse(
                verdict="error", reasons=["agent not configured (check env vars)"]
            ).model_dump(),
        )
    import time

    start = time.perf_counter()
    try:
        from .agent import run_detection

        result = await run_detection(app.state.runner, request.url, request.frames)
        logger.info(
            "analyze url=%s frames=%d verdict=%s confidence=%s cached=%s elapsed=%.2fs",
            request.url,
            len(request.frames),
            result["verdict"],
            result["confidence"],
            result["cached"],
            time.perf_counter() - start,
        )
        return AnalyzeResponse(**result)
    except Exception:
        logger.exception(
            "analyze FAILED url=%s frames=%d elapsed=%.2fs",
            request.url,
            len(request.frames),
            time.perf_counter() - start,
        )
        return JSONResponse(
            status_code=502,
            content=AnalyzeResponse(verdict="error", reasons=["analysis failed"]).model_dump(),
        )
