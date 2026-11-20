# AegisOPS — Secure IT Monitoring Platform | Local Collector

> **Enterprise Edition**: Production-quality, modular Python desktop collector monitoring host system telemetry, enforcing strict data sanitization, verifying zero data leakage via an Egress Proof Panel, and ensuring resilient offline delivery with server-side idempotency.

---

## 🛡️ Architecture & Security Model

The **Local Collector** is engineered with a strict **Zero-Trust, Zero-Leakage** security model. Rather than relying solely on blacklists or regular expressions, the collector implements:

1. **Multi-Stage Structured Sanitization Engine**: Inspects all input dictionaries recursively.
2. **Explicit Allowlisting**: Only predefined, approved numeric metrics and top-level metadata keys are permitted through the egress gate.
3. **Pydantic Validation with `extra="forbid"`**: Rejects any outgoing payload containing unrecognized fields or invalid data types.
4. **Secret Scrubbing Filter**: All log records pass through a redaction filter, preventing passwords, API tokens, JWTs, and private keys from appearing even in local debug logs.
5. **Egress Proof & Audit Panel**: Provides security engineers and auditors with live, side-by-side visibility of (A) Raw Local Input, (B) Sanitization Report, and (C) the Exact Outgoing JSON, with visual validation badges (GREEN, YELLOW, RED).
6. **Persistent SQLite Offline Queue & At-Least-Once Delivery**: Outgoing messages are persisted to local SQLite storage *before* network transmission is attempted. Records are only removed or marked acknowledged upon receiving valid server confirmation (HTTP 200/201/208).
7. **Server-Side Idempotency**: Each payload carries a unique UUIDv4 `message_id`. If network interruptions cause a retry of an already-processed message, the server acknowledges duplicate receipt without double-counting metrics.

---

## 📁 Project Directory Structure

```text
local-collector/
│
├── main.py                     # Primary entry point (GUI, headless, test-run)
├── demo.py                     # Self-contained automated enterprise verification script
├── requirements.txt            # Python dependencies with compatible versions
├── .env.example                # Sample environment variables
├── README.md                   # Complete architectural and usage documentation
│
├── config/
│   ├── __init__.py
│   └── settings.py             # Configurable settings loaded from .env
│
├── collector/
│   ├── __init__.py
│   ├── collector_service.py    # Background orchestrator for monitoring & delivery
│   ├── system_monitor.py       # CPU, RAM, OS, and architecture metrics
│   ├── network_monitor.py      # Network speeds, TCP/ping latency & packet loss
│   ├── disk_monitor.py         # Disk space percentage & read/write I/O rates
│   └── login_monitor.py        # Failed login tracking (OS Event log & test stream)
│
├── security/
│   ├── __init__.py
│   ├── sanitizer.py            # Recursive allowlist engine & secret stripper
│   ├── validator.py            # Pydantic schema validation enforcement
│   └── allowlist.py            # Approved key sets and forbidden field definitions
│
├── communication/
│   ├── __init__.py
│   ├── api_client.py           # FastAPI-compatible REST client using httpx
│   ├── connection_manager.py   # Connection health monitor and state callbacks
│   └── retry_manager.py        # Exponential backoff with random jitter & queue flush
│
├── database/
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy SQLite model for queued messages
│   ├── storage.py              # Thread-safe SQLite database manager
│   └── offline_queue.py        # Persistent FIFO queue operations
│
├── interface/
│   ├── __init__.py
│   ├── app.py                  # Main CustomTkinter desktop window & navigation
│   ├── overview.py             # Page 1: Host specifications & live metrics cards
│   ├── system_monitor_panel.py # Page 2: Real-time telemetry graphs (CPU, RAM, Disk, Net)
│   ├── security_panel.py       # Page 3: Sanitization statistics & secret injection suite
│   ├── egress_panel.py         # Page 4: Egress Proof audit panel (Sections A, B, C)
│   ├── connection_panel.py     # Page 5: Backend connection status & SQLite queue table
│   └── settings_panel.py       # Page 6: Runtime endpoint & parameter configuration
│
├── models/
│   ├── __init__.py
│   ├── metric.py               # Pydantic SystemMetrics model
│   └── payload.py              # Pydantic OutgoingPayload model
│
├── utils/
│   ├── __init__.py
│   ├── logger.py               # Secret-redacting structured logger
│   └── timestamps.py           # UTC ISO 8601 timestamp helpers
│
├── mock_backend/
│   ├── __init__.py
│   └── server.py               # Standalone FastAPI mock server with idempotency & outage simulation
│
└── tests/
    ├── __init__.py
    ├── test_collector.py       # Unit tests for CPU, RAM, Disk, Network, Login monitors
    ├── test_sanitizer.py       # Tests for password/key stripping and allowlisting
    ├── test_payload.py         # Tests for Pydantic schemas, UUIDs, extra='forbid'
    ├── test_offline_queue.py   # Tests for SQLite storage and retry persistence
    ├── test_communication_and_retry.py  # Tests for backoff, connection errors, timeouts
    └── test_end_to_end_flow.py # End-to-end integration test (outage, retry, idempotency)
```

---

## 💻 Tech Stack & Requirements

- **Python**: 3.11+ (Tested on Python 3.13)
- **GUI**: `customtkinter`, `Pillow`, `matplotlib`
- **Telemetry**: `psutil`, `socket`, `platform`, `subprocess`
- **Networking**: `httpx`, `asyncio`
- **Validation & Models**: `pydantic` v2 (`extra="forbid"`)
- **Persistence**: `sqlalchemy`, `sqlite3`
- **Configuration & Security**: `python-dotenv`, `cryptography`, `uuid`
- **Backend & Testing**: `fastapi`, `uvicorn`, `pytest`, `pytest-asyncio`

---

## 🚀 Quickstart & Setup

### 1. Install Dependencies
```bash
pip install -r local-collector/requirements.txt
```

### 2. Run Automated Enterprise Verification Suite
To immediately run an end-to-end demonstration verifying all 6 major architectural requirements:
```bash
cd local-collector
python demo.py
```
This script runs a complete scenario showing:
- Real machine CPU, RAM, Disk, and Network telemetry collection.
- Secret injection (passwords, AWS keys, JWTs) intercepted and stripped with zero leakage.
- Simulated backend outage with persistent SQLite queueing.
- Backend recovery and automatic queue flush.
- Server-side idempotency duplicate rejection.

### 3. Run Automated Pytest Suite
Run the full test suite covering all 10 testing requirements:
```bash
cd local-collector
python -m pytest tests/ -v
```

---

## 🖥️ Running the Application

### Option A: Launch Desktop GUI
```bash
cd local-collector
python main.py
```

#### GUI Pages:
1. **Overview**: Host device specifications, operating system, real-time CPU, RAM, Disk, and Network status cards.
2. **System Monitor**: Live matplotlib telemetry graphs updating every second (CPU, RAM, Disk, Network latency).
3. **Security & Sanitizer**: Sanitization statistics, zero-leakage verification badge, and an interactive **Secret Injection Simulator** allowing security auditors to inject passwords, tokens, and test attack events.
4. **Egress Proof Panel**: Live audit screen displaying:
   - **Section A**: Local Input (raw collected telemetry & input events)
   - **Section B**: Sanitization Report (number of sensitive fields detected and removed, validation status)
   - **Section C**: Outgoing Payload (exact sanitized JSON transmitted)
   - **Visual Status Badges**:
     - 🟢 **GREEN**: Payload validated and transmitted.
     - 🟡 **YELLOW**: Payload stored in SQLite offline queue.
     - 🔴 **RED**: Payload rejected due to validation failure.
5. **Connection & Offline Queue**: Backend connection state, queue metrics, persistent SQLite message table, and a **Manual Retry Now** button.
6. **Settings**: Configurable backend URL, tenant ID, device ID, collection interval, and latency target.

### Option B: Run in Headless Daemon Mode
For background or server environments without a display:
```bash
cd local-collector
python main.py --headless
```

### Option C: Run Mock Backend Server
To test live HTTP transmission against the standalone FastAPI mock backend:
```bash
# Terminal 1: Start Mock Backend
cd local-collector
python mock_backend/server.py

# Terminal 2: Run Desktop GUI or Collector
cd local-collector
python main.py
```

The mock backend runs on `http://127.0.0.1:8000` and provides:
- `GET /api/v1/health`
- `POST /api/v1/metrics` (with duplicate detection & idempotency support)
- `POST /api/v1/heartbeat`
- `GET /api/v1/received` (inspect all received payloads)
- `POST /api/v1/control/toggle-outage` (toggle simulated 503 backend outage)

---

## 📋 Standardized Outgoing Payload Specification

All outgoing telemetry transmitted to the central backend adheres to this strict JSON schema:

```json
{
  "message_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "tenant_id": "TENANT_001",
  "device_id": "DEVICE_001",
  "timestamp": "2026-11-20T10:00:00.000000Z",
  "region": "ap-south-1",
  "metrics": {
    "cpu_usage": 45.2,
    "ram_usage": 68.1,
    "ram_total_gb": 16.0,
    "ram_available_gb": 5.1,
    "disk_usage": 72.0,
    "disk_read_mbs": 1.25,
    "disk_write_mbs": 3.40,
    "network_upload_kbps": 12.5,
    "network_download_kbps": 45.8,
    "network_latency_ms": 24.0,
    "packet_loss_percent": 0.0,
    "failed_login_count": 0
  },
  "collector_status": "online"
}
```

Any unrecognized top-level or metrics key is stripped by the sanitizer and strictly forbidden by Pydantic's `extra="forbid"`.

---

## 🔒 Verification & Compliance Checklist

| Feature | Implementation | Verified By |
|---|---|---|
| **Real System Monitoring** | psutil, socket, platform, disk I/O, network throughput | `test_collector.py` & UI Overview |
| **Data Sanitization** | Strict allowlist, recursive stripper, secret heuristics | `test_sanitizer.py` & Security Panel |
| **Zero-Leakage Guarantee** | No passwords, tokens, JWTs, AWS keys, or PII transmitted | `test_sanitizer.py` & `demo.py` |
| **Strict Schema Validation** | Pydantic v2 `extra="forbid"`, UUIDv4, ISO8601 UTC | `test_payload.py` |
| **Egress Proof Panel** | Live 3-section audit view (A/B/C) with visual color badges | `interface/egress_panel.py` |
| **Persistent Offline Queue** | SQLite persistent storage before network attempt | `test_offline_queue.py` |
| **Resilient Retry & Backoff** | Exponential backoff with random jitter | `test_communication_and_retry.py` |
| **Server Idempotency** | Message ID deduplication preventing repeat processing | `test_end_to_end_flow.py` & `demo.py` |
| **Desktop Application** | Modern dark theme, CustomTkinter, live charts | `interface/app.py` |
| **Automated Test Suite** | 21 passing automated tests covering all 10 requirements | `pytest tests/ -v` |
