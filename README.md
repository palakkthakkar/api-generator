# SentinelAPI

A real-time API telemetry ingestion and anomaly detection platform.

## What this project contains

- `server/` — FastAPI backend that receives telemetry and stores aggregated metrics.
- `server/app/workers/aggregator.py` — background worker that computes 1-minute metric windows and detects anomalies.
- `dashboard/` — React dashboard UI showing live endpoint metrics and anomaly events.
- `docker-compose.yml` — full-stack development environment with Redis, PostgreSQL, backend, aggregator, and dashboard.
- `scripts/demo_traffic.py` — synthetic traffic generator for demoing the pipeline.

## Recommended way to run it

### 1) Use Docker Compose (best for presentation)

From the repository root:

```powershell
cd c:\Users\thakk\Desktop\api-generator
docker compose up --build
```

This starts:

- `redis` on `localhost:6379`
- `postgres` on `localhost:5432`
- `server` API on `http://localhost:8100`
- `aggregator` worker
- `dashboard` on `http://localhost:3000`

### 2) Open the dashboard

In your browser, visit:

- `http://localhost:3000`

This React app connects to the backend WebSocket at `ws://localhost:8100/ws/dashboard` and loads historical anomalies from `http://localhost:8100/api/v1/dashboard/anomalies`.

### 3) Generate demo traffic

Open a second terminal and run:

```powershell
cd c:\Users\thakk\Desktop\api-generator
python .\scripts\demo_traffic.py --normal-minutes 2 --anomaly-index 0
```

This will send synthetic API telemetry to `http://localhost:8100/api/v1/ingest` and then inject an anomaly.

### 4) What to show during the presentation

- The dashboard endpoint list and metrics charts
- The anomaly feed on the right side
- The terminal output from `demo_traffic.py` showing anomaly injection
- The backend logs showing stored windows and detected anomalies

## Local development setup (alternative)

If you want to run the backend locally without Docker:

1. Create and activate a Python virtual environment

```powershell
cd c:\Users\thakk\Desktop\api-generator
python -m venv .venv
& .venv\Scripts\Activate.ps1
```

2. Install backend dependencies

```powershell
& .venv\Scripts\python.exe -m pip install -r server\requirements.txt
```

> Recommended Python version: **3.11**, because the pinned backend dependencies are tested against that runtime.

3. Install the dashboard dependencies

```powershell
cd dashboard
npm install
```

4. Create a `.env` file at the repo root or in `server/` with these values:

```text
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://sentinel:sentinel@localhost:5432/sentinel
```

5. Start the backend and worker

```powershell
# In one terminal
cd c:\Users\thakk\Desktop\api-generator\server
& .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8100

# In another terminal
cd c:\Users\thakk\Desktop\api-generator\server
& .venv\Scripts\python.exe -m app.workers.aggregator
```

6. Start the dashboard

```powershell
cd c:\Users\thakk\Desktop\api-generator\dashboard
npm start
```

## Key endpoints

- `POST /api/v1/ingest` — ingest telemetry batches
- `GET /api/v1/dashboard/endpoints` — endpoint list and latest status
- `GET /api/v1/dashboard/metrics/{app_name}/{endpoint}` — metrics by endpoint
- `GET /api/v1/dashboard/anomalies` — recent anomalies
- `ws://localhost:8100/ws/dashboard` — live WebSocket stream for metrics and anomalies

## Notes on the current pipeline

- The backend accepts telemetry events and writes them into Redis Streams.
- The aggregator worker reads the streams, computes metric windows, stores them in PostgreSQL, and publishes live metric updates.
- The worker now also trains an anomaly detector after enough windows are collected, and publishes anomaly notifications.
- The dashboard listens to live metric and anomaly updates and displays them in real time.

## Troubleshooting

- If the dashboard cannot connect, make sure the backend is running on `localhost:8100`.
- If `demo_traffic.py` fails, make sure Docker is not blocking host port `8100` and that the backend is healthy.
- Use `docker compose logs -f server` and `docker compose logs -f aggregator` to see live backend logs.
