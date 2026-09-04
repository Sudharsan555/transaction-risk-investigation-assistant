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
        self.assertEqual(first_line, "VERDICT: NOTHING FLAGGED")
        
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
        self.assertEqual(first_line, "VERDICT: ATTENTION NEEDED")
        
        # Verify all cited transaction IDs are present in the report
        for f in result.findings:
            for txn_id in f.cited_transaction_ids:
                self.assertIn(txn_id, report)
                
        # Verify disclaimer
        self.assertIn("DISCLAIMER:", report)

    def test_empty_customer_report(self):
        result = self.rule_engine.evaluate_customer("CUST-199")
        report, model_used, fallback_used = self.llm.generate_investigation_report(result)
        
        first_line = report.strip().split("\n")[0]
        self.assertEqual(first_line, "VERDICT: NOTHING FLAGGED")
        self.assertIn("DISCLAIMER:", report)


if __name__ == "__main__":
    unittest.main()
