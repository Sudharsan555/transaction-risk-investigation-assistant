"""
Deterministic Risk Rule Engine for Transaction Investigation (PS06).
Pure Python / pandas logic with zero LLM and zero network dependencies.
Evaluates customer transaction histories against individual baselines.
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import math

from src.models import Transaction, CustomerProfile, RiskFinding, InvestigationResult
from src.data_loader import DataLoader, parse_iso_datetime, data_loader


class RiskRuleEngine:
    def __init__(self, loader: Optional[DataLoader] = None):
        self.loader = loader or data_loader

    def evaluate_customer(
        self,
        customer_id: str,
        transactions: Optional[List[Transaction]] = None,
        profile: Optional[CustomerProfile] = None
    ) -> InvestigationResult:
        """
        Main evaluation entrypoint for a single customer.
        Accepts optional override transactions/profile for sandbox/custom analysis.
        """
        # 1. Resolve Profile & Transactions
        if profile is None:
            profile = self.loader.get_customer(customer_id)
        
        if transactions is None:
            transactions = self.loader.get_customer_transactions(customer_id)

        # Fallback profile derivation if missing
        if profile is None:
            profile = self.loader.derive_baseline(transactions, customer_id)

        # 2. Edge Case: Empty or Near-Empty Transaction History
        if not transactions or len(transactions) == 0:
            return self._build_empty_history_result(profile)

        # Clone transactions so we can safely annotate flags
        txns = [t.model_copy(deep=True) for t in transactions]
        txns.sort(key=lambda t: t.timestamp)

        findings: List[RiskFinding] = []
        cited_txn_id_set: Set[str] = set()
        flag_reason_map: Dict[str, List[str]] = {}

        # 3. Rule 1: Unusually Large Transfers (Statistical Outlier)
        large_transfer_findings = self._evaluate_large_transfers(txns, profile)
        findings.extend(large_transfer_findings)

        # 4. Rule 2: Burst of Transfers to New Payee
        new_payee_findings = self._evaluate_new_payee_burst(txns, profile)
        findings.extend(new_payee_findings)

        # 5. Rule 3: Odd-Hours Activity
        odd_hours_findings = self._evaluate_odd_hours(txns, profile)
        findings.extend(odd_hours_findings)

        # 6. Rule 4: Break from Established Pattern (Channel / Velocity / Category)
        pattern_break_findings = self._evaluate_pattern_break(txns, profile)
        findings.extend(pattern_break_findings)

        # 7. Collect cited transaction IDs and reasons
        for f in findings:
            for t_id in f.cited_transaction_ids:
                cited_txn_id_set.add(t_id)
                if t_id not in flag_reason_map:
                    flag_reason_map[t_id] = []
                flag_reason_map[t_id].append(f.rule_name)

        # Annotate transactions
        cited_transactions: List[Transaction] = []
        for t in txns:
            if t.transaction_id in cited_txn_id_set:
                t.is_flagged = True
                t.flag_reasons = flag_reason_map.get(t.transaction_id, [])
                cited_transactions.append(t)

        # 8. Compute Risk Score & Verdict
        risk_score = self._calculate_risk_score(findings)
        verdict = "ATTENTION NEEDED" if len(findings) > 0 else "NOTHING FLAGGED"
        
        # Determine baseline evidence status: distinguish routine clean history from insufficient data
        if len(txns) < 3 and len(findings) == 0:
            evidence_status = "INSUFFICIENT_EVIDENCE"
        else:
            evidence_status = "SUFFICIENT_HISTORY"

        # Summary statistics
        total_vol = sum(t.amount for t in txns)
        summary_stats = {
            "total_transactions": len(txns),
            "total_volume": round(total_vol, 2),
            "flagged_transactions_count": len(cited_transactions),
            "earliest_transaction": txns[0].timestamp if txns else None,
            "latest_transaction": txns[-1].timestamp if txns else None,
            "avg_transaction_amount": round(total_vol / len(txns), 2) if txns else 0.0
        }

        baseline_dict = {
            "baseline_avg_amount": profile.baseline_avg_amount,
            "baseline_std_amount": profile.baseline_std_amount,
            "baseline_max_normal": profile.baseline_max_normal,
            "baseline_active_hours": profile.baseline_active_hours,
            "known_payees_count": len(profile.known_payees),
            "known_payees_sample": profile.known_payees[:6],
            "common_channels": profile.common_channels
        }

        return InvestigationResult(
            customer_id=profile.customer_id,
            customer_name=profile.name,
            account_type=profile.account_type,
            account_number=profile.account_number,
            verdict=verdict,
            evidence_status=evidence_status,
            risk_score=risk_score,
            findings_count=len(findings),
            findings=findings,
            cited_transactions=cited_transactions,
            customer_baseline=baseline_dict,
            summary_statistics=summary_stats,
            llm_report=None,
            llm_model_used=None,
            fallback_used=False
        )

    def _evaluate_large_transfers(
        self, txns: List[Transaction], profile: CustomerProfile
    ) -> List[RiskFinding]:
        """
        Detects transactions that are statistical outliers compared to customer's baseline.
        Z-Score > 3.0 and amount > 2.5x baseline average, and > baseline_max_normal.
        """
        findings = []
        avg = profile.baseline_avg_amount
        std = profile.baseline_std_amount
        max_norm = profile.baseline_max_normal

        # Skip rule if baseline has no historical spend
        if avg <= 0:
            return findings

        for t in txns:
            # If std is very small, use multiplier threshold
            effective_std = std if std > 5.0 else max(10.0, avg * 0.3)
            z_score = (t.amount - avg) / effective_std

            is_outlier = False
            # Outlier condition:
            # 1. Z-score >= 3.2 AND amount is at least 3.0x average AND amount exceeds max normal
            # 2. OR amount > 5x max normal
            if (z_score >= 3.2 and t.amount >= avg * 2.8 and t.amount > max_norm) or (t.amount >= max_norm * 4.0 and t.amount > 1000.0):
                is_outlier = True

            if is_outlier:
                severity = "HIGH" if (t.amount > 5000.0 or z_score >= 5.0) else "MEDIUM"
                findings.append(
                    RiskFinding(
                        rule_id="RULE_LARGE_TRANSFER",
                        rule_name="Unusually Large Transfer Outlier",
                        severity=severity,
                        cited_transaction_ids=[t.transaction_id],
                        metric_observed=f"${t.amount:,.2f} via {t.channel} to '{t.payee}' (Z-score: {z_score:.1f})",
                        baseline_reference=f"Customer historical avg: ${avg:,.2f} (std: ${std:,.2f}), standard ceiling: ${max_norm:,.2f}",
                        technical_summary=(
                            f"Transaction {t.transaction_id} of ${t.amount:,.2f} on {t.timestamp[:10]} significantly exceeds "
                            f"the customer's established spending baseline of ${avg:,.2f} by {t.amount / max(avg, 1.0):.1f}x."
                        ),
                        suggested_first_step=(
                            f"Contact account holder via out-of-band verified phone to confirm authorization of ${t.amount:,.2f} "
                            f"payment to '{t.payee}'."
                        )
                    )
                )

        return findings

    def _evaluate_new_payee_burst(
        self, txns: List[Transaction], profile: CustomerProfile
    ) -> List[RiskFinding]:
        """
        Detects multiple transfers (>= 2) to a previously unseen payee within a short window (<= 48h).
        """
        findings = []
        known_set = set(p.lower().strip() for p in profile.known_payees)

        # Group transactions by payee
        payee_txns: Dict[str, List[Transaction]] = {}
        for t in txns:
            p_clean = t.payee.strip()
            if p_clean.lower() not in known_set:
                if p_clean not in payee_txns:
                    payee_txns[p_clean] = []
                payee_txns[p_clean].append(t)

        for payee_name, p_list in payee_txns.items():
            if len(p_list) < 2:
                continue

            # Check sliding 48-hour window
            p_list.sort(key=lambda x: x.timestamp)
            burst_clusters: List[List[Transaction]] = []
            current_cluster = [p_list[0]]

            for next_txn in p_list[1:]:
                dt_prev = parse_iso_datetime(current_cluster[-1].timestamp)
                dt_curr = parse_iso_datetime(next_txn.timestamp)
                if dt_prev and dt_curr and (dt_curr - dt_prev) <= timedelta(hours=48):
                    current_cluster.append(next_txn)
                else:
                    if len(current_cluster) >= 2:
                        burst_clusters.append(current_cluster)
                    current_cluster = [next_txn]

            if len(current_cluster) >= 2:
                burst_clusters.append(current_cluster)

            for cluster in burst_clusters:
                total_burst_amt = sum(c.amount for c in cluster)
                cited_ids = [c.transaction_id for c in cluster]
                dt_first = cluster[0].timestamp
                dt_last = cluster[-1].timestamp
                
                severity = "HIGH" if (len(cluster) >= 3 or total_burst_amt >= 3000.0) else "MEDIUM"

                findings.append(
                    RiskFinding(
                        rule_id="RULE_NEW_PAYEE_BURST",
                        rule_name="Burst of Transfers to Newly Added Payee",
                        severity=severity,
                        cited_transaction_ids=cited_ids,
                        metric_observed=f"{len(cluster)} transactions totaling ${total_burst_amt:,.2f} to new counterparty '{payee_name}'",
                        baseline_reference=f"Payee '{payee_name}' has 0 historical transactions in account profile; customer has {len(known_set)} known payees.",
                        technical_summary=(
                            f"Rapid sequence of {len(cluster)} payments to newly introduced counterparty '{payee_name}' "
                            f"between {dt_first} and {dt_last} (Total: ${total_burst_amt:,.2f})."
                        ),
                        suggested_first_step=(
                            f"Review counterparty registration time for '{payee_name}', inspect IP/device fingerprint consistency, "
                            f"and verify whether secondary MFA was triggered during payee addition."
                        )
                    )
                )

        return findings

    def _evaluate_odd_hours(
        self, txns: List[Transaction], profile: CustomerProfile
    ) -> List[RiskFinding]:
        """
        Detects transactions executed outside the customer's established active hours window.
        Only flags if the amount is non-trivial (> 1.2x baseline avg or > $150).
        """
        findings = []
        active_hours = profile.baseline_active_hours
        if not active_hours or len(active_hours) < 2:
            return findings

        start_h, end_h = active_hours[0], active_hours[1]
        odd_hour_txns: List[Transaction] = []

        for t in txns:
            dt = parse_iso_datetime(t.timestamp)
            if not dt:
                continue

            hour = dt.hour
            # Check if outside window
            is_odd = False
            if start_h <= end_h:
                if hour < start_h or hour > end_h:
                    is_odd = True
            else:
                # Night owl window spanning midnight (e.g. 20:00 to 04:00)
                if hour > end_h and hour < start_h:
                    is_odd = True

            if is_odd and (t.amount >= max(150.0, profile.baseline_avg_amount * 1.2)):
                odd_hour_txns.append(t)

        if odd_hour_txns:
            # Group or flag individual
            cited_ids = [t.transaction_id for t in odd_hour_txns]
            total_odd_amt = sum(t.amount for t in odd_hour_txns)
            hours_str = ", ".join([f"{parse_iso_datetime(t.timestamp).strftime('%H:%M')} on {t.timestamp[:10]}" for t in odd_hour_txns[:3]])
            
            severity = "HIGH" if (total_odd_amt > 2000.0 or len(odd_hour_txns) >= 2) else "MEDIUM"

            findings.append(
                RiskFinding(
                    rule_id="RULE_ODD_HOURS",
                    rule_name="Odd-Hours Transaction Activity",
                    severity=severity,
                    cited_transaction_ids=cited_ids,
                    metric_observed=f"{len(odd_hour_txns)} odd-hour transactions totaling ${total_odd_amt:,.2f} (Timestamps: {hours_str})",
                    baseline_reference=f"Customer established active window is {start_h:02d}:00 to {end_h:02d}:00.",
                    technical_summary=(
                        f"Detected transactions executed during inactive overnight hours ({hours_str}) "
                        f"in direct deviation from the customer's established diurnal pattern."
                    ),
                    suggested_first_step=(
                        "Examine session authentication logs, geolocation IP tags, and device identifiers associated "
                        "with the overnight transactions to detect potential credential stuffing or session hijacking."
                    )
                )
            )

        return findings

    def _evaluate_pattern_break(
        self, txns: List[Transaction], profile: CustomerProfile
    ) -> List[RiskFinding]:
        """
        Detects breaks from established baseline:
        - Sudden high-risk channel usage (e.g. Wire/International when customer baseline is strictly POS/Mobile).
        - High-risk categories (Cryptocurrency, Offshore, International Remittance).
        """
        findings = []
        common_channels_lower = set(c.lower() for c in profile.common_channels)
        
        # Check for uncharacteristic Wire / International transfers
        wire_txns = []
        high_risk_category_txns = []

        for t in txns:
            ch_lower = t.channel.lower()
            cat_lower = (t.category or "").lower()

            # Channel deviation: Wire transaction on an account with no baseline wire usage
            if ch_lower == "wire" and "wire" not in common_channels_lower and t.amount > 1000.0:
                wire_txns.append(t)

            # High risk category deviation
            if any(k in cat_lower for k in ["crypto", "offshore", "international wire", "liquidation"]):
                high_risk_category_txns.append(t)

        # Wire Channel Break Finding
        if wire_txns:
            cited_ids = [t.transaction_id for t in wire_txns]
            total_wire_amt = sum(t.amount for t in wire_txns)
            findings.append(
                RiskFinding(
                    rule_id="RULE_PATTERN_BREAK",
                    rule_name="Channel & Velocity Pattern Break",
                    severity="HIGH" if total_wire_amt > 5000.0 else "MEDIUM",
                    cited_transaction_ids=cited_ids,
                    metric_observed=f"{len(wire_txns)} high-value Wire transactions totaling ${total_wire_amt:,.2f}",
                    baseline_reference=f"Account channel baseline is strictly {', '.join(profile.common_channels)}; Wire transfers are unprecedented.",
                    technical_summary=(
                        f"Account initiated {len(wire_txns)} Wire transfers totaling ${total_wire_amt:,.2f}. "
                        f"Customer history reflects zero baseline usage of wire remittance channels."
                    ),
                    suggested_first_step=(
                        "Verify beneficiary banking details with originator institution, place temporary hold on pending outbound wires, "
                        "and request supervisor validation."
                    )
                )
            )

        # High Risk Category Finding
        if high_risk_category_txns:
            # Deduplicate with already cited wire IDs if identical
            unique_cat_txns = [t for t in high_risk_category_txns if t.transaction_id not in [f_id for f in findings for f_id in f.cited_transaction_ids]]
            if unique_cat_txns:
                cited_ids = [t.transaction_id for t in unique_cat_txns]
                total_cat_amt = sum(t.amount for t in unique_cat_txns)
                findings.append(
                    RiskFinding(
                        rule_id="RULE_PATTERN_BREAK",
                        rule_name="Atypical Merchant Category Profile",
                        severity="HIGH" if total_cat_amt > 3000.0 else "MEDIUM",
                        cited_transaction_ids=cited_ids,
                        metric_observed=f"{len(unique_cat_txns)} transactions totaling ${total_cat_amt:,.2f} in high-risk categories ({unique_cat_txns[0].category})",
                        baseline_reference="Customer historical activity is restricted to domestic retail, utilities, and standard merchant categories.",
                        technical_summary=(
                            f"Transactions directed towards high-risk merchant categories ({unique_cat_txns[0].category}) "
                            f"which represent an anomalous departure from historical spending taxonomy."
                        ),
                        suggested_first_step=(
                            "Confirm whether the customer has authorized new merchant categories or recently engaged in foreign exchange / digital asset transactions."
                        )
                    )
                )

        return findings

    def _calculate_risk_score(self, findings: List[RiskFinding]) -> int:
        """Calculates a normalized 0-100 composite risk score from findings."""
        if not findings:
            return 0
        score = 0
        for f in findings:
            if f.severity == "HIGH":
                score += 40
            elif f.severity == "MEDIUM":
                score += 25
            else:
                score += 15
        return min(100, score)

    def _build_empty_history_result(self, profile: CustomerProfile) -> InvestigationResult:
        """Constructs a clean, non-alarming result for empty or new accounts."""
        return InvestigationResult(
            customer_id=profile.customer_id,
            customer_name=profile.name,
            account_type=profile.account_type,
            account_number=profile.account_number,
            verdict="NOTHING FLAGGED",
            evidence_status="INSUFFICIENT_EVIDENCE",
            risk_score=0,
            findings_count=0,
            findings=[],
            cited_transactions=[],
            customer_baseline={
                "baseline_avg_amount": 0.0,
                "baseline_std_amount": 0.0,
                "baseline_max_normal": 0.0,
                "baseline_active_hours": profile.baseline_active_hours,
                "known_payees_count": 0,
                "known_payees_sample": [],
                "common_channels": profile.common_channels
            },
            summary_statistics={
                "total_transactions": 0,
                "total_volume": 0.0,
                "flagged_transactions_count": 0,
                "earliest_transaction": None,
                "latest_transaction": None,
                "avg_transaction_amount": 0.0
            },
            llm_report=None,
            llm_model_used=None,
            fallback_used=False
        )


# Global singleton instance
rule_engine = RiskRuleEngine()
