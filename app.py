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

    # Sort flagged accounts to the top, then insufficient evidence, then clean accounts
    result_list.sort(key=lambda x: (0 if x["verdict"] == "ATTENTION_REQUIRED" else (1 if x["verdict"] == "INSUFFICIENT_EVIDENCE" else 2), -x["risk_score"]))
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

    # 2. Grounded LLM Layer (Google Gemini / Resilient Fallback)
    report_md, model_name, fallback_used = llm_engine.generate_investigation_report(result)
    result.llm_report = report_md
    result.llm_model_used = model_name
    result.fallback_used = fallback_used

    return result


@app.get("/api/transactions/{transaction_id}/analysis", response_model=InvestigationResult)
async def analyze_single_transaction(transaction_id: str):
    """
    Evaluates a specific transaction against customer historical baseline,
    guaranteeing the evaluated transaction is STRICTLY excluded from baseline derivation.
    """
    try:
        result = rule_engine.evaluate_transaction(transaction_id)
        report_md, model_name, fallback_used = llm_engine.generate_investigation_report(result)
        result.llm_report = report_md
        result.llm_model_used = model_name
        result.fallback_used = fallback_used
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
    Strictly separates historical transactions from observed transactions to prevent baseline contamination.
    Strictly validates incoming transaction fields with structured HTTP 422 errors.
    """
    hist_txns = list(request.historical_transactions or [])
    obs_txns = list(request.observed_transactions or [])
    legacy_txns = list(request.transactions or [])

    # Auto-partition legacy or flat payloads: if only a flat list of txns is provided and >= 6,
    # separate the baseline (first N-1) from the evaluated transaction (last 1)
    if not hist_txns and not obs_txns and legacy_txns:
        if len(legacy_txns) >= 6:
            hist_txns = legacy_txns[:-1]
            obs_txns = [legacy_txns[-1]]
            eval_txns = obs_txns
        else:
            eval_txns = legacy_txns
    elif obs_txns:
        eval_txns = obs_txns
    elif legacy_txns:
        eval_txns = legacy_txns
    else:
        eval_txns = []

    # Determine customer ID & account name
    cust_profile = request.customer_profile
    cust_id = request.customer_id or "CUSTOM-001"
    cust_name = request.customer_name or "Custom Sandbox Account"
    if cust_profile:
        cust_id = cust_profile.customer_id or cust_id
        cust_name = cust_profile.name or cust_name
    elif eval_txns and eval_txns[0].customer_id:
        cust_id = eval_txns[0].customer_id
    elif hist_txns and hist_txns[0].customer_id:
        cust_id = hist_txns[0].customer_id

    # Baseline derivation & contamination prevention
    if hist_txns:
        # Strict separation: baseline derived ONLY from historical_transactions
        # Observed transactions NEVER contaminate baseline
        derived_profile = data_loader.derive_baseline(
            hist_txns,
            customer_id=cust_id,
            name=cust_name,
            exclude_transaction_ids=[t.transaction_id for t in eval_txns]
        )
        if cust_profile:
            derived_profile.account_type = cust_profile.account_type or derived_profile.account_type
            derived_profile.account_number = cust_profile.account_number or derived_profile.account_number
        cust_profile = derived_profile
        result = rule_engine.evaluate_customer(
            cust_id,
            transactions=eval_txns,
            profile=cust_profile,
            historical_transactions=hist_txns
        )
    else:
        # No explicit historical_transactions provided
        if not eval_txns:
            # Entirely empty payload
            empty_profile = cust_profile or data_loader.derive_baseline([], cust_id, cust_name)
            result = rule_engine.evaluate_customer(cust_id, transactions=[], profile=empty_profile)
        elif cust_profile is not None:
            # User provided a manual customer profile without historical transactions
            # Rule engine strictly enforces MIN_TRANSACTIONS_FOR_BASELINE:
            # If history < 5, verdict MUST be INSUFFICIENT_EVIDENCE
            result = rule_engine.evaluate_customer(cust_id, transactions=eval_txns, profile=cust_profile)
        else:
            # Legacy mode: single list of transactions provided
            derived_profile = data_loader.derive_baseline(eval_txns, cust_id, cust_name)
            result = rule_engine.evaluate_customer(cust_id, transactions=eval_txns, profile=derived_profile)

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
