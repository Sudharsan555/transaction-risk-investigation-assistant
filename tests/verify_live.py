"""
Live End-to-End Verification Script
"""

import httpx
import sys

def main():
    client = httpx.Client(base_url="http://localhost:8000", timeout=10.0)

    print("=== 1. Testing Static Assets & Index ===")
    r_index = client.get("/")
    assert r_index.status_code == 200, f"Failed index: {r_index.status_code}"
    print(f"[OK] GET / -> HTTP 200 (HTML size: {len(r_index.text)} bytes)")

    r_css = client.get("/static/css/style.css")
    assert r_css.status_code == 200, f"Failed CSS: {r_css.status_code}"
    print(f"[OK] GET /static/css/style.css -> HTTP 200 ({len(r_css.text)} bytes)")

    r_js = client.get("/static/js/app.js")
    assert r_js.status_code == 200, f"Failed JS: {r_js.status_code}"
    print(f"[OK] GET /static/js/app.js -> HTTP 200 ({len(r_js.text)} bytes)")

    print("\n=== 2. Testing API Health & Customers List ===")
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    health_data = r_health.json()
    print(f"[OK] GET /api/health -> HTTP 200 | Track ID: {health_data['track_id']} | Total Customers: {health_data['total_customers_loaded']}")

    r_custs = client.get("/api/customers")
    assert r_custs.status_code == 200
    custs = r_custs.json()["customers"]
    print(f"[OK] GET /api/customers -> HTTP 200 | Loaded {len(custs)} customers")

    print("\n=== 3. Testing Anomaly & Clean Customer Analysis ===")
    cases = [
        ("CUST-104", "Elena Rostova", "ATTENTION NEEDED"),
        ("CUST-109", "Marcus Vance", "ATTENTION NEEDED"),
        ("CUST-112", "Aisha Patel", "ATTENTION NEEDED"),
        ("CUST-115", "David Chen", "ATTENTION NEEDED"),
        ("CUST-118", "Sophia Morales", "ATTENTION NEEDED"),
        ("CUST-101", "Alexander Hayes", "NOTHING FLAGGED"),
        ("CUST-199", "Lucas Vance", "NOTHING FLAGGED"),
    ]

    for c_id, expected_name, expected_verdict in cases:
        res = client.get(f"/api/customers/{c_id}/analysis").json()
        verdict = res["verdict"]
        score = res["risk_score"]
        findings = res["findings_count"]
        report_line1 = res["llm_report"].strip().split("\n")[0]
        
        assert verdict == expected_verdict, f"Expected {expected_verdict} for {c_id}, got {verdict}"
        assert report_line1 == f"VERDICT: {expected_verdict}", f"Line 1 mismatch: {report_line1}"
        assert "DISCLAIMER:" in res["llm_report"], "Disclaimer missing in report"

        print(f"[OK] {c_id:8s} | {expected_name:18s} | Verdict: {verdict:16s} | Score: {score:3d} | Findings: {findings} | Line 1: {report_line1}")

    print("\n=== 4. Testing Interactive Sandbox POST Endpoint ===")
    sample_payload = {
        "customer_profile": {
            "customer_id": "TEST-CUST-99",
            "name": "Sandbox Test Customer",
            "account_type": "Checking",
            "account_number": "ACC-99887766",
            "baseline_avg_amount": 50.0,
            "baseline_std_amount": 20.0,
            "baseline_max_normal": 150.0,
            "baseline_active_hours": [8, 20],
            "known_payees": ["Grocery Mart"],
            "common_channels": ["POS"]
        },
        "transactions": [
            {
                "transaction_id": "SB-TXN-01",
                "timestamp": "2026-08-30T12:00:00",
                "description": "Routine Lunch",
                "payee": "Grocery Mart",
                "amount": 25.0,
                "channel": "POS"
            },
            {
                "transaction_id": "SB-TXN-02",
                "timestamp": "2026-08-30T02:30:00",
                "description": "Urgent Crypto Outbound Wire",
                "payee": "Anonymous Crypto Exchange",
                "amount": 9500.0,
                "channel": "Wire"
            }
        ]
    }
    r_sb = client.post("/api/analyze/custom", json=sample_payload)
    assert r_sb.status_code == 200, f"Sandbox failed: {r_sb.status_code}"
    sb_data = r_sb.json()
    print(f"[OK] POST /api/analyze/custom -> HTTP 200 | Verdict: {sb_data['verdict']} | Score: {sb_data['risk_score']} | Findings: {sb_data['findings_count']}")

    print("\n[SUCCESS] ALL END-TO-END VERIFICATION CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    main()
