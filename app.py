import json
from pathlib import Path
from typing import List, Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.config import HOST, PORT, STATIC_DIR, DATA_DIR, TRACK_ID, GEMINI_MODEL
from src.models import (
    Transaction,
    CustomerProfile,
    InvestigationResult,
    CustomAnalysisRequest
)
from src.data_loader import data_loader
from src.rule_engine import rule_engine
from src.llm_engine import llm_engine

app = FastAPI(
    title="Transaction Risk Investigation Assistant",
    description="Bank Fraud Desk Risk Engine & AI Grounded Investigation Assistant (NexusTiQ 24 TRACK_ID=PS06)",
    version="1.0.0"
)

# CORS middleware for seamless local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/api/health")
async def health_check():
    """Health check and environment readiness."""
    has_api_key = bool(llm_engine.api_key)
    return {
        "status": "healthy",
        "track_id": TRACK_ID,
        "app": "Transaction Risk Investigation Assistant",
        "gemini_api_configured": has_api_key,
        "active_model": GEMINI_MODEL if has_api_key else "Deterministic Fallback Engine",
        "total_customers_loaded": len(data_loader.get_all_customers())
    }


@app.get("/api/customers")
async def get_customers():
    """
    Returns list of all customers with pre-evaluated risk badges and metadata.
    """
    customers = data_loader.get_all_customers()
    result_list = []
    
    for c in customers:
        txns = data_loader.get_customer_transactions(c.customer_id)
        # Quick deterministic evaluation for dashboard overview
        res = rule_engine.evaluate_customer(c.customer_id, transactions=txns, profile=c)
        result_list.append({
            "customer_id": c.customer_id,
            "name": c.name,
            "account_type": c.account_type,
            "account_number": c.account_number,
            "baseline_avg_amount": c.baseline_avg_amount,
            "baseline_max_normal": c.baseline_max_normal,
            "baseline_active_hours": c.baseline_active_hours,
            "total_transactions": len(txns),
            "total_volume": c.total_volume,
            "verdict": res.verdict,
            "risk_score": res.risk_score,
            "findings_count": res.findings_count
        })

    # Sort flagged accounts to the top
    result_list.sort(key=lambda x: (0 if x["verdict"] == "ATTENTION NEEDED" else 1, -x["risk_score"]))
    return {"customers": result_list}


@app.get("/api/customers/{customer_id}/analysis", response_model=InvestigationResult)
async def analyze_customer(customer_id: str):
    """
    Runs deterministic rule engine + LLM report generation for the given customer.
    """
    customer = data_loader.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")

    txns = data_loader.get_customer_transactions(customer_id)
    
    # 1. Deterministic Rule Evaluation (Strictly no LLM)
    result = rule_engine.evaluate_customer(customer_id, transactions=txns, profile=customer)

    # 2. Grounded LLM Layer (Gemini 2.0 Flash / Resilient Fallback)
    report_md, model_name, fallback_used = llm_engine.generate_investigation_report(result)
    result.llm_report = report_md
    result.llm_model_used = model_name
    result.fallback_used = fallback_used

    return result


@app.get("/api/customers/{customer_id}/transactions")
async def get_customer_transactions(customer_id: str):
    """
    Returns full transaction ledger for customer with inline risk annotations.
    """
    customer = data_loader.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")

    txns = data_loader.get_customer_transactions(customer_id)
    res = rule_engine.evaluate_customer(customer_id, transactions=txns, profile=customer)
    
    flagged_ids = {t.transaction_id: t.flag_reasons for t in res.cited_transactions}
    
    annotated = []
    for t in txns:
        t_dict = t.model_dump()
        if t.transaction_id in flagged_ids:
            t_dict["is_flagged"] = True
            t_dict["flag_reasons"] = flagged_ids[t.transaction_id]
        else:
            t_dict["is_flagged"] = False
            t_dict["flag_reasons"] = []
        annotated.append(t_dict)

    return {
        "customer_id": customer_id,
        "total": len(annotated),
        "flagged_count": len(flagged_ids),
        "transactions": annotated
    }


@app.post("/api/analyze/custom", response_model=InvestigationResult)
async def analyze_custom_payload(request: CustomAnalysisRequest):
    """
    Sandbox endpoint: Evaluates an arbitrary payload of transactions against
    a custom or dynamically derived customer baseline.
    """
    raw_txns = request.transactions
    if not raw_txns:
        # Empty payload
        empty_profile = request.customer_profile or data_loader.derive_baseline([], "CUSTOM-001", "Custom Account")
        res = rule_engine.evaluate_customer("CUSTOM-001", transactions=[], profile=empty_profile)
        report_md, model_name, fallback_used = llm_engine.generate_investigation_report(res)
        res.llm_report = report_md
        res.llm_model_used = model_name
        res.fallback_used = fallback_used
        return res

    # Parse transactions safely
    parsed_txns: List[Transaction] = []
    for idx, row in enumerate(raw_txns, 1001):
        txn_id = str(row.get("transaction_id", f"CUSTOM-TXN-{idx}")).strip()
        parsed = data_loader._parse_transaction_row({
            "transaction_id": txn_id,
            "customer_id": str(row.get("customer_id", "CUSTOM-001")),
            "timestamp": str(row.get("timestamp", "2026-08-30T12:00:00")),
            "description": str(row.get("description", "Custom Transaction")),
            "payee": str(row.get("payee", "Unknown Payee")),
            "amount": row.get("amount", 0.0),
            "channel": str(row.get("channel", "Web")),
            "category": str(row.get("category", "General"))
        })
        if parsed:
            parsed_txns.append(parsed)

    # Derive baseline profile if not explicitly provided
    cust_profile = request.customer_profile
    if cust_profile is None:
        cust_profile = data_loader.derive_baseline(parsed_txns, "CUSTOM-001", "Custom Sandbox Account")

    # Evaluate
    result = rule_engine.evaluate_customer("CUSTOM-001", transactions=parsed_txns, profile=cust_profile)
    report_md, model_name, fallback_used = llm_engine.generate_investigation_report(result)
    result.llm_report = report_md
    result.llm_model_used = model_name
    result.fallback_used = fallback_used

    return result


@app.get("/api/test-fixtures")
async def get_test_fixtures():
    """
    Returns curated sample test fixtures from data/sample_test_inputs.json.
    """
    fixtures_file = DATA_DIR / "sample_test_inputs.json"
    if fixtures_file.exists():
        with open(fixtures_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"test_cases": []}


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main single-page application."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Transaction Risk Investigation Assistant</h1><p>NexusTiQ 24 TRACK_ID=PS06</p>")


if __name__ == "__main__":
    print(f"[START] Starting Transaction Risk Investigation Assistant (TRACK_ID={TRACK_ID})")
    print(f"[INFO] Access the application at: http://localhost:{PORT}")
    uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
