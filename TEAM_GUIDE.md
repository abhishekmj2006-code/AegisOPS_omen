# AegisOPS — Complete Team Member Onboarding & Operating Guide

Welcome to **AegisOPS**! This guide is written so that anyone on the team—even with zero prior knowledge of the codebase—can run, understand, and present this project with confidence in under 5 minutes.

---

## 1. What Is AegisOPS in Simple English?

**AegisOPS** is an **Enterprise IT Observability and AIOps Safe Remediation Platform**.

Imagine you manage hundreds of company laptops or cloud servers. Normally, when a system slows down or fails, an IT administrator has to sift through thousands of noisy log lines to guess what happened.

**AegisOPS automates this entire lifecycle in real time:**
1. **Monitors Edge Machines**: Constantly measures CPU, RAM, Disk I/O, Network Latency, and Login attempts.
2. **Guarantees Zero Data Leakage**: An in-memory sanitizer physically intercepts and removes passwords, API tokens, cookies, and personal secrets before any data leaves the host.
3. **Applies Google Gemini AI**: An integrated AI engine (`gemini-2.5-flash`) analyzes metric deviations, diagnoses the exact technical root cause in plain English, and calculates a confidence score.
4. **Human-in-the-Loop Safe Remediation**: The AI proposes a fix that the operator can safely **simulate in dry-run mode**, **approve**, **execute**, or **roll back** with a single click.

---

## 2. How the System Fits Together (Two-Tier Architecture)

AegisOPS is divided into two separate applications that communicate securely over HTTP REST APIs:

```
┌─────────────────────────────────────────────────────────────┐
│                 TIER 1: LOCAL COLLECTOR                     │
│               (Runs on the Client/Laptop)                   │
│                                                             │
│  • Desktop GUI (CustomTkinter)                              │
│  • Hardware & Network Monitors (Python psutil + sockets)    │
│  • In-Memory Privacy Sanitizer (Strips secrets)             │
│  • SQLite Offline Queue (Buffers data if internet drops)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
               HTTP POST /api/v1/metrics (Bearer Auth)
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    TIER 2: CENTRAL SAAS                     │
│                (Runs on the Server/Cloud)                   │
│                                                             │
│  • FastAPI Backend Server (Port 8000)                       │
│  • Google Gemini AI Engine (gemini-2.5-flash)               │
│  • Central SQLite Database (central_saas.db)                │
│  • Grafana Dark-Theme Web Dashboard (http://localhost:8000) │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Quick Start: How to Run in 60 Seconds

### Prerequisites
* Windows 10/11
* Python 3.10, 3.11, 3.12, or 3.13 installed and added to PATH.

### The 1-Click Launch (Recommended)
In the project root folder `AegisOPS`:
1. Double-click **`start_aegisops.bat`**.
2. **What this does automatically:**
   - Launches the Central SaaS backend in the background on `http://127.0.0.1:8000`.
   - Launches the Local Collector Desktop GUI window.
3. Open your browser to: **`http://127.0.0.1:8000/`**.

### The Manual Terminal Launch (Alternative)
If you prefer running from the command line:
* **Terminal 1 (Backend):**
  ```powershell
  python central-saas/main.py
  ```
* **Terminal 2 (Local Collector GUI):**
  ```powershell
  python local-collector/main.py
  ```

### How to Stop Everything
Double-click **`stop_aegisops.bat`** (or press `Ctrl + C` in the terminals).

---

## 4. Tour of the Local Collector Desktop App (Tier 1)

When the desktop application opens, you will see a navigation sidebar on the left with 6 panels:

| Panel | What It Does & What to Look At |
| :--- | :--- |
| **System Overview** | Live dials showing real-time CPU %, RAM %, and Disk % of your laptop. |
| **Telemetry Graphs** | Real-time scrolling time-series graphs for compute and network latency. |
| **Security & Sanitizer** | **Interactive Leakage Simulator:** Click the red button `Inject Password & AWS API Key`. Watch the counter tick up showing 3 sensitive fields intercepted and scrubbed before serialization. |
| **Egress Proof Audit** | Shows the exact raw JSON payload leaving your machine. Notice that `source_timezone` is your actual timezone and all secret fields are completely missing. |
| **Connection & Queue** | **Offline Resilience Demo:** Shows the SQLite offline queue. Click `Simulate Disconnect` $\rightarrow$ watch pending messages accumulate in local storage $\rightarrow$ click `Reconnect & Flush` $\rightarrow$ watch all messages deliver with zero duplicates. |
| **Collector Settings** | View and configure the backend URL, Tenant ID, and Bearer API Token (masked with a Show/Hide toggle). |

---

## 5. Tour of the Central SaaS Web Dashboard (Tier 2)

Open **`http://127.0.0.1:8000/`** in Google Chrome or any modern browser.

### A. Top Navigation Bar
* **Tenant Selector:** Switch between isolated customer environments (`TENANT_001`).
* **Time Range Buttons:** `Last 5m`, `15m`, `1h` (dynamically filters chart axes).
* **Thresholds Button:** Opens a modal allowing you to adjust anomaly alert thresholds live.
* **Privacy Audit Button:** Opens `/privacy-audit` proving metadata-only ingest.

### B. Top-Row KPIs & SLA Panel
* **Active Collectors:** Number of active nodes reporting.
* **4-State Health Evaluation:** Shows counts of nodes in `Excellent`, `Good`, `Fair`, or `Poor` states (automatically downgrades to Poor if a node stops sending heartbeats for $>60$s).
* **Real-Time SLA & Delivery Reliability:**
  * *Collection-to-Dashboard Latency:* Target $\le 10$s.
  * *Breach-to-Alert Latency:* Target $\le 15$s.
  * *Duplicates Discarded:* Proof of idempotent delivery during reconnects.

### C. Live Evaluation Scenario Controller (Top Interactive Bar)
Five interactive buttons designed to inject instant test scenarios on demand:
1. `⚡ Latency Spike & Loss (>100ms, >3%)` $\rightarrow$ Simulates network transit congestion.
2. `🔥 CPU Saturation (>90%)` $\rightarrow$ Simulates a compute overload.
3. `🛡️ Failed Logins Burst (+5)` $\rightarrow$ Simulates a credential brute-force attack.
4. `⏱️ Out of Order Packets` $\rightarrow$ Tests chronological sorting resilience.
5. `🔄 Reset Nominal Baseline` $\rightarrow$ Restores normal baseline metrics.

### D. Live Charts & Collector Fleet Matrix
* **Host Compute Telemetry:** Live line chart showing CPU (orange) and RAM (purple).
* **Transport Latency & Packet Loss:** Dual-axis chart with latency in ms and packet loss %.
* **Collector Fleet Matrix:** Right column showing your laptop name (`BEAST`), OS (`Windows 11`), collector version, and the collector's own tiny CPU/RAM overhead ($< 0.2\%$ CPU, $\approx 24.5$ MB RAM).

### E. AIOps Correlated Incidents & Explainability (Where the AI Lives!)
When an anomaly occurs, an incident card appears here with:
* **The AI Badge:** Shows `🤖 Google Gemini (gemini-2.5-flash)` (or local fallback if offline).
* **Root Cause Diagnosis:** Exact plain-English technical diagnosis.
* **Why We Flagged:** Why the statistical baseline was breached ($> 2\sigma$ deviation).
* **Contributing Telemetry Signals:** Exact metric delta vs. historical mean.
* **Why This Action:** Safety justification for the proposed fix.
* **Confidence Assessment:** Confidence percentage (e.g., $94\%$).

### F. Autonomous Safe Remediation (Human-in-the-Loop)
Underneath the incident explanation, click through the 4-step remediation lifecycle:
1. Click **`Simulate Pre-check`** $\rightarrow$ Dry-run simulation validates guardrails without state changes.
2. Click **`Approve`** $\rightarrow$ Operator authorizes execution.
3. Click **`Execute Sandbox`** $\rightarrow$ Executes bounded fix and marks incident mitigating.
4. Click **`Rollback Action`** $\rightarrow$ Safely reverts system to preceding baseline parameters.

### G. Audit Ledgers (Bottom Tables)
* **Health State Transition Log:** Immutable log showing every time a machine changed health states (`Good` $\rightarrow$ `Poor` $\rightarrow$ `Fair`) with timestamps in 12-hour AM/PM format and reasons.
* **Remediation Action Audit Trail:** Complete execution and rollback log tracking operator actions.

---

## 6. Standard 3-Minute Demonstration Script

If you need to show AegisOPS to an evaluator, auditor, or technical lead, follow this exact script:

| Time | What to Do | What to Say |
| :---: | :--- | :--- |
| **0:00 - 0:30** | Double click `start_aegisops.bat` and open `http://127.0.0.1:8000`. | *"AegisOPS is a two-tier, AI-driven IT observability and safe autonomous operations platform. On the desktop, Tier 1 collects sanitized telemetry. On the browser, Tier 2 runs central aggregation and AI incident correlation."* |
| **0:30 - 1:15** | On the desktop app, go to **Security & Sanitizer** and click `Inject Password & AWS API Key`. Then switch to **Egress Proof Audit**. | *"Security is zero-trust. Our in-memory sanitizer uses strict allowlists to strip out passwords, AWS keys, and session cookies before serialization. In the Egress Proof panel, you can verify that only clean numerical metadata leaves the machine."* |
| **1:15 - 2:00** | On the web dashboard, click **`⚡ Latency Spike & Loss`** in the Scenario Controller. | *"Watch the live chart jump. Within 2 seconds, our Google Gemini AI Copilot correlates the latency spike with zero packet loss, rules out a cable break, and diagnoses transit routing delay with 88% confidence."* |
| **2:00 - 2:30** | On the incident card, click `Simulate Pre-check`, then `Approve`, then `Execute Sandbox`. | *"Remediation is safe and human-in-the-loop. The operator runs a simulated dry-run, approves the action, executes it within safety guardrails, and can trigger an instant rollback."* |
| **2:30 - 3:00** | Show the **Health State Transition Log** and click **Privacy Audit** in the top bar. | *"Every health shift and action is logged in an immutable audit ledger. Finally, the Privacy Audit page proves tenant data isolation and zero secret ingestion in central SaaS storage."* |

---

## 7. How to Run Automated Verification Tests

To verify that 100% of the platform is functional and free of regressions, run:

```powershell
python -m pytest local-collector/tests/ central-saas/tests/ -v
```

**Expected Result:**
```
============================== 48 passed in ~4.8s ==============================
```
All 48 unit and integration tests across both tiers pass cleanly.

---

## 8. Troubleshooting & FAQ

* **Q: The dashboard says "Deterministic AIOps Engine (Local Fallback)" instead of "Google Gemini".**  
  *A:* Make sure your free Gemini API key is placed in `central-saas/.env` as:  
  `GEMINI_API_KEY=AIzaSy...`  
  If the key is missing or offline, the local fallback runs automatically so nothing ever crashes.
* **Q: Port 8000 is already in use.**  
  *A:* Run `stop_aegisops.bat` to kill any leftover Python instances, or run `Get-Process python | Stop-Process -Force` in PowerShell.
* **Q: Are all timestamps in 12-hour format?**  
  *A:* Yes, all charts, heartbeat displays, and audit tables render in standard 12-hour `hh:mm:ss AM/PM` format.
* **Q: Where is data physically stored?**  
  *A:* Tier 1 stores pending offline messages in `local-collector/collector_queue.db`. Tier 2 stores all records, incidents, and audit trails in `central-saas/central_saas.db`. Both use SQLite with zero external database dependencies.
