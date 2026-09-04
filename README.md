TRACK_ID=PS6

# Transaction Risk Investigation Assistant (PS06)

An intelligent, bank-grade fraud desk investigation assistant built for **NexusTiQ 24 (Track PS06: Banking - Transaction Risk Investigation Assistant)**.

The system combines a **100% deterministic statistical risk rule engine** (zero LLM dependency) with a **strictly grounded GenAI investigation layer (Gemini 2.0 Flash)** to detect, analyze, and explain anomalous customer transaction activity without ever hallucinating findings or definitively asserting fraud.

---

## 🎯 What the Project Does

1. **Deterministic Rule Engine**: Evaluates full customer transaction histories against individual historical baselines across 4 core risk categories:
   - **Unusually Large Transfers**: Statistical z-score outlier detection vs. customer's historical average and std deviation.
   - **Burst of Transfers to New Payee**: Rapid consecutive payments to previously unseen counterparties within short time windows.
   - **Odd-Hours Activity**: Transactions executed outside the customer's established active hours baseline.
   - **Break from Established Pattern**: Sudden high-risk channel switches (e.g., sudden wire/crypto) or drastic frequency shifts.
2. **Strictly Grounded LLM Layer (Gemini 2.0 Flash)**: Generates human-readable investigation notes:
   - Starts with strict verdict: `VERDICT: ATTENTION NEEDED` or `VERDICT: NOTHING FLAGGED`.
   - Cites exact `transaction_id`s for every factual claim.
   - Never hallucinates ungrounded data.
   - Never declares fraud (flags, explains, and provides actionable investigator checklists).
   - Features **instant graceful deterministic fallback** if Gemini API key is missing or network times out.
3. **Modern FinTech Dashboard**:
   - High-aesthetic glassmorphic UI with dark/light themes.
   - Live customer search, filterable risk queues (Flagged vs. Clean).
   - Visual transaction ledger with glowing inline citations and interactive rule tooltips.
   - Interactive Sandbox Analyzer to test custom JSON/CSV transaction payloads.

---

## 🚀 Quickstart & How to Run

### Prerequisites
- Python 3.11+
- (Optional) `GEMINI_API_KEY` for AI grounded narrative (system includes automatic deterministic fallback).

### Single Command Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set your Gemini API Key
# Windows PowerShell:
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# Linux / macOS:
export GEMINI_API_KEY="your-gemini-api-key-here"

# 3. Start the application
python app.py
```

The application will start immediately and be available at:
👉 **`http://localhost:8000`**

---

## 📊 Synthetic Data Generated

Located under `data/`:
- **`customers.json`**: 18 realistic bank customer profiles with baseline spend statistics, standard active hours, and known counterparty graphs.
- **`transactions.csv`**: 1,500+ realistic transaction records spanning 6 months across POS, Mobile, Web, ATM, and Wire channels.
- **Seeded Anomaly Profiles**:
  - `CUST-104` (Elena Rostova): Unusually large international wire transfer ($14,500 vs $120 avg).
  - `CUST-109` (Marcus Vance): Burst of 3 rapid transfers in 6 hours to newly added crypto payee.
  - `CUST-112` (Aisha Patel): Multiple consecutive transactions at 03:15 AM and 04:20 AM (normal active window: 08:00–21:00).
  - `CUST-115` (David Chen): Rapid channel break with international wire transactions.
  - `CUST-118` (Sophia Morales): Multi-vector anomaly (outlier + new payee + odd hours).
  - `CUST-101`, `CUST-102`, `CUST-103`, etc.: Completely clean transaction histories with zero false positives.
  - `CUST-199` (New Account): Empty / zero-history edge case handled gracefully.

---

## 🧪 Running Automated Tests

Run the test suite covering rule engine accuracy, data validation, and API contracts:

```bash
pytest tests/ -v
# or
python -m unittest discover tests/
```

---

## 🎥 Demo Video

- **Demo Video Link**: `https://youtu.be/demo-link-placeholder-ps06` *(2-minute demonstration showing normal vs anomalous customer investigation)*

---

## 🛡️ Edge Cases Handled

- **Empty / Near-Empty History**: Returns confident, non-alarming `NOTHING FLAGGED` status.
- **Zero Anomalies**: Clean, reassuring report affirming baseline compliance.
- **Malformed Data / Missing Fields**: Gracefully handles missing amounts, timestamps, or invalid strings without throwing exceptions.
- **API Failure / Timeout**: Automatic deterministic fallback ensures report is generated within milliseconds.
- **Large Flagged Volume**: Grouped summarization prevents report cognitive overload.
