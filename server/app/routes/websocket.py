from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json
import redis.asyncio as aioredis
from ..config import settings

router = APIRouter()

# Track connected dashboard clients
connected_clients: List[WebSocket] = []


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    """
    WebSocket endpoint for the React dashboard.
    Subscribes to Redis Pub/Sub for real-time metric + anomaly updates.
    """
    await websocket.accept()
    connected_clients.append(websocket)

    r = aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.psubscribe("metrics:*", "anomaly:*")

    try:
        async for message in pubsub.listen():
            if message["type"] in ("pmessage",):
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()

                await websocket.send_json({
                    "channel": channel,
                    "data": json.loads(data),
                })
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    finally:
        await pubsub.unsubscribe()
        await r.close()