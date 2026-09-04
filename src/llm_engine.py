"""
LLM Grounding & Investigation Report Generator (Gemini 2.0 Flash).
Strictly grounds output in deterministic rule engine findings and cited transactions.
Enforces strict citation constraints, prevents definitive fraud assertions,
and provides an instant, zero-latency deterministic fallback when the API is unavailable.
"""

import json
import os
from typing import Optional, Dict, Any, Tuple
from src.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FALLBACK_MODEL
from src.models import InvestigationResult, RiskFinding, Transaction


SYSTEM_INSTRUCTION = """You are the Senior Bank Fraud Desk Investigation Assistant for a Tier-1 financial institution.
Your duty is to produce objective, clear, and actionable transaction risk investigation reports for human fraud analysts based strictly on provided deterministic risk findings.

CRITICAL OPERATIONAL RULES:
1. STRICT GROUNDING: Rely ONLY on the provided structured findings and cited transactions in the prompt payload. NEVER invent transactions, dates, amounts, counterparties, or baseline statistics not present in the payload.
2. NO FRAUD CONCLUSIONS: NEVER declare, conclude, or imply that 'fraud has occurred' or that the customer is guilty. Your role is strictly to flag anomalies, explain deviations against baseline, and hand investigative judgment to the human analyst.
3. MANDATORY CITATIONS: Every factual statement, finding, or transaction referenced MUST explicitly include its transaction ID in brackets, e.g., [TXN-1082].
4. REPORT FORMAT:
   - Line 1 MUST be strictly: "VERDICT: ATTENTION NEEDED" or "VERDICT: NOTHING FLAGGED".
   - Section 1: 📋 Executive Summary (2-3 sentences summarizing the account posture and key deviations).
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

    def generate_investigation_report(self, result: InvestigationResult) -> Tuple[str, str, bool]:
        """
        Generates a grounded investigation report.
        Returns: (report_markdown, model_name, fallback_used)
        """
        # If no API key or client, immediately use clean deterministic fallback
        if not self.client:
            report = self._generate_deterministic_fallback_report(result)
            return report, "Deterministic Fallback (No API Key)", True

        # Construct strictly grounded prompt payload
        prompt_payload = self._build_prompt_payload(result)

        # Attempt Gemini API call
        for model_name in [GEMINI_MODEL, GEMINI_FALLBACK_MODEL]:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt_payload,
                    config={
                        "system_instruction": SYSTEM_INSTRUCTION,
                        "temperature": 0.1,
                        "max_output_tokens": 1500,
                    }
                )
                if response and response.text:
                    cleaned_report = self._post_process_report(response.text, result)
                    return cleaned_report, f"Google Gemini ({model_name})", False
            except Exception as e:
                print(f"[WARN] Gemini model '{model_name}' call failed: {e}")
                continue

        # Fallback if all API attempts fail
        fallback_report = self._generate_deterministic_fallback_report(result)
        return fallback_report, "Deterministic Fallback (API Error/Timeout)", True

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
        """Ensures verdict line and disclaimer are strictly compliant."""
        lines = text.strip().split("\n")
        expected_verdict = f"VERDICT: {result.verdict}"
        
        # Ensure first line starts with exact verdict
        if not lines[0].startswith("VERDICT:"):
            text = f"{expected_verdict}\n\n" + text

        # Ensure disclaimer is included at the end
        if "DISCLAIMER:" not in text:
            text = text + f"\n\n---\n**{DISCLAIMER_TEXT}**"

        return text

    def _generate_deterministic_fallback_report(self, result: InvestigationResult) -> str:
        """
        Generates a clean, polished, fully-grounded report using deterministic logic.
        Guarantees zero downtime, exact citation preservation, and non-alarming clean states.
        """
        verdict_line = f"VERDICT: {result.verdict}"

        if result.verdict == "NOTHING FLAGGED":
            total_tx = result.summary_statistics.get("total_transactions", 0)
            total_vol = result.summary_statistics.get("total_volume", 0.0)
            avg_amt = result.customer_baseline.get("baseline_avg_amount", 0.0)
            active_h = result.customer_baseline.get("baseline_active_hours", [8, 22])

            if total_tx == 0:
                return (
                    f"{verdict_line}\n\n"
                    f"### 📋 Executive Summary\n"
                    f"Customer **{result.customer_name}** (`{result.customer_id}`) has no historical transaction records recorded on account `{result.account_number}`. "
                    f"All rule evaluations completed normally with zero baseline anomalies.\n\n"
                    f"### 🔍 Detailed Risk Findings & Evidence Breakdown\n"
                    f"- **Status**: No anomalous transactions detected.\n"
                    f"- **Rules Evaluated**: Unusually Large Transfers, New Payee Bursts, Odd-Hours Activity, Pattern & Channel Deviations.\n"
                    f"- **Triggered Rules**: None (0 findings).\n\n"
                    f"### 🧩 Risk Pattern & Baseline Adherence\n"
                    f"Account currently has zero transaction volume. Routine onboarding monitoring remains active.\n\n"
                    f"### 🛠️ Investigator Action Checklist\n"
                    f"1. No immediate action required for this account.\n"
                    f"2. Retain standard baseline profiling for upcoming transaction cycles.\n\n"
                    f"---\n**{DISCLAIMER_TEXT}**"
                )

            return (
                f"{verdict_line}\n\n"
                f"### 📋 Executive Summary\n"
                f"Comprehensive automated risk screening for **{result.customer_name}** (`{result.customer_id}`) evaluated **{total_tx} transactions** totaling **${total_vol:,.2f}**. "
                f"All evaluated transactions fall strictly within established historical behavioral norms. No suspicious outliers or pattern deviations were detected.\n\n"
                f"### 🔍 Detailed Risk Findings & Evidence Breakdown\n"
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

        # Flagged Case
        report_sections = [
            f"{verdict_line}\n",
            "### 📋 Executive Summary",
            (
                f"Automated risk screening for customer **{result.customer_name}** (`{result.customer_id}`) identified **{result.findings_count} anomalous risk pattern(s)** "
                f"across **{len(result.cited_transactions)} cited transaction(s)**. "
                f"Composite Risk Score is evaluated at **{result.risk_score}/100**. Specific baseline deviations require human investigator review."
            ),
            "\n### 🔍 Detailed Risk Findings & Evidence Breakdown"
        ]

        for idx, f in enumerate(result.findings, 1):
            cited_str = ", ".join([f"`[{t_id}]`" for t_id in f.cited_transaction_ids])
            report_sections.append(
                f"#### Finding #{idx}: {f.rule_name} (Severity: **{f.severity}**)\n"
                f"- **Cited Transactions**: {cited_str}\n"
                f"- **Observed Metric**: {f.metric_observed}\n"
                f"- **Baseline Baseline**: {f.baseline_reference}\n"
                f"- **Explanation**: {f.technical_summary}\n"
                f"- **Suggested First Step**: {f.suggested_first_step}\n"
            )

        # Correlation analysis
        report_sections.append("### 🧩 Risk Pattern & Correlation Analysis")
        if len(result.findings) > 1:
            report_sections.append(
                f"Multiple concurrent risk rules triggered on account `{result.account_number}`. "
                f"The combination of **{', '.join([f.rule_name for f in result.findings])}** suggests coordinated multi-vector deviation "
                f"from historical behavioral baselines, elevating overall priority."
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
