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


@app.get("/healthz")
async def healthz():
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
    try:
        from .agent import run_detection

        result = await run_detection(app.state.runner, request.url, request.frames)
        return AnalyzeResponse(**result)
    except Exception:
        logger.exception("analysis failed for %s", request.url)
        return JSONResponse(
            status_code=502,
            content=AnalyzeResponse(verdict="error", reasons=["analysis failed"]).model_dump(),
        )
