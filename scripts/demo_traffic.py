"""
Generates realistic synthetic API traffic with injected anomalies.
Run this against your local SentinelAPI to demo the full pipeline.

Usage: python scripts/demo_traffic.py
"""

import httpx
import time
import random
import math
import argparse

SERVER_URL = "http://localhost:8100"
APP_NAME = "demo-shop"

# Simulated endpoints with their "normal" profiles
ENDPOINTS = {
    "GET /api/products": {"latency_base": 30, "latency_std": 10, "error_rate": 0.01, "rps": 50},
    "POST /api/checkout": {"latency_base": 120, "latency_std": 30, "error_rate": 0.02, "rps": 15},
    "GET /api/search": {"latency_base": 80, "latency_std": 25, "error_rate": 0.005, "rps": 40},
    "POST /api/auth/login": {"latency_base": 60, "latency_std": 15, "error_rate": 0.03, "rps": 20},
    "GET /api/recommendations": {"latency_base": 200, "latency_std": 50, "error_rate": 0.01, "rps": 25},
}

# Anomaly scenarios to inject
ANOMALY_SCENARIOS = [
    {
        "name": "Checkout latency spike (DB connection pool exhaustion)",
        "endpoint": "POST /api/checkout",
        "duration_sec": 120,
        "latency_multiplier": 8,
        "error_rate_override": 0.25,
    },
    {
        "name": "Search service error storm (upstream timeout)",
        "endpoint": "GET /api/search",
        "duration_sec": 90,
        "latency_multiplier": 3,
        "error_rate_override": 0.50,
    },
    {
        "name": "Traffic surge on products (viral social media post)",
        "endpoint": "GET /api/products",
        "duration_sec": 180,
        "rps_multiplier": 10,
        "latency_multiplier": 2,
    },
]


def generate_normal_event(endpoint: str, profile: dict, time_of_day_factor: float = 1.0):
    """Generate one normal telemetry event."""
    method, path = endpoint.split(" ", 1)
    latency = max(1, random.gauss(profile["latency_base"], profile["latency_std"]))
    is_error = random.random() < profile["error_rate"]
    
    return {
        "endpoint": path,
        "method": method,
        "status_code": random.choice([500, 502, 503]) if is_error else 200,
        "latency_ms": round(latency * time_of_day_factor, 2),
        "request_size": random.randint(100, 2000),
        "response_size": random.randint(200, 5000),
        "timestamp": time.time(),
        "app_name": APP_NAME,
    }


def generate_anomaly_event(endpoint: str, profile: dict, scenario: dict):
    """Generate one anomalous telemetry event."""
    method, path = endpoint.split(" ", 1)
    latency = max(1, random.gauss(
        profile["latency_base"] * scenario.get("latency_multiplier", 1),
        profile["latency_std"] * 2,
    ))
    error_rate = scenario.get("error_rate_override", profile["error_rate"])
    is_error = random.random() < error_rate
    
    return {
        "endpoint": path,
        "method": method,
        "status_code": random.choice([500, 502, 503, 429]) if is_error else 200,
        "latency_ms": round(latency, 2),
        "request_size": random.randint(100, 2000),
        "response_size": random.randint(50, 500) if is_error else random.randint(200, 5000),
        "timestamp": time.time(),
        "app_name": APP_NAME,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-minutes", type=int, default=10,
                        help="Minutes of normal traffic before injecting anomalies")
    parser.add_argument("--anomaly-index", type=int, default=0,
                        help="Which anomaly scenario to inject (0-2)")
    args = parser.parse_args()

    client = httpx.Client(timeout=5.0)
    print(f"[Demo] Sending normal traffic for {args.normal_minutes} minutes...")
    print(f"[Demo] Then injecting: {ANOMALY_SCENARIOS[args.anomaly_index]['name']}")

    start_time = time.time()
    normal_duration = args.normal_minutes * 60
    anomaly_scenario = ANOMALY_SCENARIOS[args.anomaly_index]
    anomaly_started = False
    anomaly_start_time = None

    while True:
        elapsed = time.time() - start_time
        # Time-of-day effect (sinusoidal)
        tod_factor = 1.0 + 0.3 * math.sin(elapsed / 300 * math.pi)

        batch = []

        for endpoint, profile in ENDPOINTS.items():
            rps = profile["rps"] * tod_factor
            n_events = max(1, int(rps / 10))  # we send every ~100ms

            for _ in range(n_events):
                # Check if we should inject anomaly for this endpoint
                if (elapsed > normal_duration and 
                    endpoint == anomaly_scenario["endpoint"]):
                    
                    if not anomaly_started:
                        print(f"\n[Demo] ⚡ INJECTING ANOMALY: {anomaly_scenario['name']}")
                        anomaly_started = True
                        anomaly_start_time = time.time()
                    
                    anomaly_elapsed = time.time() - anomaly_start_time
                    if anomaly_elapsed < anomaly_scenario["duration_sec"]:
                        batch.append(generate_anomaly_event(endpoint, profile, anomaly_scenario))
                    else:
                        if anomaly_elapsed < anomaly_scenario["duration_sec"] + 5:
                            print(f"[Demo] ✅ Anomaly ended. Back to normal traffic.")
                        batch.append(generate_normal_event(endpoint, profile, tod_factor))
                else:
                    batch.append(generate_normal_event(endpoint, profile, tod_factor))

        # Send batch
        try:
            resp = client.post(f"{SERVER_URL}/api/v1/ingest", json={"events": batch})
            total_rps = sum(p["rps"] for p in ENDPOINTS.values())
            status = "🔴 ANOMALY" if anomaly_started and (time.time() - anomaly_start_time < anomaly_scenario["duration_sec"]) else "🟢 NORMAL"
            print(f"\r[{status}] Sent {len(batch)} events | Elapsed: {elapsed:.0f}s", end="", flush=True)
        except Exception as e:
            print(f"\n[Demo] Error sending: {e}")

        time.sleep(0.1)


if __name__ == "__main__":
    main()