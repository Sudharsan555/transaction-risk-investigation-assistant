import unittest
from src.data_loader import DataLoader, parse_iso_datetime, sanitize_float
from src.models import Transaction


class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()

    def test_load_all_customers(self):
        customers = self.loader.get_all_customers()
        self.assertGreaterEqual(len(customers), 18)
        c_ids = [c.customer_id for c in customers]
        self.assertIn("CUST-101", c_ids)
        self.assertIn("CUST-104", c_ids)
        self.assertIn("CUST-199", c_ids)

    def test_customer_transactions_integrity(self):
        txns = self.loader.get_customer_transactions("CUST-104")
        self.assertGreater(len(txns), 50)
        # Verify chronological order
        timestamps = [t.timestamp for t in txns]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_empty_customer_history(self):
        txns = self.loader.get_customer_transactions("CUST-199")
        self.assertEqual(len(txns), 0)

    def test_sanitize_float(self):
        self.assertEqual(sanitize_float(10.5), 10.5)
        self.assertEqual(sanitize_float("123.45"), 123.45)
        self.assertEqual(sanitize_float("invalid"), 0.0)
        self.assertEqual(sanitize_float(None, 5.0), 5.0)

    def test_parse_iso_datetime(self):
        dt = parse_iso_datetime("2026-08-28T14:22:15")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 14)
        self.assertIsNone(parse_iso_datetime("invalid-date"))

    def test_malformed_transaction_skipping(self):
        # Missing required ID
        res1 = self.loader._parse_transaction_row({"transaction_id": "", "customer_id": "CUST-101", "amount": "100"})
        self.assertIsNone(res1)
        # Invalid amount <= 0
        res2 = self.loader._parse_transaction_row({"transaction_id": "TXN-999", "customer_id": "CUST-101", "amount": "-50"})
        self.assertIsNone(res2)
        # Corrupted non-numeric amount
        res3 = self.loader._parse_transaction_row({"transaction_id": "TXN-999", "customer_id": "CUST-101", "amount": "abc"})
        self.assertIsNone(res3)


if __name__ == "__main__":
    unittest.main()
