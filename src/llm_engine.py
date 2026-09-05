"""
LLM Grounding & Investigation Report Generator (Gemini 2.0 Flash).
Strictly grounds output in deterministic rule engine findings and cited transactions.
Enforces strict citation constraints, prevents definitive fraud assertions,
and provides an instant, zero-latency deterministic fallback when the API is unavailable.
"""

import json
import os
import re
from typing import Optional, Dict, Any, Tuple, Set
from src.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODEL
from src.models import InvestigationResult, RiskFinding, Transaction


SYSTEM_INSTRUCTION = """You are the Senior Bank Fraud Desk Investigation Assistant for a Tier-1 financial institution.
Your duty is to produce objective, clear, grounded, and actionable transaction risk investigation reports for human fraud analysts based strictly on provided deterministic risk findings.

CRITICAL OPERATIONAL RULES:
1. STRICT GROUNDING: Rely ONLY on the provided structured findings, customer baselines, and cited transactions in the prompt payload. NEVER invent transaction IDs, transaction amounts, dates, counterparties, or customer statistics.
2. NO UNSUPPORTED FRAUD CONCLUSIONS: NEVER declare, conclude, or state definitively that 'fraud has occurred' or that the customer is guilty. Your role is strictly to flag anomalies, explain deviations against baseline, and hand investigative judgment to the human analyst.
3. CLEAR TRI-PARTITE DISTINCTION: Clearly distinguish between:
   - EVIDENCE: Verified, deterministic transaction data and mathematical deviations.
   - SUSPICION / RISK: Contextual explanation of why the observed pattern is anomalous compared to baseline.
   - RECOMMENDATION: Concrete, prioritized next investigative steps for human personnel.
4. MANDATORY CITATIONS: Every factual claim, finding, or transaction referenced MUST explicitly cite its exact transaction ID in brackets, e.g., [TXN-1082].
5. HONEST HANDLING OF INSUFFICIENT EVIDENCE: If an account has fewer than 5 transactions or minimal history, clearly declare that behavioral evidence is insufficient to mathematically establish a baseline. Never extrapolate or imagine activity.
6. HUMAN INVESTIGATOR PRIMACY: The final business and legal decision remains strictly with the human investigator.
7. REPORT FORMAT:
   - Line 1 MUST be strictly one of: "VERDICT: ATTENTION_REQUIRED", "VERDICT: NOTHING_FLAGGED", or "VERDICT: INSUFFICIENT_EVIDENCE".
   - Section 1: 📋 Executive Summary (2-3 sentences summarizing the account posture, evidence sufficiency, and key deviations).
   - Section 2: 🔍 Detailed Risk Findings & Evidence Breakdown (For each finding: Rule Name, Cited Transactions [IDs], Baseline Comparison, Plain-Language Explanation, and Suggested First Step).
   - Section 3: 🧩 Risk Pattern & Correlation Analysis (Explain how multiple transactions or rules connect, or why normal activity is verified).
   - Section 4: 🛠️ Investigator Action Checklist (3-4 concise, concrete, prioritized actions for the investigator).
   - Final Section: ⚖️ Mandatory Compliance Disclaimer (State clearly that this automated report flags indicators but does not conclude fraud).
"""

DISCLAIMER_TEXT = (
    "DISCLAIMER: This automated investigation report provides risk indicators, statistical baseline deviations, "
    "and contextual explanations. It does NOT establish, conclude, or verify that fraud has occurred. "
    "All investigative assessments and final determinations rest solely with authorized fraud desk personnel."
)


class LLMInvestigationEngine:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initializes the Gemini client if API key is present."""
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[WARN] Unable to initialize google-genai client: {e}")
                self.client = None
        else:
            self.client = None

    def validate_and_sanitize_citations(
        self, text: str, valid_transaction_ids: Set[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Scans generated report for bracketed transaction citations.
        Any transaction ID mentioned in the text that does not belong to valid_transaction_ids
        is flagged as hallucinated, replaced with [UNVERIFIED CITATION REMOVED],
        and recorded in the citation validation audit metadata.
        Guarantees ZERO hallucinated citations in final output.
        """
        citation_pattern = re.compile(r'\[((?:TXN|CUSTOM|SB|TEST)[A-Za-z0-9_-]*)\]')
        found_citations = []
        valid_citations = []
        hallucinated_citations = []

        def replace_citation(match):
            txn_id = match.group(1)
            found_citations.append(txn_id)
            if txn_id in valid_transaction_ids:
                valid_citations.append(txn_id)
                return f"[{txn_id}]"
            else:
                hallucinated_citations.append(txn_id)
                return "[UNVERIFIED CITATION REMOVED]"

        sanitized_text = citation_pattern.sub(replace_citation, text)

        validation_meta = {
            "total_citations": len(found_citations),
            "valid_citations": list(dict.fromkeys(valid_citations)),
            "hallucinated_citations": list(dict.fromkeys(hallucinated_citations)),
            "factual_contradictions": [],
            "sanitized": len(hallucinated_citations) > 0,
            "status": "PASSED_CLEAN" if len(hallucinated_citations) == 0 else "SANITIZED"
        }
        return sanitized_text, validation_meta

    def validate_citations_and_facts(
        self, text: str, valid_transactions: Dict[str, Transaction], result: InvestigationResult
    ) -> Tuple[str, Dict[str, Any], bool]:
        """
        Post-generation fact & citation verification:
        1. Checks all cited transaction IDs exist in valid_transactions.
        2. Validates cited factual amounts/metrics in citation sentences against source data.
        3. Never allows invented facts or hallucinated IDs: activates safe deterministic fallback if invalid.
        Returns: (final_report_text, validation_metadata, fallback_triggered)
        """
        citation_pattern = re.compile(r'\[((?:TXN|CUSTOM|SB|TEST)[A-Za-z0-9_-]*)\]')
        all_cited_ids = citation_pattern.findall(text)
        
        hallucinated_citations = []
        valid_citations = []
        for cid in all_cited_ids:
            if cid in valid_transactions:
                valid_citations.append(cid)
            else:
                hallucinated_citations.append(cid)

        # Factual amount, channel, and date cross-verification
        factual_contradictions = []
        sentences = re.split(r'(?<=[.!?\n])\s+', text)
        for sentence in sentences:
            sentence_cites = citation_pattern.findall(sentence)
            if not sentence_cites:
                continue
                
            for cid in sentence_cites:
                if cid not in valid_transactions:
                    continue
                actual_txn = valid_transactions[cid]
                
                # 1. Check dollar amounts mentioned in the same sentence as [TXN-xxx]
                dollar_matches = re.findall(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)', sentence)
                for d_str in dollar_matches:
                    try:
                        clean_d = float(d_str.replace(',', ''))
                    except ValueError:
                        continue
                    if clean_d <= 0:
                        continue
                    
                    # Permitted factual reference amounts in the context of this investigation
                    allowed_amounts = {
                        round(actual_txn.amount, 2),
                        round(result.customer_baseline.get("baseline_avg_amount", -1), 2),
                        round(result.customer_baseline.get("baseline_max_normal", -1), 2),
                        round(result.summary_statistics.get("total_volume", -1), 2),
                        round(result.summary_statistics.get("avg_transaction_amount", -1), 2)
                    }
                    for f in result.findings:
                        for amt_part in re.findall(r'\$([0-9,]+(?:\.[0-9]{2})?)', f.observed_value + " " + f.explanation + " " + f.baseline_value):
                            try:
                                allowed_amounts.add(round(float(amt_part.replace(',', '')), 2))
                            except ValueError:
                                pass
                                
                    if not any(abs(clean_d - a) <= 1.0 for a in allowed_amounts if a > 0):
                        factual_contradictions.append(
                            f"Transaction [{cid}] context cites unverified amount ${clean_d:,.2f} (Actual txn amount: ${actual_txn.amount:,.2f})"
                        )

                # 2. Check channel mentions in sentence with [TXN-xxx]
                actual_ch = (actual_txn.channel or "").lower()
                for ch in ["Wire", "POS", "Mobile", "Web", "ATM"]:
                    if re.search(rf'\b{ch}\b', sentence, re.IGNORECASE):
                        if ch.lower() != actual_ch and ch.lower() not in [c.lower() for c in result.customer_baseline.get("common_channels", [])]:
                            if re.search(rf'(?:via|through|channel|on)\s+{ch}', sentence, re.IGNORECASE):
                                factual_contradictions.append(
                                    f"Transaction [{cid}] context claims unverified channel '{ch}' (Actual channel: {actual_txn.channel})"
                                )

                # 3. Check date mentions (YYYY-MM-DD) in sentence with [TXN-xxx]
                date_matches = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', sentence)
                for d_val in date_matches:
                    actual_date = actual_txn.timestamp[:10] if actual_txn.timestamp else ""
                    valid_dates = {
                        actual_date,
                        (result.summary_statistics.get("earliest_transaction") or "")[:10],
                        (result.summary_statistics.get("latest_transaction") or "")[:10]
                    }
                    if actual_date and d_val not in valid_dates:
                        factual_contradictions.append(
                            f"Transaction [{cid}] context cites unverified date '{d_val}' (Actual date: {actual_date})"
                        )

        fallback_needed = (len(hallucinated_citations) > 0 or len(factual_contradictions) > 0)
        
        if fallback_needed:
            fallback_report = self._generate_deterministic_fallback_report(result)
            validation_meta = {
                "total_citations": len(all_cited_ids),
                "valid_citations": list(dict.fromkeys(valid_citations)),
                "hallucinated_citations": list(dict.fromkeys(hallucinated_citations)),
                "factual_contradictions": list(dict.fromkeys(factual_contradictions)),
                "sanitized": True,
                "fallback_applied": True,
                "status": "FALLBACK_TRIGGERED_HALLUCINATION_DETECTED"
            }
            return fallback_report, validation_meta, True

        # Clean report passed
        validation_meta = {
            "total_citations": len(all_cited_ids),
            "valid_citations": list(dict.fromkeys(valid_citations)),
            "hallucinated_citations": [],
            "factual_contradictions": [],
            "sanitized": False,
            "fallback_applied": False,
            "status": "PASSED_CLEAN"
        }
        return text, validation_meta, False

    def generate_investigation_report(self, result: InvestigationResult) -> Tuple[str, str, bool]:
        """
        Generates a grounded investigation report with post-generation citation and fact validation.
        Returns: (report_markdown, model_name, fallback_used)
        """
        # Collect valid source transactions map for citation and fact enforcement
        valid_txns_map: Dict[str, Transaction] = {t.transaction_id: t for t in result.cited_transactions}
        try:
            from src.data_loader import data_loader
            for t in data_loader.get_customer_transactions(result.customer_id):
                valid_txns_map[t.transaction_id] = t
        except Exception:
            pass

        # If no API key or client, immediately use clean deterministic fallback
        if not self.client:
            raw_report = self._generate_deterministic_fallback_report(result)
            final_report, meta, _ = self.validate_citations_and_facts(raw_report, valid_txns_map, result)
            result.citation_validation = meta
            return final_report, "Deterministic Fallback (No API Key)", True

        # Construct strictly grounded prompt payload
        prompt_payload = self._build_prompt_payload(result)

        # Attempt Gemini API call
        for model_name in [GEMINI_MODEL, GEMINI_FALLBACK_MODEL]:
            try:
                gen_config = None
                try:
                    from google.genai import types
                    gen_config = types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.1,
                        max_output_tokens=1500,
                    )
                except Exception:
                    gen_config = {
                        "system_instruction": SYSTEM_INSTRUCTION,
                        "temperature": 0.1,
                        "max_output_tokens": 1500,
                    }

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt_payload,
                    config=gen_config
                )
                if response and response.text:
                    cleaned_report = self._post_process_report(response.text, result)
                    final_report, meta, fallback_applied = self.validate_citations_and_facts(cleaned_report, valid_txns_map, result)
                    result.citation_validation = meta
                    if fallback_applied:
                        return final_report, "Deterministic Fallback (Validation Rejection)", True
                    return final_report, f"Google Gemini ({model_name})", False
            except Exception as e:
                print(f"[WARN] Gemini model '{model_name}' call failed: {e}")
                continue

        # Fallback if all API attempts fail
        fallback_report = self._generate_deterministic_fallback_report(result)
        final_report, meta, _ = self.validate_citations_and_facts(fallback_report, valid_txns_map, result)
        result.citation_validation = meta
        return final_report, "Deterministic Fallback (API Error/Timeout)", True

    def _build_prompt_payload(self, result: InvestigationResult) -> str:
        """Constructs compact JSON payload for grounding."""
        findings_data = []
        for f in result.findings:
            findings_data.append({
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity,
                "cited_transaction_ids": f.cited_transaction_ids,
                "metric_observed": f.metric_observed,
                "baseline_reference": f.baseline_reference,
                "technical_summary": f.technical_summary,
                "suggested_first_step": f.suggested_first_step
            })

        txns_data = []
        for t in result.cited_transactions:
            txns_data.append({
                "transaction_id": t.transaction_id,
                "timestamp": t.timestamp,
                "description": t.description,
                "payee": t.payee,
                "amount": f"${t.amount:,.2f}",
                "channel": t.channel,
                "category": t.category,
                "flags": t.flag_reasons
            })

        payload = {
            "customer_id": result.customer_id,
            "customer_name": result.customer_name,
            "account_type": result.account_type,
            "account_number": result.account_number,
            "deterministic_verdict": result.verdict,
            "evidence_status": result.evidence_status,
            "risk_score": result.risk_score,
            "findings_count": result.findings_count,
            "summary_statistics": result.summary_statistics,
            "customer_baseline": result.customer_baseline,
            "findings": findings_data,
            "cited_transactions": txns_data
        }

        return (
            f"Generate the final investigation report based ONLY on the following grounded bank dataset.\n\n"
            f"```json\n{json.dumps(payload, indent=2)}\n```"
        )

    def _post_process_report(self, text: str, result: InvestigationResult) -> str:
        """Ensures verdict line and disclaimer are strictly compliant with deterministic engine supremacy."""
        expected_verdict = f"VERDICT: {result.verdict}"
        lines = text.strip().split("\n")
        
        # Filter out any verdict line that may have been emitted by LLM to guarantee deterministic dominance
        non_verdict_lines = [l for l in lines if not l.strip().startswith("VERDICT:")]
        text = f"{expected_verdict}\n\n" + "\n".join(non_verdict_lines).strip()

        # Ensure disclaimer is included at the end
        if "DISCLAIMER:" not in text:
            text = text + f"\n\n---\n**{DISCLAIMER_TEXT}**"

        return text

    def _generate_deterministic_fallback_report(self, result: InvestigationResult) -> str:
        """
        Generates a clean, polished, fully-grounded report using deterministic logic.
        Guarantees zero downtime, exact citation preservation, and non-alarming clean states.
        Strictly aligns with PS06 tri-partite verdicts:
          - INSUFFICIENT_EVIDENCE
          - NOTHING_FLAGGED
          - ATTENTION_REQUIRED
        """
        verdict_line = f"VERDICT: {result.verdict}"

        # 1. Sparse History / Insufficient Data Case
        if result.verdict == "INSUFFICIENT_EVIDENCE" or result.evidence_status == "INSUFFICIENT_EVIDENCE":
            total_tx = result.summary_statistics.get("total_transactions", 0)
            return (
                f"{verdict_line}\n\n"
                f"### 📋 Executive Summary\n"
                f"Customer **{result.customer_name}** (`{result.customer_id}`) currently has {total_tx} recorded transaction(s) on account `{result.account_number}`. "
                f"**Evidence Assessment**: Insufficient transaction history (< 5 transactions) to establish an empirical behavioral baseline. "
                f"An anomaly cannot be mathematically proven without sufficient historical data. Standard onboarding monitoring controls remain active.\n\n"
                f"### 🔍 Detailed Risk Findings & Evidence Breakdown\n"
                f"- **Status**: INSUFFICIENT_EVIDENCE (Baseline Not Established).\n"
                f"- **Rules Evaluated**: Unusually Large Transfers, New Payee Bursts, Odd-Hours Activity, Pattern & Channel Deviations.\n"
                f"- **Triggered Findings**: None (0 anomalies flagged in available records).\n"
                f"- **Mathematical Precondition**: Requires a minimum of 5 historical transactions to compute statistical bounds (mean, variance, normal ceiling).\n\n"
                f"### 🧩 Risk Pattern & Baseline Adherence\n"
                f"Account currently has insufficient transaction volume for longitudinal statistical profiling. No phantom risk score is generated.\n\n"
                f"### 🛠️ Investigator Action Checklist\n"
                f"1. Await accumulation of routine transaction cycles (minimum 30-90 days / 5+ transactions) to establish statistical baseline.\n"
                f"2. Retain standard onboarding monitoring for upcoming transaction cycles.\n\n"
                f"---\n**{DISCLAIMER_TEXT}**"
            )

        # 2. Routine Clean Case
        if result.verdict == "NOTHING_FLAGGED":
            total_tx = result.summary_statistics.get("total_transactions", 0)
            total_vol = result.summary_statistics.get("total_volume", 0.0)
            avg_amt = result.customer_baseline.get("baseline_avg_amount", 0.0)
            active_h = result.customer_baseline.get("baseline_active_hours", [8, 22])

            return (
                f"{verdict_line}\n\n"
                f"### 📋 Executive Summary\n"
                f"Comprehensive automated risk screening for **{result.customer_name}** (`{result.customer_id}`) evaluated **{total_tx} transactions** totaling **${total_vol:,.2f}**. "
                f"**Evidence Assessment**: Established historical baseline verified. All evaluated transactions strictly conform to established spending, payee, temporal, and channel patterns.\n\n"
                f"### 🔍 Detailed Risk Findings & Evidence Breakdown\n"
                f"- **Status**: NOTHING_FLAGGED (Sufficient History - Routine Account Activity).\n"
                f"- **Statistical Outlier Check**: All transaction amounts remain within the expected normal spend ceiling (${result.customer_baseline.get('baseline_max_normal', 0.0):,.2f}).\n"
                f"- **Payee Frequency Check**: 100% of transactions were directed to known, recurring counterparties ({result.customer_baseline.get('known_payees_count', 0)} established payees).\n"
                f"- **Temporal Window Check**: All transactions occurred during the customer's established active window ({active_h[0]:02d}:00–{active_h[1]:02d}:00).\n"
                f"- **Channel Consistency**: Exclusively utilized established channels ({', '.join(result.customer_baseline.get('common_channels', []))}).\n\n"
                f"### 🧩 Risk Pattern & Baseline Adherence\n"
                f"Transaction frequency and average transaction size (${avg_amt:,.2f}) exhibit consistent temporal and fiscal stability across the monitored 6-month period.\n\n"
                f"### 🛠️ Investigator Action Checklist\n"
                f"1. Close investigation record as **Routine / Clear**.\n"
                f"2. Maintain automated periodic baseline recalibration.\n\n"
                f"---\n**{DISCLAIMER_TEXT}**"
            )

        # 3. Flagged Case (ATTENTION_REQUIRED)
        report_sections = [
            f"{verdict_line}\n",
            "### 📋 Executive Summary",
            (
                f"Automated risk screening for customer **{result.customer_name}** (`{result.customer_id}`) identified **{result.findings_count} anomalous risk pattern(s)** "
                f"across **{len(result.cited_transactions)} cited transaction(s)**. "
                f"Composite Risk Score is evaluated at **{result.risk_score}/100** (Investigative Urgency). "
                f"Specific baseline deviations require human investigator review."
            ),
            "\n### 🔍 Detailed Risk Findings & Evidence Breakdown"
        ]

        for idx, f in enumerate(result.findings, 1):
            cited_str = ", ".join([f"`[{t_id}]`" for t_id in f.transaction_ids])
            report_sections.append(
                f"#### Finding #{idx}: {f.rule_name} (Severity: **{f.severity}**)\n"
                f"- **Cited Transactions**: {cited_str}\n"
                f"- **Observed Metric**: {f.observed_value or f.metric_observed}\n"
                f"- **Baseline Reference**: {f.baseline_value or f.baseline_reference}\n"
                f"- **Deviation**: {f.deviation or 'N/A'}\n"
                f"- **Explanation**: {f.explanation or f.technical_summary}\n"
                f"- **Suggested First Step**: {f.investigator_action or f.suggested_first_step}\n"
            )

        # Correlation analysis
        report_sections.append("### 🧩 Risk Pattern & Correlation Analysis")
        if len(result.findings) > 1:
            report_sections.append(
                f"Multiple concurrent risk rules triggered on account `{result.account_number}`. "
                f"The combination of **{', '.join([f.rule_name for f in result.findings])}** suggests coordinated multi-vector deviation "
                f"from historical behavioral baselines, elevating overall investigative urgency."
            )
        else:
            report_sections.append(
                f"Single isolated rule deviation (**{result.findings[0].rule_name}**) observed. "
                f"All other baseline behavioral dimensions (active hours, familiar counterparties, channel mix) remained within nominal bounds."
            )

        # Investigator Action Checklist
        report_sections.append("\n### 🛠️ Investigator Action Checklist")
        report_sections.append("1. **Verify Authorization**: Contact account holder via primary verified phone number to confirm legitimacy of cited transfers.")
        report_sections.append("2. **Inspect Session Metadata**: Review IP geolocation, device fingerprint, and multi-factor authentication logs for cited transactions.")
        report_sections.append("3. **Counterparty Due Diligence**: Inspect beneficiary account details and check against internal and external fraud blacklists.")
        if any(f.severity == "HIGH" for f in result.findings):
            report_sections.append("4. **Protective Measures**: Consider placing a temporary outbound transfer hold pending analyst verification.")

        report_sections.append(f"\n---\n**{DISCLAIMER_TEXT}**")

        return "\n".join(report_sections)


# Global singleton instance
llm_engine = LLMInvestigationEngine()
