import unittest
from src.data_loader import DataLoader
from src.rule_engine import RiskRuleEngine, MIN_TRANSACTIONS_FOR_BASELINE
from src.models import Transaction, CustomerProfile


class TestRiskRuleEngine(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()
        self.engine = RiskRuleEngine(loader=self.loader)

    def test_clean_customer_evaluation(self):
        """Clean customer should strictly return NOTHING_FLAGGED with SUFFICIENT_HISTORY status."""
        res = self.engine.evaluate_customer("CUST-101")
        self.assertEqual(res.verdict, "NOTHING_FLAGGED")
        self.assertEqual(res.evidence_status, "SUFFICIENT_HISTORY")
        self.assertEqual(res.risk_score, 0)
        self.assertEqual(res.findings_count, 0)
        self.assertEqual(len(res.findings), 0)
        self.assertEqual(len(res.cited_transactions), 0)
        self.assertIn("disclaimer", res.risk_score_breakdown)

    def test_empty_history_customer(self):
        """Empty history customer should strictly return INSUFFICIENT_EVIDENCE."""
        res = self.engine.evaluate_customer("CUST-199")
        self.assertEqual(res.verdict, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res.evidence_status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res.risk_score, 0)
        self.assertEqual(res.findings_count, 0)
        self.assertEqual(len(res.cited_transactions), 0)
        self.assertIn("note", res.customer_baseline)
        self.assertEqual(res.customer_baseline.get("historical_sample_size"), 0)

    def test_insufficient_history_sparse_account(self):
        """Account with fewer than MIN_TRANSACTIONS_FOR_BASELINE (< 5) returns INSUFFICIENT_EVIDENCE."""
        sparse_txns = [
            Transaction(
                transaction_id=f"SPARSE-{i}",
                customer_id="CUST-SPARSE",
                timestamp="2026-08-01T12:00:00",
                description="Small purchase",
                payee="Corner Store",
                amount=25.0 + i,
                channel="POS"
            )
            for i in range(3)  # 3 transactions < 5 threshold
        ]
        res = self.engine.evaluate_customer("CUST-SPARSE", transactions=sparse_txns)
        self.assertEqual(res.verdict, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res.evidence_status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res.risk_score, 0)
        self.assertEqual(res.findings_count, 0)
        self.assertEqual(res.risk_score_breakdown.get("evidence_status"), "INSUFFICIENT_EVIDENCE")

    def test_sparse_customer_cust_198(self):
        """Preloaded CUST-198 has 2 transactions (< 5 minimum reliable history) -> INSUFFICIENT_EVIDENCE."""
        res = self.engine.evaluate_customer("CUST-198")
        self.assertEqual(res.verdict, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res.evidence_status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res.risk_score, 0)

    def test_exactly_five_transactions_threshold(self):
        """Account with exactly 5 transactions meets the MIN_TRANSACTIONS_FOR_BASELINE threshold."""
        txns = [
            Transaction(
                transaction_id=f"EXACT5-{i}",
                customer_id="CUST-EXACT5",
                timestamp=f"2026-08-0{i+1}T12:00:00",
                description=f"Standard purchase {i+1}",
                payee="Main Street Market",
                amount=50.0 + (i * 2),
                channel="POS"
            )
            for i in range(5)  # exactly 5 transactions
        ]
        res = self.engine.evaluate_customer("CUST-EXACT5", transactions=txns)
        self.assertEqual(res.verdict, "NOTHING_FLAGGED")
        self.assertEqual(res.evidence_status, "SUFFICIENT_HISTORY")
        self.assertEqual(res.risk_score, 0)

    def test_large_transfer_outlier_rule(self):
        """CUST-104 should trigger RULE_LARGE_TRANSFER for the $14,500 wire."""
        res = self.engine.evaluate_customer("CUST-104")
        self.assertEqual(res.verdict, "ATTENTION_REQUIRED")
        self.assertGreater(res.risk_score, 0)
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_LARGE_TRANSFER", rule_ids)
        self.assertGreater(len(res.cited_transactions), 0)
        flagged_amts = [t.amount for t in res.cited_transactions]
        self.assertIn(14500.0, flagged_amts)

    def test_new_payee_burst_rule(self):
        """CUST-109 should trigger RULE_NEW_PAYEE_BURST for rapid crypto transfers."""
        res = self.engine.evaluate_customer("CUST-109")
        self.assertEqual(res.verdict, "ATTENTION_REQUIRED")
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_NEW_PAYEE_BURST", rule_ids)
        burst_payees = [t.payee for t in res.cited_transactions]
        self.assertIn("NovaDex Crypto Settlement", burst_payees)

    def test_odd_hours_rule(self):
        """CUST-112 should trigger RULE_ODD_HOURS for 3 AM and 4 AM transactions."""
        res = self.engine.evaluate_customer("CUST-112")
        self.assertEqual(res.verdict, "ATTENTION_REQUIRED")
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_ODD_HOURS", rule_ids)
        self.assertGreaterEqual(len(res.cited_transactions), 2)

    def test_pattern_break_rule(self):
        """CUST-115 should trigger RULE_PATTERN_BREAK for unprecedented international wires."""
        res = self.engine.evaluate_customer("CUST-115")
        self.assertEqual(res.verdict, "ATTENTION_REQUIRED")
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_PATTERN_BREAK", rule_ids)

    def test_multi_vector_anomaly(self):
        """CUST-118 should trigger multiple rules simultaneously."""
        res = self.engine.evaluate_customer("CUST-118")
        self.assertEqual(res.verdict, "ATTENTION_REQUIRED")
        self.assertGreaterEqual(len(res.findings), 2)
        self.assertGreaterEqual(res.risk_score, 50)

    def test_finding_schema_completeness(self):
        """Each finding must have all 8 required PS06 fields."""
        res = self.engine.evaluate_customer("CUST-104")
        self.assertGreater(len(res.findings), 0)
        for f in res.findings:
            self.assertTrue(f.rule_id)
            self.assertIn(f.severity, ["HIGH", "MEDIUM", "LOW"])
            self.assertGreater(len(f.transaction_ids), 0)
            self.assertTrue(f.observed_value)
            self.assertTrue(f.baseline_value)
            self.assertTrue(f.deviation)
            self.assertTrue(f.explanation)
            self.assertTrue(f.investigator_action)

    def test_risk_score_breakdown_transparency(self):
        """Risk score breakdown must be explainable with disclaimer and rule points."""
        res = self.engine.evaluate_customer("CUST-104")
        breakdown = res.risk_score_breakdown
        self.assertIn("rule_contributions", breakdown)
        self.assertIn("capped_score", breakdown)
        self.assertIn("disclaimer", breakdown)
        self.assertIn("investigative urgency", breakdown["disclaimer"].lower())

    def test_evaluate_transaction_baseline_separation(self):
        """Evaluating single transaction must strictly exclude that transaction from baseline."""
        target_tid = "TXN-1318"
        res = self.engine.evaluate_transaction(target_tid)
        self.assertEqual(res.verdict, "ATTENTION_REQUIRED")
        self.assertIn("baseline_avg_amount", res.customer_baseline)
        self.assertEqual(res.customer_baseline.get("provenance"), "HISTORICAL_TRANSACTIONS_ONLY")

    def test_all_cited_transactions_are_traceable(self):
        """Every transaction ID cited in findings must exist in source transactions."""
        all_customers = self.loader.get_all_customers()
        for cust in all_customers:
            res = self.engine.evaluate_customer(cust.customer_id)
            source_txns = self.loader.get_customer_transactions(cust.customer_id)
            source_ids = set(t.transaction_id for t in source_txns)
            
            for f in res.findings:
                for cited_id in f.cited_transaction_ids:
                    self.assertIn(
                        cited_id,
                        source_ids,
                        f"Cited ID {cited_id} not found in customer {cust.customer_id} source data!"
                    )


if __name__ == "__main__":
    unittest.main()

