from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import ingest

app = FastAPI(
    title="SentinelAPI",
    description="Real-time API anomaly detection platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # lock this down in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)


@app.get("/")
async def root():
    return {"service": "SentinelAPI", "version": "0.1.0"}