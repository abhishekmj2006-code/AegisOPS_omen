# AegisOPS — Tier 2: Central SaaS Platform

Multi-tenant, metadata-only observability and AIOps intelligence platform engineered for zero-leakage enterprise monitoring.

---

## Architecture Overview

AegisOPS Central SaaS Platform serves as the central Tier 2 ingestion and analytical intelligence hub:
- **Metadata-Only Ingest:** Receives allow-listed metadata exclusively (`message_id`, `tenant_id`, `device_id`, timestamps, and approved numeric metrics). Zero raw logs, zero passwords, and zero secrets are ever transmitted or stored.
- **Strict Multi-Tenant Separation:** Customer data is partitioned per tenant (`TENANT_001`, `TENANT_002`) with tenant isolation enforced at the repository and query boundary.
- **Idempotency & Deduplication:** Enforces message UUID uniqueness. Duplicates resulting from post-outage collector flushes are acknowledged (`200 OK`) and discarded without corrupting analytics.
- **Out-of-Order Resilient Chronology:** Event time-series queries sort records by UTC event time, ensuring telemetry trends remain accurate regardless of transmission latency.
- **Four-State Health Evaluation:**
  - **Excellent:** Nominal operations within statistical baselines.
  - **Good:** Minor deviations with no service degradation.
  - **Fair:** Warning threshold breach or stale data.
  - **Poor:** Collector offline (heartbeat lost > 60s) or critical incident.
- **AIOps Intelligence Engine:**
  - **Observe:** Real-time multi-dimensional time-series metrics.
  - **Detect:** Rolling baseline statistical anomaly detection (Z-score divergence).
  - **Correlate:** Multi-signal alert-noise reduction (combining latency + loss or compute load into unified incidents).
  - **Recommend:** Plain-language explainable recommendations detailing root cause, contributing signals, and confidence scores.
  - **Act (Autonomous Ops):** Human-in-the-loop review, dry-run simulation, execution, and rollback safeguards with full audit trails.

---

## Quick Start

### 1. Launch Central SaaS Platform
```powershell
cd central-saas
python main.py
```
Or double-click `run_backend.bat` in the repository root.

- **Web Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Privacy Audit Proof:** [http://127.0.0.1:8000/privacy-audit](http://127.0.0.1:8000/privacy-audit)
- **OpenAPI Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Connect Local Collector (Tier 1)
In a second terminal:
```powershell
cd local-collector
python main.py
```
The desktop collector will begin streaming sanitized, allow-listed metadata directly into the Central SaaS Platform.

### 3. Run Automated Tests
```powershell
python -m pytest central-saas/tests/ -v
```
All 11 Tier 2 unit and integration tests pass.
