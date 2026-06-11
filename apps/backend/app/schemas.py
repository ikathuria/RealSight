"""Pydantic request/response models for the RealSight API."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# 1 MB of binary JPEG ≈ 1.37 MB of base64 text
MAX_FRAME_B64_CHARS = 1_400_000


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=10, max_length=2048)
    frames: list[str] = Field(..., min_length=1, max_length=5)

    @field_validator("frames")
    @classmethod
    def frames_within_size_limit(cls, frames: list[str]) -> list[str]:
        for i, frame in enumerate(frames):
            if len(frame) > MAX_FRAME_B64_CHARS:
                raise ValueError(f"frame {i} exceeds 1MB limit")
        return frames


class AnalyzeResponse(BaseModel):
    verdict: Literal["ai_generated", "likely_real", "uncertain", "error"]
    confidence: int = Field(0, ge=0, le=100)
    reasons: list[str] = []
    cached: bool = False
