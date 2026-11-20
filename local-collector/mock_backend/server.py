"""Mock central SaaS backend for enterprise evaluation and offline queue testing."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Set
from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

app = FastAPI(
    title="AegisOPS Central Backend (Mock Server)",
    description="Stand-in for central backend to verify Local Collector transmission and idempotency.",
    version="1.0.0",
)

# In-memory storage for test verification
received_messages: List[Dict[str, Any]] = []
seen_message_ids: Set[str] = set()
server_forced_offline: bool = False


@app.middleware("http")
async def simulated_outage_middleware(request: Request, call_next):
    """Simulates server outages when toggled for test scenarios."""
    global server_forced_offline
    # Allow control endpoints even if offline simulation is on
    if server_forced_offline and not request.url.path.startswith("/api/v1/control"):
        return Response(
            content='{"error": "Simulated backend service outage"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )
    return await call_next(request)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AegisCentralBackendMock",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_messages_received": len(received_messages),
    }


@app.post("/api/v1/metrics")
async def receive_metrics(payload: Dict[str, Any], response: Response):
    """Receive and store sanitized metrics with idempotency protection.
    
    If message_id has already been received, acknowledges with 200 without duplication.
    If new, stores message and returns 201 Created.
    """
    message_id = payload.get("message_id")
    if not message_id:
        raise HTTPException(status_code=400, detail="Missing required 'message_id'")

    if message_id in seen_message_ids:
        # Idempotent acknowledgment of duplicate delivery
        response.status_code = status.HTTP_200_OK
        return {
            "status": "duplicate_ignored",
            "message_id": message_id,
            "message": "Payload was previously received and acknowledged; duplicate rejected.",
        }

    # Record message
    seen_message_ids.add(message_id)
    received_messages.append({
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    })

    response.status_code = status.HTTP_201_CREATED
    return {
        "status": "received",
        "message_id": message_id,
        "device_id": payload.get("device_id"),
        "metrics_count": len(payload.get("metrics", {})),
    }


@app.post("/api/v1/heartbeat")
async def receive_heartbeat(payload: Dict[str, Any]):
    """Heartbeat endpoint for collector presence."""
    return {
        "status": "alive",
        "device_id": payload.get("device_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/received")
async def get_received(limit: int = 50):
    """Inspect all received metrics messages (for testing and verification)."""
    return {
        "total": len(received_messages),
        "messages": received_messages[-limit:],
    }


@app.post("/api/v1/control/toggle-outage")
async def toggle_outage():
    """Toggle simulated 503 outage for offline queue testing."""
    global server_forced_offline
    server_forced_offline = not server_forced_offline
    return {"forced_offline": server_forced_offline}


@app.post("/api/v1/control/clear")
async def clear_data():
    """Reset mock server state."""
    global received_messages, seen_message_ids
    received_messages.clear()
    seen_message_ids.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    print("Starting AegisOPS Mock Backend on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
