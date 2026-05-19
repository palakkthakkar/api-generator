from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import redis.asyncio as aioredis
from ..config import settings

router = APIRouter()

# Async Redis connection (created on first call)
_redis = None

async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url)
    return _redis


class TelemetryEvent(BaseModel):
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    request_size: int
    response_size: int
    timestamp: float
    app_name: str = "default"
    metadata: dict = {}


class IngestRequest(BaseModel):
    events: List[TelemetryEvent]


@router.post("/api/v1/ingest")
async def ingest_telemetry(payload: IngestRequest):
    """
    Receive a batch of telemetry events and push each to a
    Redis Stream keyed by app_name:endpoint.
    """
    r = await get_redis()
    
    pushed = 0
    for event in payload.events:
        stream_key = f"telemetry:{event.app_name}:{event.endpoint}"
        await r.xadd(
            stream_key,
            {"data": json.dumps(event.model_dump())},
            maxlen=50_000,  # cap stream length per endpoint
        )
        pushed += 1

    return {"status": "ok", "events_ingested": pushed}


@router.get("/api/v1/health")
async def health():
    """Health check endpoint."""
    r = await get_redis()
    await r.ping()
    return {"status": "healthy"}