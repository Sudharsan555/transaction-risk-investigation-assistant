TRACK_ID=PS06

# Transaction Risk Investigation Assistant (PS06)

An intelligent, bank-grade fraud desk investigation assistant built for **NexusTiQ 24 (Track PS06: Banking - Transaction Risk Investigation Assistant)**.

The system features a **strict two-stage architecture**:
1. **Deterministic Risk Engine (Pure Python / Zero LLM Dependency)**: Evaluates full customer transaction histories against individual historical baselines across statistical outlier thresholds, rapid payee bursts, odd-hours activity, and channel deviations.
2. **Grounded GenAI Investigation Layer (Gemini 3.6 Flash / Gemini 3.5 Flash Lite / Resilient Deterministic Fallback)**: Translates structured findings and cited transaction rows into a human-readable investigation note with strict evidence citations (`[TXN-xxxx]`), actionable investigator steps, and mandatory compliance disclaimers.

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

## 🎯 Evaluator & Judge Testing Guide: How to Supply JSON Test Cases

Evaluators and automated grading testbeds can test arbitrary JSON test cases through any of **4 frictionless methods**:

### Method 1: Headless CLI Evaluation (No Server or Browser Needed)
To evaluate any JSON test case file directly from terminal:
```bash
python evaluate.py path/to/testcase.json
```
For pure machine-readable JSON output (ideal for automated grading scripts):
```bash
python evaluate.py --json path/to/testcase.json
```
Or via stdin piping:
```bash
cat testcase.json | python evaluate.py
```

### Method 2: Web Dashboard Sandbox (Interactive UI + File Upload)
1. Open **`http://localhost:8000`** in your browser.
2. Click **🧪 Sandbox / Custom Test** in the top navigation bar.
3. Choose your preferred input method:
   - **Click 1-Click Presets**: Test large outliers, odd hours, payee bursts, sparse accounts, etc.
   - **Click "📁 Upload JSON File"**: Select any `.json` test file directly from your computer.
   - **Drag & Drop**: Drag a `.json` file directly onto the payload text area.
   - **Paste Raw JSON**: Paste any test case JSON directly into the editor.
4. Click **Run Sandbox Investigation** — the dossier, metrics, citations, and grounded report render instantly.

### Method 3: Interactive Swagger API Docs (`/docs`)
1. Open **`http://localhost:8000/docs`**
2. Expand **`POST /api/analyze/custom`**
3. Click **Try it out**, paste your JSON test payload, and click **Execute**.

### Method 4: Automated cURL / API Integration
```bash
curl -X POST "http://localhost:8000/api/analyze/custom" \
     -H "Content-Type: application/json" \
     -d @path/to/testcase.json
```

---

### 🛡️ Zero-Friction Input Compatibility Guarantee
The evaluation engine is engineered to accept **any standard bank or benchmark JSON format without throwing syntax or mapping errors**:
- ✅ **Anti-Contamination Split Schema**: `{ "historical_transactions": [...], "observed_transactions": [...] }`
- ✅ **Legacy Flat Schema**: `{ "transactions": [...] }` (Auto-partitions baseline vs evaluated transactions)
- ✅ **Raw JSON Array**: `[ { "transaction_id": "...", "amount": ... }, ... ]`
- ✅ **Interchangeable Field Names**: Automatically maps `merchant`, `counterparty`, `recipient`, or `description` to `payee`.
- ✅ **Standard ISO-8601 Timestamps**: Full support for timestamps with or without `Z` suffix (`2026-08-01T10:00:00Z` or `2026-08-01T10:00:00`).
- ✅ **Sanitized Amounts**: Accepts numeric floats (`45.00`) or formatted strings (`"$45.00"`).
- ✅ **Zero Phantom Scores**: Accounts with $< 5$ transactions strictly return `INSUFFICIENT_EVIDENCE` (Score = `0/100`).

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
The system runs immediately out-of-the-box using high-speed deterministic fallback if no API key is set. To enable live Google Gemini generation (default model: `gemini-3.6-flash`), set your API key:

The application uses **Google Gemini ONLY** via official `google-genai` SDK. It reads the API key strictly from `GEMINI_API_KEY`. No OpenAI, Claude, Groq, hosted vector databases, or external RAG services are used. If Gemini is unavailable, times out, or returns invalid facts, the application gracefully and safely falls back to the deterministic report.

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
Transaction History
        ↓
Deterministic Risk Engine (Layer 1)
[Pure Python • Baseline Separation • Z-Scores • Diurnal Windows • Payee Clusters • Channel Baselines]
        ↓
Verified Findings + Cited Transactions
        ↓
Gemini Investigation Layer (Stage 2)
[Google Gemini 3.6 Flash / 3.5 Flash Lite • Grounded Prompting • Traceable [TXN-xxxx] Citations]
        ↓
Post-Generation Citation & Fact Validation Firewall
[Hallucination Stripping • Factual Amount/Date/Channel Cross-Verification • Safe Fallback Guard]
        ↓
Grounded Investigation Report
        ↓
Human Investigator (Final Legal & Business Decision)
```

### Core Design Principles:
- **Transaction History → Deterministic Risk Engine → Verified Findings → Gemini Explanation → Citation Validation → Human Investigator.**
- **Gemini must NEVER independently decide fraud.** Gemini's sole responsibility is objective evidence translation, multi-vector correlation, and investigator action recommendation.
- **Human investigator primacy**: The final fraud determination, account restriction, and legal assessment rest exclusively with human fraud desk personnel.

---

## 🛡️ Distinguishing "Nothing Flagged" vs "Insufficient Evidence"

The assistant cleanly distinguishes between three standardized verdicts:

1. **`ATTENTION_REQUIRED` (Verified Baseline Deviations)**:
   - Evaluates account transactions against established multi-month historical baseline.
   - Identified measurable anomalies across statistical outliers, rapid new payee bursts, odd-hours activity, or channel pattern breaks.

2. **`NOTHING_FLAGGED` (Sufficient History - Routine Account)**:
   - Evaluates full multi-month history (e.g., `CUST-101` with 80+ transactions).
   - Confirms that all transactions strictly adhere to historical spend averages, normal active hours, and familiar counterparties.
   - Outputs an objective, non-alarming confirmation that account behavior is consistent with historical baseline.

3. **`INSUFFICIENT_EVIDENCE` (Limited History < 5 Transactions)**:
   - Handles new or sparse accounts (e.g., `CUST-198` with 2 transactions, or `CUST-199` with 0 transactions).
   - The engine flags `evidence_status: "INSUFFICIENT_EVIDENCE"` without generating phantom risk scores.
   - The investigation note explicitly states that transaction history is insufficient (< 5 transactions) to construct a reliable empirical baseline, recommending standard onboarding monitoring rather than pretending a normal pattern exists.

---

## 🔍 Traceable Citations in the UI

The web interface (`http://localhost:8000`) provides interactive citation traceability:
- **Interactive Citation Tags**: Every transaction referenced in the Gemini report appears as an interactive tag (e.g., `[TXN-1318]`).
- **One-Click Ledger Jump**: Clicking any citation tag instantly scrolls to the corresponding row in the transaction ledger.
- **Visual Pulse Highlight**: The targeted row illuminates with a glowing animated border and highlight pulse, enabling fraud analysts to visually verify the evidence behind every AI statement immediately.

---

## 📊 Dataset Overview

All data resides in `data/`:
- **`customers.json`**: 20 customer profiles with precomputed spend distributions, 95th percentiles, active hours, and known counterparties.
- **`transactions.csv`**: 1,485 realistic multi-month transactions across POS, Mobile, Web, ATM, and Wire channels.
- **`sample_test_inputs.json`**: Curated verification fixtures demonstrating core fraud detection vectors and baseline controls.

### Seeded Account Matrix

| Customer ID | Customer Name | Account Profile | Seeded Anomaly Pattern | Expected Verdict | Risk Score | Evidence Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CUST-104`** | Elena Rostova | Personal Checking | Unusually Large Transfer Outlier ($14,500 Wire vs $115 avg) | `ATTENTION_REQUIRED` | 80 / 100 | Sufficient History |
| **`CUST-109`** | Marcus Vance | Tech Contractor | Rapid Burst of 3 Transfers to New Crypto Payee | `ATTENTION_REQUIRED` | 100 / 100 | Sufficient History |
| **`CUST-112`** | Aisha Patel | Senior Consultant | Odd-Hours Activity (03:15 AM & 04:20 AM transfers) | `ATTENTION_REQUIRED` | 100 / 100 | Sufficient History |
| **`CUST-115`** | David Chen | Retail Store Owner | Channel Break (Unprecedented International Wires) | `ATTENTION_REQUIRED` | 100 / 100 | Sufficient History |
| **`CUST-118`** | Sophia Morales | Medical Specialist | Multi-Vector Anomaly (Outlier + New Payee + Odd Hours) | `ATTENTION_REQUIRED` | 100 / 100 | Sufficient History |
| **`CUST-101`** | Alexander Hayes | Standard Checking | Clean Routine History (Adheres to baseline) | `NOTHING_FLAGGED` | 0 / 100 | Sufficient History |
| **`CUST-198`** | Zoe Kensington | Recent Account | Sparse History Edge Case (2 transactions < 5 minimum) | `INSUFFICIENT_EVIDENCE` | 0 / 100 | Insufficient Evidence |
| **`CUST-199`** | Lucas Vance | New Account | Empty / Zero Transaction History Edge Case | `INSUFFICIENT_EVIDENCE` | 0 / 100 | Insufficient Evidence |

---

## 🏆 Judge & Evaluator Testing Guide (Zero-Friction Evaluation)

We have engineered four distinct evaluation methods catering to both non-technical business judges and automated technical testbeds:

```
┌────────────────────────────────────────────────────────────────────────┐
│               EVALUATOR & JUDGE TESTING WORKFLOWS                      │
├──────────────────────────┬─────────────────────────────────────────────┤
│ 1. Zero-JSON 1-Click UI  │ Click "⚡ Run Test Instantly" on any card    │
│ 2. Drag-and-Drop Upload  │ Drop any .json test file into Web Sandbox   │
│ 3. Standalone CLI Tool   │ python evaluate.py test_cases/ (No server!) │
│ 4. Swagger / OpenAPI     │ http://localhost:8000/docs                  │
└──────────────────────────┴─────────────────────────────────────────────┘
```

### Method 1: Zero-JSON 1-Click Benchmark Suite (Recommended for Judges)
*Ideal for evaluators who do not want to write or format raw JSON.*
1. Open `http://localhost:8000` in your web browser.
2. Click **"🧪 Sandbox Analyzer"** in the top navigation bar.
3. On the **⚡ 1-Click Scenarios (Zero JSON Needed)** tab, browse the categorized scenario benchmark cards:
   - **🚨 Section 1: High-Risk Behavioral Anomalies**
     - **Case 1: Large Wire Outlier** (`CUST-104` Elena Rostova): $14,500 wire outlier vs $109 spend baseline.
     - **Case 2: New Payee Burst** (`CUST-109` Marcus Vance): 3 rapid successive payments to unseen crypto payee.
     - **Case 3: Odd-Hours Activity** (`CUST-112` Aisha Patel): 03:15 AM & 04:20 AM diurnal window violations.
     - **Case 4: Pattern Break** (`CUST-115` David Chen): Sudden uncharacteristic high-value wire transfers.
     - **Case 5: Multi-Vector Anomaly** (`CUST-118` Sophia Morales): Concurrent outlier + new payee + odd hours.
   - **✅ Section 2: Normal Baseline Adherence Control**
     - **Case 6: Clean Baseline Customer** (`CUST-101` Alexander Hayes): 85 routine transactions adhering to baseline.
   - **⏳ Section 3: Data Quality & Cold-Start Limits**
     - **Case 7: Empty History Edge Case** (`CUST-199` Lucas Vance): 0 transactions returning `INSUFFICIENT_EVIDENCE`.
     - **Case 8: Sparse History Edge Case** (`CUST-198` Zoe Kensington): 2 transactions (< 5 minimum reliable baseline).
4. Click **"⚡ Run Test Instantly"** on any card:
   - Evaluates the scenario immediately, computes additive risk scores, generates the grounded Gemini report, and lights up traceable citations in the transaction ledger.

---

### Method 2: Drag-and-Drop / Custom File Upload (Web UI)
*Ideal for evaluators who have their own `.json` test files.*
1. In the Sandbox modal, switch to the **"📁 Custom JSON / File Upload"** tab.
2. **Drag & Drop** your `.json` file into the dashed dropzone (or click *"browse from your computer"*).
3. The editor automatically reads and formats the JSON.
4. Click **"Run Sandbox Investigation"** to execute the pipeline.
5. *Need to fix syntax?* Click **"✨ Format JSON"** to automatically strip markdown code blocks and format braces.

---

### Method 3: Standalone Headless CLI (`evaluate.py`)
*Ideal for automated grading testbeds, terminal evaluators, or headless CI environments without starting a web server or binding port 8000.*

```bash
# 1. Run the entire test suite in batch (evaluates all 8 scenarios in 2 seconds):
python evaluate.py test_cases

# 2. Run any specific test case file:
python evaluate.py test_cases/01_large_outlier_wire.json

# 3. Output raw JSON response only (ideal for automated grading scripts):
python evaluate.py test_cases/01_large_outlier_wire.json --json

# 4. Pipe JSON directly via stdin:
cat test_cases/01_large_outlier_wire.json | python evaluate.py --json
```

---

### Method 4: Interactive Swagger / OpenAPI Docs
*Ideal for REST API testing.*
- Open: `http://localhost:8000/docs`
- Expand `POST /api/analyze/custom`, click **"Try it out"**, paste any payload, and click **"Execute"**.

---

## 📋 How Evaluators Can Test Different Input JSON Payloads

The system includes 8 ready-to-test JSON files in the [`test_cases/`](file:///C:/Users/Vsb_Aids_pc292/.gemini/antigravity/scratch/transaction-risk-investigation-assistant/test_cases) directory. Evaluators can use these files directly or model their own test cases on them.

### Quick Testcase Matrix & CLI Commands

| Scenario File | Target Account | Seeded Anomaly Vector | Expected Verdict | Expected Risk Score | Quick Command |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `01_large_outlier_wire.json` | `CUST-104` Elena Rostova | $14,500 Outbound Wire (132x average spend) | `ATTENTION_REQUIRED` | `80 / 100` | `python evaluate.py test_cases/01_large_outlier_wire.json` |
| `02_new_payee_burst.json` | `CUST-109` Marcus Vance | 3 Rapid Transfers to New Crypto Payee | `ATTENTION_REQUIRED` | `100 / 100` | `python evaluate.py test_cases/02_new_payee_burst.json` |
| `03_odd_hours_activity.json` | `CUST-112` Aisha Patel | Transactions at 03:15 AM & 04:20 AM | `ATTENTION_REQUIRED` | `100 / 100` | `python evaluate.py test_cases/03_odd_hours_activity.json` |
| `04_pattern_break_wire.json` | `CUST-115` David Chen | Unprecedented High-Value International Wires | `ATTENTION_REQUIRED` | `100 / 100` | `python evaluate.py test_cases/04_pattern_break_wire.json` |
| `05_multi_vector_fraud.json` | `CUST-118` Sophia Morales | Concurrent Outlier + New Payee + Odd Hours | `ATTENTION_REQUIRED` | `100 / 100` | `python evaluate.py test_cases/05_multi_vector_fraud.json` |
| `06_clean_baseline.json` | `CUST-101` Alexander Hayes | 85 Routine Transactions Conforming to Baseline | `NOTHING_FLAGGED` | `0 / 100` | `python evaluate.py test_cases/06_clean_baseline.json` |
| `07_empty_history_edge_case.json` | `CUST-199` Lucas Vance | Brand New Account (0 Transactions) | `INSUFFICIENT_EVIDENCE` | `0 / 100` | `python evaluate.py test_cases/07_empty_history_edge_case.json` |
| `08_sparse_history_edge_case.json` | `CUST-198` Zoe Kensington | Sparse History (2 Transactions < 5 threshold) | `INSUFFICIENT_EVIDENCE` | `0 / 100` | `python evaluate.py test_cases/08_sparse_history_edge_case.json` |

---

### Supported JSON Payload Schemas

When evaluators provide their own JSON files, the assistant supports two flexible input structures:

#### Schema A: Strict Baseline Separation (Recommended)
Guarantees mathematical anti-contamination: the behavioral baseline is computed **exclusively** from `historical_transactions`, and `observed_transactions` are evaluated against that baseline:

```json
{
  "customer_profile": {
    "customer_id": "CUST-EVAL-01",
    "name": "Jane Doe",
    "account_type": "Personal Checking",
    "account_number": "ACC-55291048",
    "known_payees": ["Local Market", "Metro Fuel", "Corner Cafe"],
    "common_channels": ["POS", "Mobile"]
  },
  "historical_transactions": [
    {"transaction_id": "H01", "timestamp": "2026-08-01T10:00:00", "payee": "Local Market", "amount": 42.50, "channel": "POS"},
    {"transaction_id": "H02", "timestamp": "2026-08-02T11:30:00", "payee": "Metro Fuel", "amount": 55.00, "channel": "POS"},
    {"transaction_id": "H03", "timestamp": "2026-08-03T12:15:00", "payee": "Corner Cafe", "amount": 28.00, "channel": "Mobile"},
    {"transaction_id": "H04", "timestamp": "2026-08-04T09:45:00", "payee": "Local Market", "amount": 61.00, "channel": "POS"},
    {"transaction_id": "H05", "timestamp": "2026-08-05T13:00:00", "payee": "Corner Cafe", "amount": 35.00, "channel": "Mobile"}
  ],
  "observed_transactions": [
    {
      "transaction_id": "OBS-01",
      "timestamp": "2026-08-06T03:30:00",
      "payee": "Offshore Crypto Exchange",
      "amount": 9200.00,
      "channel": "Wire",
      "description": "Urgent Offshore Wire Transfer"
    }
  ]
}
```

#### Schema B: Flat Transaction Array (Auto-Partitioned)
Evaluators can also paste or upload a raw list of transactions `[ {...}, {...} ]`. If 6 or more transactions are provided, the engine automatically treats the earlier transactions as historical baseline and the final transactions as observed transactions:

```json
[
  {"transaction_id": "TXN-01", "timestamp": "2026-08-01T10:00:00", "payee": "Supermarket", "amount": 40.00, "channel": "POS"},
  {"transaction_id": "TXN-02", "timestamp": "2026-08-02T11:00:00", "payee": "Gas Station", "amount": 50.00, "channel": "POS"},
  {"transaction_id": "TXN-03", "timestamp": "2026-08-03T12:00:00", "payee": "Coffee Shop", "amount": 30.00, "channel": "Mobile"},
  {"transaction_id": "TXN-04", "timestamp": "2026-08-04T09:00:00", "payee": "Supermarket", "amount": 45.00, "channel": "POS"},
  {"transaction_id": "TXN-05", "timestamp": "2026-08-05T14:00:00", "payee": "Pharmacy", "amount": 35.00, "channel": "POS"},
  {"transaction_id": "TXN-06", "timestamp": "2026-08-06T03:15:00", "payee": "Unknown Wire Beneficiary", "amount": 8500.00, "channel": "Wire"}
]
```

---

### Step-by-Step: How to Test Your Own JSON

1. **Create your JSON payload** following either Schema A or Schema B above (or edit one of the pre-built files in `test_cases/`).
2. **Test via Web UI**:
   - Open `http://localhost:8000` → click **"🧪 Sandbox Analyzer"** → switch to **"📁 Custom JSON / File Upload"**.
   - Drag and drop your `.json` file into the dropzone (or paste your JSON).
   - Click **"Run Sandbox Investigation"**.
3. **Test via CLI**:
   ```bash
   python evaluate.py path/to/your_file.json
   ```
4. **Test via cURL**:
   ```bash
   curl -X POST http://localhost:8000/api/analyze/custom -H "Content-Type: application/json" -d @path/to/your_file.json
   ```

---

## 🧪 Test Scenarios & Verification Fixtures

You can verify any scenario using the REST API or Web UI at `http://localhost:8000`.

### 1. Test Case 1: Unusually Large Transfer Outlier (`CUST-104`)
```bash
curl http://localhost:8000/api/customers/CUST-104/analysis
```
- `verdict`: `"ATTENTION_REQUIRED"`
- `risk_score`: `80`
- `findings`: Contains `RULE_LARGE_TRANSFER` citing transaction `TXN-1318` ($14,500.00 wire transfer vs historical avg $115.00).

### 2. Test Case 2: New Payee Rapid Burst (`CUST-109`)
```bash
curl http://localhost:8000/api/customers/CUST-109/analysis
```
- `verdict`: `"ATTENTION_REQUIRED"`
- `risk_score`: `100`
- `findings`: Contains `RULE_NEW_PAYEE_BURST` citing `["TXN-1718", "TXN-1719", "TXN-1720"]` to new payee `NovaDex Crypto Settlement`.

### 3. Test Case 3: Odd-Hours Diurnal Deviation (`CUST-112`)
```bash
curl http://localhost:8000/api/customers/CUST-112/analysis
```
- `verdict`: `"ATTENTION_REQUIRED"`
- `risk_score`: `100`
- `findings`: Contains `RULE_ODD_HOURS` citing `["TXN-1941", "TXN-1942"]` occurring at 03:15 AM and 04:20 AM (baseline is 08:00–21:00).

### 4. Test Case 4: Clean Routine Customer (`CUST-101`)
```bash
curl http://localhost:8000/api/customers/CUST-101/analysis
```
- `verdict`: `"NOTHING_FLAGGED"`
- `risk_score`: `0`
- `evidence_status`: `"SUFFICIENT_HISTORY"`
- `findings_count`: `0`

### 5. Test Case 5: Sparse History Edge Case (`CUST-198`)
```bash
curl http://localhost:8000/api/customers/CUST-198/analysis
```
- `verdict`: `"INSUFFICIENT_EVIDENCE"`
- `risk_score`: `0`
- `evidence_status`: `"INSUFFICIENT_EVIDENCE"`
- `findings_count`: `0`

### 6. Test Case 6: Empty Transaction History Edge Case (`CUST-199`)
```bash
curl http://localhost:8000/api/customers/CUST-199/analysis
```
- `verdict`: `"INSUFFICIENT_EVIDENCE"`
- `risk_score`: `0`
- `evidence_status`: `"INSUFFICIENT_EVIDENCE"`
- `findings_count`: `0`

### 7. Test Case 7: Custom Payload Sandbox (`POST /api/analyze/custom`)
```bash
curl -X POST http://localhost:8000/api/analyze/custom \
  -H "Content-Type: application/json" \
  -d '{
    "historical_transactions": [
      {"transaction_id": "H1", "timestamp": "2026-08-01T12:00:00", "payee": "Routine Grocery", "amount": 45.0, "channel": "POS"},
      {"transaction_id": "H2", "timestamp": "2026-08-02T12:00:00", "payee": "Routine Grocery", "amount": 50.0, "channel": "POS"},
      {"transaction_id": "H3", "timestamp": "2026-08-03T12:00:00", "payee": "Routine Grocery", "amount": 42.0, "channel": "POS"},
      {"transaction_id": "H4", "timestamp": "2026-08-04T12:00:00", "payee": "Routine Grocery", "amount": 48.0, "channel": "POS"},
      {"transaction_id": "H5", "timestamp": "2026-08-05T12:00:00", "payee": "Routine Grocery", "amount": 46.0, "channel": "POS"}
    ],
    "observed_transactions": [
      {"transaction_id": "OBS-1", "timestamp": "2026-08-30T03:00:00", "amount": 9500.0, "payee": "Unseen Entity", "channel": "Wire"}
    ]
  }'
```
- `verdict`: `"ATTENTION_REQUIRED"`
- Baseline derived strictly from the 5 historical transactions ($46.20 avg).
- Cites `OBS-1` for large transfer outlier, odd hours, and uncharacteristic wire channel without baseline contamination.

---

## 🧪 Running Automated Tests

Run the full automated test suite (**51 unit & integration tests** covering deterministic rules, anti-contamination baselines, Gemini fact-checking firewalls, and HTTP 422 input validation):
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
