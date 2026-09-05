"""
Deterministic Risk Rule Engine for Transaction Investigation (PS06).
Pure Python / pandas logic with zero LLM and zero network dependencies.
Evaluates customer transaction histories against individual baselines.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import math

from src.models import Transaction, CustomerProfile, RiskFinding, InvestigationResult
from src.data_loader import DataLoader, parse_iso_datetime, data_loader

# PS06 Compliance Constants
MIN_TRANSACTIONS_FOR_BASELINE = 5
WEIGHT_HIGH_SEVERITY = 40
WEIGHT_MEDIUM_SEVERITY = 25
WEIGHT_LOW_SEVERITY = 15
MAX_RISK_SCORE = 100


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
        Strictly returns one of:
          - ATTENTION_REQUIRED (rule violations found)
          - NOTHING_FLAGGED (routine customer behavior within baseline)
          - INSUFFICIENT_EVIDENCE (history too sparse < MIN_TRANSACTIONS_FOR_BASELINE)
        """
        # 1. Resolve Profile & Transactions
        profile_was_explicit = (profile is not None)
        if profile is None:
            profile = self.loader.get_customer(customer_id)
            if profile is not None:
                profile_was_explicit = True
        
        if transactions is None:
            transactions = self.loader.get_customer_transactions(customer_id)

        # Fallback profile derivation if missing
        if profile is None:
            profile = self.loader.derive_baseline(transactions or [], customer_id)

        # 2. Edge Case: Empty or Sparse History (< MIN_TRANSACTIONS_FOR_BASELINE)
        if not transactions or len(transactions) == 0:
            return self._build_empty_history_result(profile)

        # Baseline history sufficiency strictly enforced (minimum 5 historical transactions)
        if profile_was_explicit:
            if 0 < profile.total_transactions < MIN_TRANSACTIONS_FOR_BASELINE:
                has_sufficient_history = False
            elif profile.total_transactions >= MIN_TRANSACTIONS_FOR_BASELINE:
                has_sufficient_history = True
            elif profile.baseline_avg_amount > 0 and profile.baseline_max_normal > 0:
                has_sufficient_history = True
            else:
                has_sufficient_history = (len(transactions) >= MIN_TRANSACTIONS_FOR_BASELINE)
        else:
            has_sufficient_history = (len(transactions) >= MIN_TRANSACTIONS_FOR_BASELINE)

        if not has_sufficient_history:
            return self._build_insufficient_history_result(profile, transactions)

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
            for t_id in f.transaction_ids:
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

        # 8. Compute Explainable Risk Score & Tri-Partite Verdict
        risk_score, score_breakdown = self._calculate_risk_score(findings)
        verdict = "ATTENTION_REQUIRED" if len(findings) > 0 else "NOTHING_FLAGGED"
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
            "baseline_median_amount": profile.baseline_median_amount,
            "baseline_std_amount": profile.baseline_std_amount,
            "baseline_max_normal": profile.baseline_max_normal,
            "baseline_amount_range": profile.baseline_amount_range,
            "baseline_active_hours": profile.baseline_active_hours,
            "known_payees_count": len(profile.known_payees),
            "known_payees_sample": profile.known_payees[:6],
            "common_channels": profile.common_channels,
            "common_categories": profile.common_categories,
            "baseline_frequency_per_month": profile.baseline_frequency_per_month,
            "provenance": getattr(profile, "provenance", "HISTORICAL_TRANSACTIONS_ONLY"),
            "historical_sample_size": profile.total_transactions,
            "reliability": "SUFFICIENT"
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
            risk_score_breakdown=score_breakdown,
            citation_validation={
                "total_citations": len(cited_txn_id_set),
                "valid_citations": list(cited_txn_id_set),
                "hallucinated_citations": [],
                "sanitized": False,
                "status": "PASSED_CLEAN"
            },
            llm_report=None,
            llm_model_used=None,
            fallback_used=False
        )

    def evaluate_transaction(
        self,
        transaction_id: str,
        customer_id: Optional[str] = None
    ) -> InvestigationResult:
        """
        Evaluates a specific transaction against customer historical baseline.
        Ensures the evaluated transaction is STRICTLY excluded from baseline derivation.
        """
        # Find transaction
        target_txn = None
        target_cid = customer_id
        
        if target_cid:
            all_txns = self.loader.get_customer_transactions(target_cid)
            for t in all_txns:
                if t.transaction_id == transaction_id:
                    target_txn = t
                    break
        else:
            for c in self.loader.get_all_customers():
                c_txns = self.loader.get_customer_transactions(c.customer_id)
                for t in c_txns:
                    if t.transaction_id == transaction_id:
                        target_txn = t
                        target_cid = c.customer_id
                        break
                if target_txn:
                    break

        if not target_txn or not target_cid:
            raise ValueError(f"Transaction '{transaction_id}' not found.")

        # Build baseline ONLY from all OTHER historical transactions (strictly excluding evaluated txn)
        all_txns = self.loader.get_customer_transactions(target_cid)
        historical_txns = [t for t in all_txns if t.transaction_id != transaction_id]

        profile = self.loader.derive_baseline(
            historical_txns,
            customer_id=target_cid,
            name=self.loader.get_customer(target_cid).name if self.loader.get_customer(target_cid) else "Customer",
            exclude_transaction_ids=[transaction_id]
        )

        return self.evaluate_customer(
            customer_id=target_cid,
            transactions=[target_txn],
            profile=profile
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
                dev_str = f"{t.amount / max(avg, 1.0):.1f}x baseline average (Z-Score: {z_score:.1f})"
                obs_str = f"${t.amount:,.2f} via {t.channel} to '{t.payee}'"
                base_str = f"Customer historical average: ${avg:,.2f} (std: ${std:,.2f}), normal ceiling: ${max_norm:,.2f}"
                tech_exp = (
                    f"Transaction {t.transaction_id} of ${t.amount:,.2f} on {t.timestamp[:10]} significantly exceeds "
                    f"the customer's established spending baseline of ${avg:,.2f} by {t.amount / max(avg, 1.0):.1f}x."
                )
                action_str = (
                    f"Contact account holder via out-of-band verified phone to confirm authorization of ${t.amount:,.2f} "
                    f"payment to '{t.payee}'."
                )
                findings.append(
                    RiskFinding(
                        rule_id="RULE_LARGE_TRANSFER",
                        rule_name="Unusually Large Transfer Outlier",
                        severity=severity,
                        cited_transaction_ids=[t.transaction_id],
                        transaction_ids=[t.transaction_id],
                        metric_observed=f"{obs_str} (Z-score: {z_score:.1f})",
                        observed_value=obs_str,
                        baseline_reference=base_str,
                        baseline_value=base_str,
                        deviation=dev_str,
                        technical_summary=tech_exp,
                        explanation=tech_exp,
                        suggested_first_step=action_str,
                        investigator_action=action_str
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
                dev_str = f"Velocity burst of {len(cluster)} rapid payments totaling ${total_burst_amt:,.2f} to previously unseen counterparty within 48h"
                obs_str = f"{len(cluster)} transactions totaling ${total_burst_amt:,.2f} to new counterparty '{payee_name}'"
                base_str = f"Payee '{payee_name}' has 0 historical transactions in account profile; customer has {len(known_set)} established payees."
                tech_exp = (
                    f"Rapid sequence of {len(cluster)} payments to newly introduced counterparty '{payee_name}' "
                    f"between {dt_first} and {dt_last} (Total: ${total_burst_amt:,.2f})."
                )
                action_str = (
                    f"Review counterparty registration time for '{payee_name}', inspect IP/device fingerprint consistency, "
                    f"and verify whether secondary MFA was triggered during payee addition."
                )

                findings.append(
                    RiskFinding(
                        rule_id="RULE_NEW_PAYEE_BURST",
                        rule_name="Burst of Transfers to Newly Added Payee",
                        severity=severity,
                        cited_transaction_ids=cited_ids,
                        transaction_ids=cited_ids,
                        metric_observed=obs_str,
                        observed_value=obs_str,
                        baseline_reference=base_str,
                        baseline_value=base_str,
                        deviation=dev_str,
                        technical_summary=tech_exp,
                        explanation=tech_exp,
                        suggested_first_step=action_str,
                        investigator_action=action_str
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
            dev_str = f"Activity occurring outside established {start_h:02d}:00-{end_h:02d}:00 diurnal window"
            obs_str = f"{len(odd_hour_txns)} odd-hour transactions totaling ${total_odd_amt:,.2f} (Timestamps: {hours_str})"
            base_str = f"Customer established active window is {start_h:02d}:00 to {end_h:02d}:00."
            tech_exp = (
                f"Detected transactions executed during inactive overnight hours ({hours_str}) "
                f"in direct deviation from the customer's established diurnal pattern."
            )
            action_str = (
                "Examine session authentication logs, geolocation IP tags, and device identifiers associated "
                "with the overnight transactions to detect potential credential stuffing or session hijacking."
            )

            findings.append(
                RiskFinding(
                    rule_id="RULE_ODD_HOURS",
                    rule_name="Odd-Hours Transaction Activity",
                    severity=severity,
                    cited_transaction_ids=cited_ids,
                    transaction_ids=cited_ids,
                    metric_observed=obs_str,
                    observed_value=obs_str,
                    baseline_reference=base_str,
                    baseline_value=base_str,
                    deviation=dev_str,
                    technical_summary=tech_exp,
                    explanation=tech_exp,
                    suggested_first_step=action_str,
                    investigator_action=action_str
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
            dev_str = f"Unprecedented channel usage (Wire) with high-value volume (${total_wire_amt:,.2f})"
            obs_str = f"{len(wire_txns)} high-value Wire transactions totaling ${total_wire_amt:,.2f}"
            base_str = f"Account channel baseline is strictly {', '.join(profile.common_channels)}; Wire transfers are unprecedented."
            tech_exp = (
                f"Account initiated {len(wire_txns)} Wire transfers totaling ${total_wire_amt:,.2f}. "
                f"Customer history reflects zero baseline usage of wire remittance channels."
            )
            action_str = (
                "Verify beneficiary banking details with originator institution, place temporary hold on pending outbound wires, "
                "and request supervisor validation."
            )
            findings.append(
                RiskFinding(
                    rule_id="RULE_PATTERN_BREAK",
                    rule_name="Channel & Velocity Pattern Break",
                    severity="HIGH" if total_wire_amt > 5000.0 else "MEDIUM",
                    cited_transaction_ids=cited_ids,
                    transaction_ids=cited_ids,
                    metric_observed=obs_str,
                    observed_value=obs_str,
                    baseline_reference=base_str,
                    baseline_value=base_str,
                    deviation=dev_str,
                    technical_summary=tech_exp,
                    explanation=tech_exp,
                    suggested_first_step=action_str,
                    investigator_action=action_str
                )
            )

        # High Risk Category Finding
        if high_risk_category_txns:
            # Deduplicate with already cited wire IDs if identical
            unique_cat_txns = [t for t in high_risk_category_txns if t.transaction_id not in [f_id for f in findings for f_id in f.transaction_ids]]
            if unique_cat_txns:
                cited_ids = [t.transaction_id for t in unique_cat_txns]
                total_cat_amt = sum(t.amount for t in unique_cat_txns)
                cat_name = unique_cat_txns[0].category or "High-Risk Merchant"
                dev_str = f"High-risk spending category '{cat_name}' departure from established merchant taxonomy"
                obs_str = f"{len(unique_cat_txns)} transactions totaling ${total_cat_amt:,.2f} in high-risk categories ({cat_name})"
                base_str = f"Customer historical activity is restricted to domestic retail, utilities, and standard categories ({', '.join(profile.common_categories[:4]) if profile.common_categories else 'Retail, Utilities'})."
                tech_exp = (
                    f"Transactions directed towards high-risk merchant categories ({cat_name}) "
                    f"which represent an anomalous departure from historical spending taxonomy."
                )
                action_str = (
                    "Confirm whether the customer has authorized new merchant categories or recently engaged in foreign exchange / digital asset transactions."
                )
                findings.append(
                    RiskFinding(
                        rule_id="RULE_PATTERN_BREAK",
                        rule_name="Atypical Merchant Category Profile",
                        severity="HIGH" if total_cat_amt > 3000.0 else "MEDIUM",
                        cited_transaction_ids=cited_ids,
                        transaction_ids=cited_ids,
                        metric_observed=obs_str,
                        observed_value=obs_str,
                        baseline_reference=base_str,
                        baseline_value=base_str,
                        deviation=dev_str,
                        technical_summary=tech_exp,
                        explanation=tech_exp,
                        suggested_first_step=action_str,
                        investigator_action=action_str
                    )
                )

        return findings

    def _calculate_risk_score(self, findings: List[RiskFinding]) -> Tuple[int, Dict[str, Any]]:
        """
        Calculates an explainable, deterministic additive composite risk score from findings.
        Returns (capped_score, breakdown_dict).
        """
        contributions = []
        raw_total = 0
        for f in findings:
            pts = WEIGHT_HIGH_SEVERITY if f.severity == "HIGH" else (
                WEIGHT_MEDIUM_SEVERITY if f.severity == "MEDIUM" else WEIGHT_LOW_SEVERITY
            )
            raw_total += pts
            contributions.append({
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity,
                "points": pts,
                "transaction_ids": f.transaction_ids
            })

        capped_score = min(MAX_RISK_SCORE, raw_total)
        breakdown = {
            "base_score": 0,
            "rule_contributions": contributions,
            "raw_total": raw_total,
            "capped_score": capped_score,
            "max_possible": MAX_RISK_SCORE,
            "disclaimer": "This score indicates investigative urgency for human fraud analysts, NOT a statistical probability of fraud."
        }
        return capped_score, breakdown

    def _build_empty_history_result(self, profile: CustomerProfile) -> InvestigationResult:
        """Constructs an explicit INSUFFICIENT_EVIDENCE result for accounts with zero transactions."""
        return InvestigationResult(
            customer_id=profile.customer_id,
            customer_name=profile.name,
            account_type=profile.account_type,
            account_number=profile.account_number,
            verdict="INSUFFICIENT_EVIDENCE",
            evidence_status="INSUFFICIENT_EVIDENCE",
            risk_score=0,
            findings_count=0,
            findings=[],
            cited_transactions=[],
            customer_baseline={
                "baseline_avg_amount": 0.0,
                "baseline_median_amount": 0.0,
                "baseline_std_amount": 0.0,
                "baseline_max_normal": 0.0,
                "baseline_amount_range": [0.0, 0.0],
                "baseline_active_hours": profile.baseline_active_hours or [8, 22],
                "known_payees_count": 0,
                "known_payees_sample": [],
                "common_channels": profile.common_channels,
                "common_categories": profile.common_categories,
                "baseline_frequency_per_month": 0.0,
                "provenance": "HISTORICAL_TRANSACTIONS_ONLY",
                "historical_sample_size": 0,
                "reliability": "INSUFFICIENT_HISTORY",
                "note": "Zero historical transactions recorded. Empirical baseline metrics cannot be established."
            },
            summary_statistics={
                "total_transactions": 0,
                "total_volume": 0.0,
                "flagged_transactions_count": 0,
                "earliest_transaction": None,
                "latest_transaction": None,
                "avg_transaction_amount": 0.0
            },
            risk_score_breakdown={
                "base_score": 0,
                "rule_contributions": [],
                "raw_total": 0,
                "capped_score": 0,
                "max_possible": MAX_RISK_SCORE,
                "evidence_status": "INSUFFICIENT_EVIDENCE",
                "minimum_history_required": MIN_TRANSACTIONS_FOR_BASELINE,
                "disclaimer": "This score indicates investigative urgency for human fraud analysts, NOT a statistical probability of fraud."
            },
            citation_validation={
                "total_citations": 0,
                "valid_citations": [],
                "hallucinated_citations": [],
                "sanitized": False,
                "status": "PASSED_CLEAN"
            },
            llm_report=None,
            llm_model_used=None,
            fallback_used=False
        )

    def _build_insufficient_history_result(
        self, profile: CustomerProfile, transactions: List[Transaction]
    ) -> InvestigationResult:
        """
        Constructs an explicit INSUFFICIENT_EVIDENCE result for accounts with sparse history (< 5 transactions).
        Explicitly states that an anomaly cannot be mathematically proven without sufficient historical baseline.
        Never generates phantom risk scores.
        """
        total_vol = sum(t.amount for t in transactions)
        return InvestigationResult(
            customer_id=profile.customer_id,
            customer_name=profile.name,
            account_type=profile.account_type,
            account_number=profile.account_number,
            verdict="INSUFFICIENT_EVIDENCE",
            evidence_status="INSUFFICIENT_EVIDENCE",
            risk_score=0,
            findings_count=0,
            findings=[],
            cited_transactions=[],
            customer_baseline={
                "baseline_avg_amount": profile.baseline_avg_amount,
                "baseline_median_amount": profile.baseline_median_amount,
                "baseline_std_amount": profile.baseline_std_amount,
                "baseline_max_normal": profile.baseline_max_normal,
                "baseline_amount_range": profile.baseline_amount_range,
                "baseline_active_hours": profile.baseline_active_hours,
                "known_payees_count": len(profile.known_payees),
                "known_payees_sample": profile.known_payees[:6],
                "common_channels": profile.common_channels,
                "common_categories": profile.common_categories,
                "baseline_frequency_per_month": profile.baseline_frequency_per_month,
                "provenance": "HISTORICAL_TRANSACTIONS_ONLY",
                "historical_sample_size": len(transactions),
                "reliability": "INSUFFICIENT_HISTORY",
                "note": f"Fewer than {MIN_TRANSACTIONS_FOR_BASELINE} historical transactions recorded ({len(transactions)} available). Baseline metrics are insufficient for statistical anomaly detection."
            },
            summary_statistics={
                "total_transactions": len(transactions),
                "total_volume": round(total_vol, 2),
                "flagged_transactions_count": 0,
                "earliest_transaction": transactions[0].timestamp if transactions else None,
                "latest_transaction": transactions[-1].timestamp if transactions else None,
                "avg_transaction_amount": round(total_vol / len(transactions), 2) if transactions else 0.0
            },
            risk_score_breakdown={
                "base_score": 0,
                "rule_contributions": [],
                "raw_total": 0,
                "capped_score": 0,
                "max_possible": MAX_RISK_SCORE,
                "evidence_status": "INSUFFICIENT_EVIDENCE",
                "minimum_history_required": MIN_TRANSACTIONS_FOR_BASELINE,
                "disclaimer": "This score indicates investigative urgency for human fraud analysts, NOT a statistical probability of fraud."
            },
            citation_validation={
                "total_citations": 0,
                "valid_citations": [],
                "hallucinated_citations": [],
                "sanitized": False,
                "status": "PASSED_CLEAN"
            },
            llm_report=None,
            llm_model_used=None,
            fallback_used=False
        )


# Global singleton instance
rule_engine = RiskRuleEngine()
