import unittest
from fastapi.testclient import TestClient
from app import app


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["track_id"], "PS06")
        self.assertIn("total_customers_loaded", data)

    def test_get_customers_list(self):
        response = self.client.get("/api/customers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("customers", data)
        self.assertGreaterEqual(len(data["customers"]), 18)
        
        # Verify flagged accounts are at the top
        verdicts = [c["verdict"] for c in data["customers"]]
        attention_indices = [i for i, v in enumerate(verdicts) if v == "ATTENTION_REQUIRED"]
        clean_indices = [i for i, v in enumerate(verdicts) if v == "NOTHING_FLAGGED"]
        if attention_indices and clean_indices:
            self.assertLess(min(attention_indices), max(clean_indices))

    def test_analyze_customer_endpoint(self):
        response = self.client.get("/api/customers/CUST-104/analysis")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["customer_id"], "CUST-104")
        self.assertEqual(data["verdict"], "ATTENTION_REQUIRED")
        self.assertIn("llm_report", data)
        self.assertTrue(data["llm_report"].startswith("VERDICT: ATTENTION_REQUIRED"))
        self.assertIn("risk_score_breakdown", data)
        self.assertIn("citation_validation", data)

    def test_analyze_sparse_customer_endpoint(self):
        response = self.client.get("/api/customers/CUST-198/analysis")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["customer_id"], "CUST-198")
        self.assertEqual(data["verdict"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(data["evidence_status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(data["risk_score"], 0)
        self.assertTrue(data["llm_report"].startswith("VERDICT: INSUFFICIENT_EVIDENCE"))

    def test_analyze_single_transaction_endpoint(self):
        response = self.client.get("/api/transactions/TXN-1318/analysis")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["verdict"], "ATTENTION_REQUIRED")
        self.assertIn("llm_report", data)
        self.assertTrue(data["llm_report"].startswith("VERDICT: ATTENTION_REQUIRED"))

    def test_customer_transactions_endpoint(self):
        response = self.client.get("/api/customers/CUST-104/transactions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("transactions", data)
        self.assertGreater(data["flagged_count"], 0)
        flagged_items = [t for t in data["transactions"] if t["is_flagged"]]
        self.assertGreater(len(flagged_items), 0)

    def test_custom_sandbox_analysis_valid(self):
        payload = {
            "customer_profile": {
                "customer_id": "TEST-CUST",
                "name": "Test User",
                "account_type": "Checking",
                "account_number": "ACC-12345678",
                "baseline_avg_amount": 50.0,
                "baseline_std_amount": 20.0,
                "baseline_max_normal": 150.0,
                "baseline_active_hours": [8, 20],
                "known_payees": ["Grocery Store"],
                "common_channels": ["POS"]
            },
            "transactions": [
                {
                    "transaction_id": "TEST-TXN-1",
                    "timestamp": "2026-08-30T14:00:00",
                    "description": "Routine purchase",
                    "payee": "Grocery Store",
                    "amount": 45.0,
                    "channel": "POS"
                },
                {
                    "transaction_id": "TEST-TXN-2",
                    "timestamp": "2026-08-30T03:00:00",
                    "description": "Sudden Outbound Wire",
                    "payee": "New International Exchange",
                    "amount": 8500.0,
                    "channel": "Wire"
                }
            ]
        }
        response = self.client.post("/api/analyze/custom", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["verdict"], "ATTENTION_REQUIRED")
        self.assertIn("llm_report", data)
        self.assertTrue(data["llm_report"].startswith("VERDICT: ATTENTION_REQUIRED"))

    def test_custom_sandbox_rejects_negative_amount_422(self):
        """Input validation: non-positive amounts must be rejected with HTTP 422 Unprocessable Entity."""
        invalid_payload = {
            "transactions": [
                {
                    "transaction_id": "TXN-BAD-1",
                    "timestamp": "2026-08-30T14:00:00",
                    "payee": "Merchant",
                    "amount": -50.0
                }
            ]
        }
        response = self.client.post("/api/analyze/custom", json=invalid_payload)
        self.assertEqual(response.status_code, 422)

    def test_custom_sandbox_rejects_malformed_timestamp_422(self):
        """Input validation: invalid timestamps must be rejected with HTTP 422 Unprocessable Entity."""
        invalid_payload = {
            "transactions": [
                {
                    "transaction_id": "TXN-BAD-2",
                    "timestamp": "NOT-A-TIMESTAMP",
                    "payee": "Merchant",
                    "amount": 100.0
                }
            ]
        }
        response = self.client.post("/api/analyze/custom", json=invalid_payload)
        self.assertEqual(response.status_code, 422)

    def test_custom_sandbox_rejects_empty_payee_422(self):
        """Input validation: empty payee field must be rejected with HTTP 422 Unprocessable Entity."""
        invalid_payload = {
            "transactions": [
                {
                    "transaction_id": "TXN-BAD-3",
                    "timestamp": "2026-08-30T14:00:00",
                    "payee": "   ",
                    "amount": 100.0
                }
            ]
        }
        response = self.client.post("/api/analyze/custom", json=invalid_payload)
        self.assertEqual(response.status_code, 422)

    def test_serve_html_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Transaction Risk Investigation Assistant", response.text)


if __name__ == "__main__":
    unittest.main()

