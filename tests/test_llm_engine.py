import unittest
from src.data_loader import DataLoader
from src.rule_engine import RiskRuleEngine
from src.llm_engine import LLMInvestigationEngine, DISCLAIMER_TEXT
from src.models import Transaction, InvestigationResult, CustomerProfile


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
        self.assertEqual(first_line, "VERDICT: NOTHING_FLAGGED")
        
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
        self.assertEqual(first_line, "VERDICT: ATTENTION_REQUIRED")
        
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
        self.assertEqual(first_line, "VERDICT: INSUFFICIENT_EVIDENCE")
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

    def test_validate_citations_and_facts_detects_hallucinated_amount(self):
        """Fact validation catches invented transaction amounts and safely triggers deterministic fallback."""
        txn = Transaction(
            transaction_id="TXN-1015",
            customer_id="CUST-101",
            timestamp="2026-08-01T12:00:00",
            description="Lunch",
            payee="Cafe",
            amount=45.00,
            channel="POS"
        )
        valid_map = {"TXN-1015": txn}
        res = self.rule_engine.evaluate_customer("CUST-101")
        
        # Simulated LLM hallucinating a $95,000.00 transfer on a $45.00 transaction
        hallucinated_text = "Analysis shows [TXN-1015] was a massive wire transfer of $95,000.00 to an offshore account."
        final_report, meta, fallback_applied = self.llm.validate_citations_and_facts(hallucinated_text, valid_map, res)
        
        self.assertTrue(fallback_applied)
        self.assertTrue(meta["fallback_applied"])
        self.assertGreater(len(meta["factual_contradictions"]), 0)
        self.assertEqual(meta["status"], "FALLBACK_TRIGGERED_HALLUCINATION_DETECTED")
        # Final report must have fallen back to safe deterministic report
        self.assertTrue(final_report.startswith("VERDICT: NOTHING_FLAGGED"))

    def test_gemini_fallback_on_unavailable_client(self):
        """When Gemini client is not initialized, generate_investigation_report safely falls back."""
        # Create an engine with client forced to None
        fallback_engine = LLMInvestigationEngine()
        fallback_engine.client = None
        
        res = self.rule_engine.evaluate_customer("CUST-104")
        report, model_name, fallback_used = fallback_engine.generate_investigation_report(res)
        
        self.assertTrue(fallback_used)
        self.assertIn("Deterministic Fallback", model_name)
        self.assertTrue(report.startswith("VERDICT: ATTENTION_REQUIRED"))
    def test_validate_citations_and_facts_detects_hallucinated_channel(self):
        """Fact validation catches invented channel claims and safely triggers deterministic fallback."""
        txn = Transaction(
            transaction_id="TXN-1015",
            customer_id="CUST-101",
            timestamp="2026-08-01T12:00:00",
            description="POS purchase",
            payee="Cafe",
            amount=45.00,
            channel="POS"
        )
        valid_map = {"TXN-1015": txn}
        res = self.rule_engine.evaluate_customer("CUST-101")
        
        hallucinated_text = "Analysis shows [TXN-1015] was transmitted via Wire to an unverified counterparty."
        final_report, meta, fallback_applied = self.llm.validate_citations_and_facts(hallucinated_text, valid_map, res)
        
        self.assertTrue(fallback_applied)
        self.assertTrue(meta["fallback_applied"])
        self.assertGreater(len(meta["factual_contradictions"]), 0)
        self.assertEqual(meta["status"], "FALLBACK_TRIGGERED_HALLUCINATION_DETECTED")
        self.assertTrue(final_report.startswith("VERDICT: NOTHING_FLAGGED"))

    def test_validate_citations_and_facts_detects_hallucinated_date(self):
        """Fact validation catches invented transaction dates and safely triggers deterministic fallback."""
        txn = Transaction(
            transaction_id="TXN-1015",
            customer_id="CUST-101",
            timestamp="2026-08-01T12:00:00",
            description="Purchase",
            payee="Cafe",
            amount=45.00,
            channel="POS"
        )
        valid_map = {"TXN-1015": txn}
        res = self.rule_engine.evaluate_customer("CUST-101")
        
        hallucinated_text = "Transaction [TXN-1015] was executed on 2024-01-01 in deviation from normal schedule."
        final_report, meta, fallback_applied = self.llm.validate_citations_and_facts(hallucinated_text, valid_map, res)
        
        self.assertTrue(fallback_applied)
        self.assertTrue(meta["fallback_applied"])
        self.assertGreater(len(meta["factual_contradictions"]), 0)
        self.assertEqual(meta["status"], "FALLBACK_TRIGGERED_HALLUCINATION_DETECTED")
        self.assertTrue(final_report.startswith("VERDICT: NOTHING_FLAGGED"))

    def test_post_process_report_enforces_deterministic_verdict_supremacy(self):
        """Even if LLM tries to emit a rogue verdict, post_process_report enforces deterministic engine verdict."""
        res = self.rule_engine.evaluate_customer("CUST-101")
        self.assertEqual(res.verdict, "NOTHING_FLAGGED")
        
        rogue_llm_text = (
            "VERDICT: FRAUD_DETECTED_CONFIRMED\n\n"
            "### 📋 Executive Summary\n"
            "Customer account has been compromised."
        )
        cleaned = self.llm._post_process_report(rogue_llm_text, res)
        
        # Line 1 must strictly be deterministic verdict
        self.assertTrue(cleaned.startswith("VERDICT: NOTHING_FLAGGED"))
        self.assertNotIn("FRAUD_DETECTED_CONFIRMED", cleaned)
        self.assertIn("DISCLAIMER:", cleaned)


if __name__ == "__main__":
    unittest.main()

