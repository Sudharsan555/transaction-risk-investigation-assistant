TRACK_ID=PS6

# Transaction Risk Investigation Assistant (PS06)

An intelligent, bank-grade fraud desk investigation assistant built for **NexusTiQ 24 (Track PS06: Banking - Transaction Risk Investigation Assistant)**.

The system features a **strict two-stage architecture**:
1. **Deterministic Risk Engine (Pure Python / Zero LLM Dependency)**: Evaluates full customer transaction histories against individual historical baselines across statistical outlier thresholds, rapid payee bursts, odd-hours activity, and channel deviations.
2. **Grounded GenAI Investigation Layer (Gemini 2.0 Flash / Resilient Deterministic Fallback)**: Translates structured findings and cited transaction rows into a human-readable investigation note with strict evidence citations (`[TXN-xxxx]`), actionable investigator steps, and mandatory compliance disclaimers.

---

## ⚡ HR-Friendly / One-Command Quick Run

For evaluators, recruiters, and judges who want to clone and launch the entire application with a single copy-paste command:

### Windows (PowerShell):
```powershell
git clone https://github.com/Sudharsan555/transaction-risk-investigation-assistant.git; cd transaction-risk-investigation-assistant; pip install -r requirements.txt; python app.py
```

### Linux / macOS:
```bash
git clone https://github.com/Sudharsan555/transaction-risk-investigation-assistant.git && cd transaction-risk-investigation-assistant && pip install -r requirements.txt && python app.py
```

Application serves immediately at 👉 **`http://localhost:8000`**

---

## 🚀 Quick Setup & Run

### 1. Clone the Repository
```bash
git clone https://github.com/Sudharsan555/transaction-risk-investigation-assistant.git
cd transaction-risk-investigation-assistant
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment (Optional)
The system runs immediately out-of-the-box using high-speed deterministic fallback if no API key is set. To enable live Google Gemini 2.0 Flash generation, set your API key:

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="your-gemini-api-key-here"
```

**Linux / macOS:**
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

*(You can also copy `.env.example` to `.env` and paste your key)*

### 4. Run the Application
```bash
python app.py
```
Open **`http://localhost:8000`** in any web browser.

---

## 🤖 Where GenAI Is Used

Gemini functions as the **investigation reasoning and explanation layer** in the fraud desk workflow.

The **deterministic risk engine** first computes mathematical baselines and identifies measurable anomalies (Z-score outliers, burst frequencies, temporal anomalies, and channel deviations).

**Gemini receives strictly structured evidence from the engine**:
- Triggered risk rules and severity levels
- Customer baseline reference metrics (historical average spend, spending ceiling, established active hours)
- Specific cited transaction rows (`transaction_id`, amount, payee, channel, timestamp)

**Gemini converts this evidence into**:
- **Investigator-Ready Explanations**: Translating statistical deviations into plain-English bank context.
- **Risk Correlation Analysis**: Correlating multi-vector anomalies (e.g., connecting a sudden midnight wire transfer with an uncharacteristic new payee).
- **Prioritized Next Steps**: Generating concrete, sequential checklists for human fraud analysts (e.g., out-of-band customer verification, session IP review).
- **Grounded Investigation Reports**: Structured reports where every factual claim references an exact transaction ID.

> **Key Principle**: Gemini does **not** invent risk findings, does not hallucinate transactions, and does **not** make the final legal or business fraud decision. The human investigator remains the ultimate decision-maker.

---

## 🧠 GenAI Reasoning & Prompt Design

The system implements a rigorous two-stage separation of concerns:

### Stage 1 — Deterministic Evidence Generation
Before any GenAI invocation, pure Python code evaluates customer activity against established behavioral profiles to answer:
- **What changed?** (Outlier spend, sudden new counterparty burst, uncharacteristic channel)
- **Which rule was triggered?** (`RULE_LARGE_TRANSFER`, `RULE_NEW_PAYEE_BURST`, `RULE_ODD_HOURS`, `RULE_PATTERN_BREAK`)
- **What is the customer's normal baseline?** (Empirical average, 95th percentile ceiling, active diurnal window)
- **Which transactions triggered the finding?** (Exact transaction IDs and recorded metadata)

### Stage 2 — Grounded Gemini Investigation
Gemini receives *only* the compact JSON evidence payload compiled by Stage 1.

The system prompt enforces **11 strict operational rules**:
1. **Strict Grounding**: Rely ONLY on provided structured findings, baselines, and transactions in the payload. Never invent IDs, amounts, dates, counterparties, or statistics.
2. **No Unsupported Fraud Accusations**: Never declare that "fraud has occurred" or that a customer is guilty. Maintain objective, neutral investigative phrasing.
3. **Tri-Partite Distinction**: Clearly differentiate between:
   - **Evidence**: Verified historical numbers and mathematical metrics.
   - **Suspicion / Risk**: Contextual reasoning on why activity breaks pattern.
   - **Recommendation**: Concrete investigative actions for bank personnel.
4. **Mandatory Citations**: Every factual statement must cite its transaction ID in brackets (`[TXN-xxxx]`).
5. **Honest Handling of Insufficient Evidence**: If an account has zero or minimal transaction history, explicitly state that behavioral evidence is insufficient to establish an empirical baseline. Never extrapolate or imagine activity.
6. **Human Investigator Primacy**: Explicitly remind analysts that final determination rests with authorized fraud desk personnel.
7. **Predictable Output Structure**: Fixed format featuring Verdict line, Executive Summary, Detailed Evidence Breakdown, Correlation Analysis, Action Checklist, and Compliance Disclaimer.

---

## 🏛️ System Architecture

```
Transaction Data (CSV / JSON)
        ↓
Deterministic Risk Engine (Layer 1)
[Pure Python • Z-Scores • Diurnal Windows • Payee Clusters • Channel Baselines]
        ↓
Structured Findings + Cited Transactions
        ↓
Gemini Investigation Layer (Layer 2)
[Google Gemini 2.0 Flash • Strict Grounding • Traceable [TXN-xxxx] Citations]
        ↓
Grounded Investigation Report
        ↓
Human Investigator Decision
```

### Core Design Principles:
- **The Deterministic Engine detects measurable anomalies.**
- **Gemini explains and correlates the evidence.**
- **The Human Investigator makes the final decision.**

---

## 🛡️ Distinguishing "Nothing Flagged" vs "Insufficient Evidence"

The assistant cleanly distinguishes between two non-fraud scenarios:

1. **`NOTHING FLAGGED` (Sufficient History - Routine Account)**:
   - Evaluates full multi-month history (e.g., `CUST-101` with 80+ transactions).
   - Confirms that all transactions strictly adhere to historical spend averages, normal active hours, and familiar counterparties.
   - Outputs an objective, non-alarming confirmation that account behavior is consistent with historical baseline.

2. **`NOTHING FLAGGED` (Insufficient Evidence - Limited History)**:
   - Handles new or empty accounts (e.g., `CUST-199` with 0 transactions).
   - The engine flags `evidence_status: "INSUFFICIENT_EVIDENCE"` without raising false alarms.
   - The investigation note explicitly states that transaction history is insufficient to construct an empirical baseline, recommending standard onboarding monitoring rather than pretending a normal pattern exists.

---

## 🔍 Traceable Citations in the UI

The web interface (`http://localhost:8000`) provides interactive citation traceability:
- **Interactive Citation Tags**: Every transaction referenced in the Gemini report appears as an interactive tag (e.g., `[TXN-1335]`).
- **One-Click Ledger Jump**: Clicking any citation tag instantly scrolls to the corresponding row in the transaction ledger.
- **Visual Pulse Highlight**: The targeted row illuminates with a glowing animated border and highlight pulse, enabling fraud analysts to visually verify the evidence behind every AI statement immediately.

---

## 📊 Dataset Overview

All data resides in `data/`:
- **`customers.json`**: 19 customer profiles with precomputed spend distributions, 95th percentiles, active hours, and known counterparties.
- **`transactions.csv`**: 1,483 realistic multi-month transactions across POS, Mobile, Web, ATM, and Wire channels.
- **`sample_test_inputs.json`**: Curated verification fixtures demonstrating core fraud detection vectors and baseline controls.

### Seeded Account Matrix

| Customer ID | Customer Name | Account Profile | Seeded Anomaly Pattern | Expected Verdict | Risk Score | Evidence Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CUST-104`** | Elena Rostova | Personal Checking | Unusually Large Transfer Outlier ($14,500 Wire vs $115 avg) | `ATTENTION NEEDED` | 80 / 100 | Sufficient History |
| **`CUST-109`** | Marcus Vance | Tech Contractor | Rapid Burst of 3 Transfers to New Crypto Payee | `ATTENTION NEEDED` | 100 / 100 | Sufficient History |
| **`CUST-112`** | Aisha Patel | Senior Consultant | Odd-Hours Activity (03:15 AM & 04:20 AM transfers) | `ATTENTION NEEDED` | 100 / 100 | Sufficient History |
| **`CUST-115`** | David Chen | Retail Store Owner | Channel Break (Unprecedented International Wires) | `ATTENTION NEEDED` | 100 / 100 | Sufficient History |
| **`CUST-118`** | Sophia Morales | Medical Specialist | Multi-Vector Anomaly (Outlier + New Payee + Odd Hours) | `ATTENTION NEEDED` | 100 / 100 | Sufficient History |
| **`CUST-101`** | Alexander Hayes | Standard Checking | Clean Routine History (Adheres to baseline) | `NOTHING FLAGGED` | 0 / 100 | Sufficient History |
| **`CUST-199`** | Lucas Vance | New Account | Empty / Zero Transaction History Edge Case | `NOTHING FLAGGED` | 0 / 100 | Insufficient Evidence |

---

## 🧪 Test Scenarios & Verification Fixtures

You can verify any scenario using the REST API or Web UI at `http://localhost:8000`.

### 1. Test Case 1: Unusually Large Transfer Outlier (`CUST-104`)
```bash
curl http://localhost:8000/api/customers/CUST-104/analysis
```
- `verdict`: `"ATTENTION NEEDED"`
- `risk_score`: `80`
- `findings`: Contains `RULE_LARGE_TRANSFER` citing transaction `TXN-1335` ($14,500.00 wire transfer vs historical avg $115.00).

### 2. Test Case 2: New Payee Rapid Burst (`CUST-109`)
```bash
curl http://localhost:8000/api/customers/CUST-109/analysis
```
- `verdict`: `"ATTENTION NEEDED"`
- `risk_score`: `100`
- `findings`: Contains `RULE_NEW_PAYEE_BURST` citing `["TXN-1718", "TXN-1719", "TXN-1720"]` to new payee `NovaDex Crypto Settlement`.

### 3. Test Case 3: Odd-Hours Diurnal Deviation (`CUST-112`)
```bash
curl http://localhost:8000/api/customers/CUST-112/analysis
```
- `verdict`: `"ATTENTION NEEDED"`
- `risk_score`: `100`
- `findings`: Contains `RULE_ODD_HOURS` citing `["TXN-1941", "TXN-1942"]` occurring at 03:15 AM and 04:20 AM (baseline is 08:00–21:00).

### 4. Test Case 4: Clean Routine Customer (`CUST-101`)
```bash
curl http://localhost:8000/api/customers/CUST-101/analysis
```
- `verdict`: `"NOTHING FLAGGED"`
- `risk_score`: `0`
- `evidence_status`: `"SUFFICIENT_HISTORY"`
- `findings_count`: `0`

### 5. Test Case 5: Empty Transaction History Edge Case (`CUST-199`)
```bash
curl http://localhost:8000/api/customers/CUST-199/analysis
```
- `verdict`: `"NOTHING FLAGGED"`
- `risk_score`: `0`
- `evidence_status`: `"INSUFFICIENT_EVIDENCE"`
- `findings_count`: `0`

### 6. Test Case 6: Custom Payload Sandbox (`POST /api/analyze/custom`)
```bash
curl -X POST http://localhost:8000/api/analyze/custom -H "Content-Type: application/json" -d "{\"transactions\": [{\"transaction_id\": \"CUSTOM-1\", \"timestamp\": \"2026-08-30T03:00:00\", \"amount\": 9500.0, \"payee\": \"Unseen Entity\", \"channel\": \"Wire\"}]}"
```
- `verdict`: `"ATTENTION NEEDED"`
- Cites `CUSTOM-1` for large transfer, odd hours, and uncharacteristic wire channel.

---

## 🧪 Running Automated Tests

Run the full automated test suite (23 unit & integration tests):
```bash
python -m unittest discover tests -v
```

Run live end-to-end verification (with app running on port 8000):
```bash
python tests/verify_live.py
```

---

## ⚠️ System Limitations & Governance Boundaries

1. **Statistical Cold-Start Threshold**: Accounts with fewer than 5 historical transactions cannot mathematically establish a reliable behavioral baseline. The system explicitly returns `INSUFFICIENT_EVIDENCE` without generating phantom risk scores.
2. **Deterministic Risk Precondition**: GenAI (Gemini) is strictly downstream of the deterministic rule engine. Gemini never independently invents fraud flags, alters mathematical deviations, or computes risk scores.
3. **Investigative Urgency vs. Probability of Fraud**: Risk scores (0–100) indicate investigative urgency for human fraud desk analysts. A high score does not represent an empirical probability of fraud or a definitive assertion of guilt.
4. **Data Ingestion Boundary**: The current hackathon implementation parses CSV ledgers and JSON profiles. Enterprise production would ingest via real-time Apache Kafka event streams and BigQuery data warehouses.

---

## 🎥 Demo & Evaluation Walkthrough

To inspect and test the interactive application live:
1. Run `python app.py` (or the one-command quickstart).
2. Open `http://localhost:8000` in any web browser.
3. **Inspect Flagged Investigations**: Click on `CUST-104` (Large Outlier Wire), `CUST-109` (Crypto Payee Burst), or `CUST-112` (Odd-Hours Diurnal Deviation) to review the tri-partite investigation notes, clickable transaction citations `[TXN-xxxx]`, and additive risk score breakdown.
4. **Inspect Clean Routine Customer**: Click on `CUST-101` to verify `NOTHING_FLAGGED` posture with reassuring baseline adherence.
5. **Inspect Sparse Account**: Click on `CUST-199` to verify `INSUFFICIENT_EVIDENCE` handling without false alarms.
6. **Sandbox Custom Payloads**: Click **"Open Custom Sandbox"** in the top-right navbar to test custom transaction payloads with immediate evaluation.

> *Live screen-recorded video walkthrough demonstrating normal vs flagged accounts, citation jump navigation, and custom payload evaluation is prepared for evaluators and judges.*

---

## 📌 Repository Metadata & Topics

- **Description**: `A grounded Gemini-powered transaction risk investigation assistant that detects behavioral anomalies and generates traceable evidence-based investigation reports.`
- **Suggested Topics**: `genai`, `gemini`, `fastapi`, `transaction-risk`, `risk-analysis`, `banking`, `fraud-detection`, `hackathon`

---

## 👨‍💻 Author Details
**Sudharsan V**  
B.E. Computer Science and Engineering, 2023–2027  
V.S.B. College of Engineering Technical Campus  
GitHub: [Sudharsan555](https://github.com/Sudharsan555)  
LinkedIn: [sudharsan555](https://linkedin.com/in/sudharsan555)  
Email: [sudharsanvasu2006@gmail.com](mailto:sudharsanvasu2006@gmail.com)
