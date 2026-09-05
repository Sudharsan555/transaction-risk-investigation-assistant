import unittest
from src.data_loader import DataLoader
from src.rule_engine import RiskRuleEngine


class TestRiskRuleEngine(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()
        self.engine = RiskRuleEngine(loader=self.loader)

    def test_clean_customer_evaluation(self):
        """Clean customer should return NOTHING FLAGGED with SUFFICIENT_HISTORY status."""
        res = self.engine.evaluate_customer("CUST-101")
        self.assertEqual(res.verdict, "NOTHING FLAGGED")
        self.assertEqual(res.evidence_status, "SUFFICIENT_HISTORY")
        self.assertEqual(res.risk_score, 0)
        self.assertEqual(res.findings_count, 0)
        self.assertEqual(len(res.findings), 0)
        self.assertEqual(len(res.cited_transactions), 0)

    def test_empty_history_customer(self):
        """Empty history customer should return NOTHING FLAGGED with INSUFFICIENT_EVIDENCE status."""
        res = self.engine.evaluate_customer("CUST-199")
        self.assertEqual(res.verdict, "NOTHING FLAGGED")
        self.assertEqual(res.evidence_status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(res.risk_score, 0)
        self.assertEqual(res.findings_count, 0)
        self.assertEqual(len(res.cited_transactions), 0)

    def test_large_transfer_outlier_rule(self):
        """CUST-104 should trigger RULE_LARGE_TRANSFER for the $14,500 wire."""
        res = self.engine.evaluate_customer("CUST-104")
        self.assertEqual(res.verdict, "ATTENTION NEEDED")
        self.assertGreater(res.risk_score, 0)
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_LARGE_TRANSFER", rule_ids)
        self.assertGreater(len(res.cited_transactions), 0)
        # Verify cited transaction is high value
        flagged_amts = [t.amount for t in res.cited_transactions]
        self.assertIn(14500.0, flagged_amts)

    def test_new_payee_burst_rule(self):
        """CUST-109 should trigger RULE_NEW_PAYEE_BURST for rapid crypto transfers."""
        res = self.engine.evaluate_customer("CUST-109")
        self.assertEqual(res.verdict, "ATTENTION NEEDED")
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_NEW_PAYEE_BURST", rule_ids)
        # Verify cited transactions match the new payee
        burst_payees = [t.payee for t in res.cited_transactions]
        self.assertIn("NovaDex Crypto Settlement", burst_payees)

    def test_odd_hours_rule(self):
        """CUST-112 should trigger RULE_ODD_HOURS for 3 AM and 4 AM transactions."""
        res = self.engine.evaluate_customer("CUST-112")
        self.assertEqual(res.verdict, "ATTENTION NEEDED")
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_ODD_HOURS", rule_ids)
        self.assertGreaterEqual(len(res.cited_transactions), 2)

    def test_pattern_break_rule(self):
        """CUST-115 should trigger RULE_PATTERN_BREAK for unprecedented international wires."""
        res = self.engine.evaluate_customer("CUST-115")
        self.assertEqual(res.verdict, "ATTENTION NEEDED")
        rule_ids = [f.rule_id for f in res.findings]
        self.assertIn("RULE_PATTERN_BREAK", rule_ids)

    def test_multi_vector_anomaly(self):
        """CUST-118 should trigger multiple rules simultaneously."""
        res = self.engine.evaluate_customer("CUST-118")
        self.assertEqual(res.verdict, "ATTENTION NEEDED")
        self.assertGreaterEqual(len(res.findings), 2)
        self.assertGreaterEqual(res.risk_score, 50)

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
