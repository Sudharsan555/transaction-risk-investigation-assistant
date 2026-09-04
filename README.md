TRACK_ID=PS6

# Transaction Risk Investigation Assistant (PS06)

An intelligent, bank-grade fraud desk investigation assistant built for **NexusTiQ 24 (Track PS06: Banking - Transaction Risk Investigation Assistant)**.

The system features a **strict two-layer architecture**:
1. **Deterministic Rule Engine (Pure Python / Zero LLM Dependency)**: Evaluates full customer transaction histories against individual historical baselines across statistical outlier thresholds, rapid payee bursts, odd-hours activity, and channel deviations.
2. **Grounded GenAI Investigation Layer (Gemini 2.0 Flash / Resilient Deterministic Fallback)**: Translates structured findings and cited transaction rows into a human-readable investigation note with strict evidence citations (`[TXN-xxxx]`), actionable investigator steps, and mandatory disclaimers.

---

## 🚀 Quickstart & How to Run

### Prerequisites
- Python 3.11+
- (Optional) `GEMINI_API_KEY` for Google Gemini 2.0 Flash live generative reports (system automatically utilizes instant deterministic fallback if key is omitted).

### Single Command Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set your Gemini API Key
# Windows PowerShell:
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# Linux / macOS:
export GEMINI_API_KEY="your-gemini-api-key-here"

# 3. Start application
python app.py
```

The application will start within seconds and serve both backend API and frontend UI at:
👉 **`http://localhost:8000`**

---

## 🎯 Architecture & Strict Separation (Graded Criteria)

```
┌─────────────────────────────────────────────────────────────┐
│                   Customer Transaction Data                 │
│              (1,480+ Txns across 19 Accounts)               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       Layer 1: Deterministic Risk Rule Engine               │
│       (100% Python / Zero LLM / Zero Network Calls)         │
│  - Statistical Large Transfer Outlier Detection (Z-Score)   │
│  - Rapid Burst to Newly-Added Payee (<= 48h Window)        │
│  - Odd-Hours Diurnal Baseline Deviation Detection           │
│  - Channel & Merchant Category Pattern Break Detection      │
│  - Traceable Citation Mapping & Severity Calculation        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Structured Findings + Cited Rows
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       Layer 2: Grounded GenAI Investigation Layer           │
│       (Google Gemini 2.0 Flash / Resilient Fallback)        │
│  - Strict Grounding (Never hallucinates ungrounded data)    │
│  - Objective tone (Never asserts definitive fraud)          │
│  - Explicit transaction ID citations [TXN-xxxx]             │
│  - Formats: VERDICT line, Executive Summary, Evidence,      │
│    Risk Correlation, Action Checklist, Compliance Disclaimer│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       Layer 3: Modern Glassmorphic Web Dashboard            │
│       (FastAPI + Responsive FinTech UI on Port 8000)        │
│  - Customer Queue with live search and filter badges        │
│  - Interactive Transaction Ledger with cited row highlights │
│  - Interactive Sandbox for testing arbitrary payloads       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Synthetic Dataset Generated

All data resides in `data/`:
- **`customers.json`**: 19 customer profiles with precomputed spend distributions, 95th percentiles, active hours, and known counterparties.
- **`transactions.csv`**: 1,483 realistic multi-month transactions across POS, Mobile, Web, ATM, and Wire channels.
- **`sample_test_inputs.json`**: Benchmark test suite fixtures for automated grading and manual checking.

### Seeded Account Matrix

| Customer ID | Customer Name | Account Profile | Seeded Anomaly Pattern | Expected Verdict | Risk Score |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CUST-104`** | Elena Rostova | Personal Checking | Unusually Large Transfer Outlier ($14,500 Wire vs $115 avg) | `ATTENTION NEEDED` | 80 / 100 |
| **`CUST-109`** | Marcus Vance | Tech Contractor | Rapid Burst of 3 Transfers to New Crypto Payee | `ATTENTION NEEDED` | 100 / 100 |
| **`CUST-112`** | Aisha Patel | Senior Consultant | Odd-Hours Activity (03:15 AM & 04:20 AM transfers) | `ATTENTION NEEDED` | 100 / 100 |
| **`CUST-115`** | David Chen | Retail Store Owner | Channel Break (Unprecedented International Wires) | `ATTENTION NEEDED` | 100 / 100 |
| **`CUST-118`** | Sophia Morales | Medical Specialist | Multi-Vector Anomaly (Outlier + New Payee + Odd Hours) | `ATTENTION NEEDED` | 100 / 100 |
| **`CUST-101`** | Alexander Hayes | Standard Checking | Clean Routine History (Adheres to baseline) | `NOTHING FLAGGED` | 0 / 100 |
| **`CUST-199`** | Lucas Vance | New Account | Empty / Zero Transaction History Edge Case | `NOTHING FLAGGED` | 0 / 100 |

---

## 🧪 Inputs & Desired Outputs for Checking (Grading Fixtures)

You can check any scenario using the REST API or Web UI at `http://localhost:8000`.

### 1. Test Case 1: Unusually Large Transfer Outlier (`CUST-104`)

**Input Command (PowerShell / cURL):**
```powershell
curl http://localhost:8000/api/customers/CUST-104/analysis
```

**Desired Output:**
- `verdict`: `"ATTENTION NEEDED"`
- `risk_score`: `80`
- `findings`: Contains `RULE_LARGE_TRANSFER` citing transaction `TXN-1335` ($14,500.00 wire transfer vs historical avg $115.00).
- `llm_report`: Line 1 begins with `VERDICT: ATTENTION NEEDED` and ends with mandatory disclaimer.

---

### 2. Test Case 2: New Payee Rapid Burst (`CUST-109`)

**Input Command:**
```powershell
curl http://localhost:8000/api/customers/CUST-109/analysis
```

**Desired Output:**
- `verdict`: `"ATTENTION NEEDED"`
- `risk_score`: `100`
- `findings`: Contains `RULE_NEW_PAYEE_BURST` citing `["TXN-1718", "TXN-1719", "TXN-1720"]` to new payee `NovaDex Crypto Settlement`.

---

### 3. Test Case 3: Odd-Hours Diurnal Deviation (`CUST-112`)

**Input Command:**
```powershell
curl http://localhost:8000/api/customers/CUST-112/analysis
```

**Desired Output:**
- `verdict`: `"ATTENTION NEEDED"`
- `risk_score`: `100`
- `findings`: Contains `RULE_ODD_HOURS` citing `["TXN-1941", "TXN-1942"]` occurring at 03:15 AM and 04:20 AM (baseline is 08:00–21:00).

---

### 4. Test Case 4: Clean Routine Customer (`CUST-101`)

**Input Command:**
```powershell
curl http://localhost:8000/api/customers/CUST-101/analysis
```

**Desired Output:**
- `verdict`: `"NOTHING FLAGGED"`
- `risk_score`: `0`
- `findings_count`: `0`
- `cited_transactions`: `[]`
- `llm_report`: Line 1 is `VERDICT: NOTHING FLAGGED` with a reassuring, non-alarming baseline adherence explanation.

---

### 5. Test Case 5: Empty Transaction History Edge Case (`CUST-199`)

**Input Command:**
```powershell
curl http://localhost:8000/api/customers/CUST-199/analysis
```

**Desired Output:**
- `verdict`: `"NOTHING FLAGGED"`
- `risk_score`: `0`
- `findings_count`: `0`
- System does not crash or throw exceptions.

---

### 6. Test Case 6: Custom Payload Sandbox (`POST /api/analyze/custom`)

**Input Command:**
```powershell
curl -X POST http://localhost:8000/api/analyze/custom -H "Content-Type: application/json" -d "{\"transactions\": [{\"transaction_id\": \"CUSTOM-1\", \"timestamp\": \"2026-08-30T03:00:00\", \"amount\": 9500.0, \"payee\": \"Unseen Entity\", \"channel\": \"Wire\"}]}"
```

**Desired Output:**
- `verdict`: `"ATTENTION NEEDED"`
- Cites `CUSTOM-1` for large transfer, odd hours, and uncharacteristic wire channel.

---

## 🧪 Running Automated Tests

Run the full automated test suite (23 unit & integration tests):

```bash
python -m unittest discover tests -v
```

---

## 🛡️ Edge Cases Handled

1. **Empty / Near-Empty Transaction Ledger**: Verified with `CUST-199`—outputs confident, non-alarming `NOTHING FLAGGED` status.
2. **Clean Account with Zero Anomalies**: Verified with `CUST-101`—outputs polished, reassuring baseline adherence.
3. **Malformed / Missing Transaction Data**: Gracefully skips `NaN`, negative amounts, or malformed strings without throwing exceptions.
4. **LLM API Timeout / Missing Key**: Automatic deterministic fallback ensures 100% uptime and immediate sub-second responses.
5. **Traceability**: Every fact cited in an investigation report maps to a valid `transaction_id`.

---

## 🎥 Demo Video

- **Demo Video URL**: `https://youtu.be/demo-link-placeholder-ps06` *(2-3 minute demonstration showcasing normal vs flagged investigations, cited transaction highlighting, and custom sandbox test execution)*
