"""
Data loader and validation module for customers and transactions.
Handles missing/malformed fields gracefully and computes customer baselines.
"""

import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import math

from src.config import DATA_DIR
from src.models import Transaction, CustomerProfile

logger = logging.getLogger("risk_investigation")


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parse ISO formatted timestamp or common datetime strings safely."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    dt_str = dt_str.strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def sanitize_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any value to float, handling None, NaN, and invalid strings."""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 2)
    except (ValueError, TypeError):
        return default


class DataLoader:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.customers_file = self.data_dir / "customers.json"
        self.transactions_file = self.data_dir / "transactions.csv"
        self._customers_cache: Dict[str, CustomerProfile] = {}
        self._transactions_cache: Dict[str, List[Transaction]] = {}
        self.reload_data()

    def reload_data(self) -> None:
        """Loads and indexes customers and transactions."""
        self._customers_cache = {}
        self._transactions_cache = {}

        # 1. Load customers.json
        if self.customers_file.exists():
            try:
                with open(self.customers_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        avg_amt = sanitize_float(item.get("baseline_avg_amount", 0.0))
                        max_norm = sanitize_float(item.get("baseline_max_normal", 0.0))
                        med_amt = sanitize_float(item.get("baseline_median_amount", avg_amt * 0.92))
                        amt_range = item.get("baseline_amount_range", [round(avg_amt * 0.1, 2), max_norm])
                        freq_per_m = sanitize_float(item.get("baseline_frequency_per_month", float(item.get("total_transactions", 0)) / 6.0 if item.get("total_transactions") else 0.0))
                        common_cats = item.get("common_categories", ["Retail", "Dining", "Groceries", "Utilities"])

                        cust = CustomerProfile(
                            customer_id=str(item.get("customer_id", "")).strip(),
                            name=str(item.get("name", "Unknown")),
                            account_type=str(item.get("account_type", "Standard")),
                            account_number=str(item.get("account_number", "ACC-00000000")),
                            baseline_avg_amount=avg_amt,
                            baseline_median_amount=med_amt,
                            baseline_std_amount=sanitize_float(item.get("baseline_std_amount", 0.0)),
                            baseline_max_normal=max_norm,
                            baseline_amount_range=amt_range,
                            baseline_active_hours=item.get("baseline_active_hours", [8, 22]),
                            known_payees=item.get("known_payees", []),
                            common_channels=item.get("common_channels", ["Mobile", "POS", "Web"]),
                            common_categories=common_cats,
                            baseline_frequency_per_month=freq_per_m,
                            total_transactions=int(item.get("total_transactions", 0)),
                            total_volume=sanitize_float(item.get("total_volume", 0.0)),
                            provenance=str(item.get("provenance", "HISTORICAL_TRANSACTIONS_ONLY"))
                        )
                        if cust.customer_id:
                            self._customers_cache[cust.customer_id] = cust
            except Exception as e:
                logger.warning(f"Error loading customers.json: {e}")

        # 2. Load transactions.csv
        if self.transactions_file.exists():
            try:
                with open(self.transactions_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        txn = self._parse_transaction_row(row)
                        if txn:
                            c_id = txn.customer_id
                            if c_id not in self._transactions_cache:
                                self._transactions_cache[c_id] = []
                            self._transactions_cache[c_id].append(txn)
            except Exception as e:
                logger.warning(f"Error loading transactions.csv: {e}")

        # Sort each customer's transactions chronologically
        for c_id in self._transactions_cache:
            self._transactions_cache[c_id].sort(key=lambda t: t.timestamp)

    def _parse_transaction_row(self, row: Dict[str, Any]) -> Optional[Transaction]:
        """Safely parses a transaction row, skipping corrupt/missing required fields with logging."""
        txn_id = str(row.get("transaction_id", "")).strip()
        cust_id = str(row.get("customer_id", "")).strip()
        timestamp_str = str(row.get("timestamp", "")).strip()
        
        # Must have transaction_id and customer_id
        if not txn_id or not cust_id:
            logger.warning(f"Skipping CSV row with missing transaction_id or customer_id: {row}")
            return None
        
        # Timestamp validation
        dt = parse_iso_datetime(timestamp_str)
        if not dt:
            logger.warning(f"Skipping CSV row with invalid timestamp format '{timestamp_str}': {row}")
            return None
            
        amount = sanitize_float(row.get("amount", 0.0))
        if amount <= 0:
            logger.warning(f"Skipping CSV row with invalid non-positive amount {amount}: {row}")
            return None

        payee = str(row.get("payee", "")).strip()
        if not payee:
            logger.warning(f"Skipping CSV row with missing payee: {row}")
            return None
            
        return Transaction(
            transaction_id=txn_id,
            customer_id=cust_id,
            timestamp=timestamp_str,
            description=str(row.get("description", "Transaction")).strip() or "Transaction",
            payee=payee,
            amount=amount,
            channel=str(row.get("channel", "Web")).strip() or "Web",
            category=str(row.get("category", "General")).strip() or "General"
        )

    def get_all_customers(self) -> List[CustomerProfile]:
        """Returns all loaded customer profiles."""
        return list(self._customers_cache.values())

    def get_customer(self, customer_id: str) -> Optional[CustomerProfile]:
        """Returns customer profile by customer_id."""
        return self._customers_cache.get(customer_id)

    def get_customer_transactions(self, customer_id: str) -> List[Transaction]:
        """Returns list of transactions for customer_id."""
        return self._transactions_cache.get(customer_id, [])

    def derive_baseline(
        self,
        transactions: List[Transaction],
        customer_id: str,
        name: str = "Unknown",
        exclude_transaction_ids: Optional[List[str]] = None
    ) -> CustomerProfile:
        """
        Derives baseline metrics dynamically from a given list of transactions.
        Strictly excludes any transaction ID passed in exclude_transaction_ids
        to ensure evaluated transactions never leak into the historical baseline.
        """
        exclude_set = set(exclude_transaction_ids or [])
        valid_txns = [t for t in transactions if t.amount > 0 and t.transaction_id not in exclude_set]
        if not valid_txns:
            return CustomerProfile(
                customer_id=customer_id,
                name=name,
                account_type="Standard Checking",
                account_number=f"ACC-{abs(hash(customer_id)) % 100000000:08d}",
                baseline_avg_amount=0.0,
                baseline_std_amount=0.0,
                baseline_max_normal=0.0,
                baseline_active_hours=[8, 22],
                known_payees=[],
                common_channels=["Mobile"],
                total_transactions=0,
                total_volume=0.0,
                provenance="HISTORICAL_TRANSACTIONS_ONLY"
            )

        amounts = [t.amount for t in valid_txns]
        n = len(amounts)
        avg = sum(amounts) / n
        sorted_amts = sorted(amounts)
        median_amt = sorted_amts[n // 2] if n % 2 != 0 else (sorted_amts[n // 2 - 1] + sorted_amts[n // 2]) / 2.0
        variance = sum((x - avg) ** 2 for x in amounts) / n if n > 1 else 0.0
        std = math.sqrt(variance)
        p95_idx = int(0.95 * n)
        max_normal = sorted_amts[min(p95_idx, n - 1)] * 1.5
        min_normal = round(sorted_amts[0], 2)
        amount_range = [min_normal, round(max_normal, 2)]

        # Frequency calculation
        timestamps = [parse_iso_datetime(t.timestamp) for t in valid_txns if parse_iso_datetime(t.timestamp)]
        if len(timestamps) >= 2:
            span_days = max(1.0, (max(timestamps) - min(timestamps)).total_seconds() / 86400.0)
            freq_per_month = round((len(valid_txns) / span_days) * 30.0, 1)
        else:
            freq_per_month = round(float(len(valid_txns)), 1)

        # Active hours
        hours = []
        for t in valid_txns:
            dt = parse_iso_datetime(t.timestamp)
            if dt:
                hours.append(dt.hour)
        if hours:
            min_h = max(0, min(hours))
            max_h = min(23, max(hours))
            active_hours = [min_h, max_h]
        else:
            active_hours = [8, 22]

        payees = list({t.payee for t in valid_txns if t.payee})
        channels = list({t.channel for t in valid_txns if t.channel})
        categories = list({t.category for t in valid_txns if t.category})

        return CustomerProfile(
            customer_id=customer_id,
            name=name,
            account_type="Standard Checking",
            account_number=f"ACC-{abs(hash(customer_id)) % 100000000:08d}",
            baseline_avg_amount=round(avg, 2),
            baseline_median_amount=round(median_amt, 2),
            baseline_std_amount=round(std, 2),
            baseline_max_normal=round(max_normal, 2),
            baseline_amount_range=amount_range,
            baseline_active_hours=active_hours,
            known_payees=payees[:20],
            common_channels=channels,
            common_categories=categories[:10],
            baseline_frequency_per_month=freq_per_month,
            total_transactions=len(valid_txns),
            total_volume=round(sum(amounts), 2),
            provenance="HISTORICAL_TRANSACTIONS_ONLY"
        )


# Global singleton instance
data_loader = DataLoader()
