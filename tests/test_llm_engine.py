import unittest
from src.data_loader import DataLoader
from src.rule_engine import RiskRuleEngine
from src.llm_engine import LLMInvestigationEngine, DISCLAIMER_TEXT


class TestLLMInvestigationEngine(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()
        self.rule_engine = RiskRuleEngine(loader=self.loader)
        self.llm = LLMInvestigationEngine()

    def test_clean_customer_report_format(self):
        result = self.rule_engine.evaluate_customer("CUST-101")
        report, model_used, fallback_used = self.llm.generate_investigation_report(result)
        
        # Verify first line
        first_line = report.strip().split("\n")[0]
        self.assertIn(first_line, ["VERDICT: NOTHING_FLAGGED", "VERDICT: NOTHING FLAGGED"])
        
        # Verify disclaimer
        self.assertIn("DISCLAIMER:", report)
        
        # Verify non-alarming language
        self.assertIn("Executive Summary", report)
        self.assertIn("Investigator Action Checklist", report)

    def test_flagged_customer_report_citations(self):
        result = self.rule_engine.evaluate_customer("CUST-104")
        report, model_used, fallback_used = self.llm.generate_investigation_report(result)
        
        # Verify first line
        first_line = report.strip().split("\n")[0]
        self.assertIn(first_line, ["VERDICT: ATTENTION_REQUIRED", "VERDICT: ATTENTION NEEDED"])
        
        # Verify all cited transaction IDs are present in the report
        for f in result.findings:
            for txn_id in f.transaction_ids:
                self.assertIn(txn_id, report)
                
        # Verify disclaimer
        self.assertIn("DISCLAIMER:", report)

    def test_empty_customer_report(self):
        result = self.rule_engine.evaluate_customer("CUST-199")
        report, model_used, fallback_used = self.llm.generate_investigation_report(result)
        
        first_line = report.strip().split("\n")[0]
        self.assertIn(first_line, ["VERDICT: INSUFFICIENT_EVIDENCE", "VERDICT: NOTHING FLAGGED"])
        self.assertIn("DISCLAIMER:", report)

    def test_citation_validator_sanitizes_hallucinated_ids(self):
        """Zero hallucinated citations in final output: strips invalid IDs."""
        valid_ids = {"TXN-1015", "TXN-1020"}
        mock_text = (
            "Investigation verified anomaly in [TXN-1015]. "
            "However, an unverified transfer was mentioned in [TXN-9999] and [CUSTOM-8888]."
        )
        sanitized, meta = self.llm.validate_and_sanitize_citations(mock_text, valid_ids)

        self.assertIn("[TXN-1015]", sanitized)
        self.assertNotIn("[TXN-9999]", sanitized)
        self.assertNotIn("[CUSTOM-8888]", sanitized)
        self.assertIn("[UNVERIFIED CITATION REMOVED]", sanitized)
        self.assertTrue(meta["sanitized"])
        self.assertEqual(meta["status"], "SANITIZED")
        self.assertIn("TXN-9999", meta["hallucinated_citations"])
        self.assertIn("CUSTOM-8888", meta["hallucinated_citations"])
        self.assertIn("TXN-1015", meta["valid_citations"])


if __name__ == "__main__":
    unittest.main()
