import math
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


def _check_valid_timestamp(dt_str: str) -> bool:
    if not dt_str or not isinstance(dt_str, str):
        return False
    dt_str = dt_str.strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            datetime.strptime(dt_str, fmt)
            return True
        except ValueError:
            continue
    return False


class Transaction(BaseModel):
    transaction_id: str
    customer_id: Optional[str] = "CUSTOM-001"
    timestamp: str  # ISO format YYYY-MM-DDTHH:MM:SS
    description: Optional[str] = "Transaction"
    payee: str
    amount: float
    channel: Optional[str] = "Web"  # Mobile, Web, POS, ATM, Wire
    category: Optional[str] = "General"
    is_flagged: bool = False
    flag_reasons: List[str] = Field(default_factory=list)

    @field_validator("amount")
    @classmethod
    def validate_positive_amount(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError(f"Transaction amount must be strictly positive (> 0), got: {v}")
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"Transaction amount cannot be NaN or Infinite, got: {v}")
        return round(float(v), 2)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_format(cls, v: str) -> str:
        if not v or not _check_valid_timestamp(v):
            raise ValueError(f"Invalid timestamp '{v}'. Expected ISO-8601 string (e.g. YYYY-MM-DDTHH:MM:SS).")
        return v.strip()

    @field_validator("transaction_id", "payee")
    @classmethod
    def validate_required_non_empty(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return str(v).strip()

    @field_validator("channel")
    @classmethod
    def validate_channel_non_empty(cls, v: Optional[str]) -> str:
        if v is not None and not str(v).strip():
            raise ValueError("Channel cannot be empty or whitespace.")
        return str(v).strip() if v else "Web"


class CustomerProfile(BaseModel):
    customer_id: str
    name: str = "Unknown Customer"
    account_type: str = "Standard Checking"  # Personal Checking, Small Business, High Net Worth, Student
    account_number: str = "ACC-00000000"
    baseline_avg_amount: float = 0.0
    baseline_median_amount: float = 0.0
    baseline_std_amount: float = 0.0
    baseline_max_normal: float = 0.0
    baseline_amount_range: List[float] = Field(default_factory=lambda: [0.0, 0.0])
    baseline_active_hours: List[int] = Field(default_factory=lambda: [8, 22])  # [start_hour, end_hour]
    known_payees: List[str] = Field(default_factory=list)
    common_channels: List[str] = Field(default_factory=lambda: ["Mobile", "POS", "Web"])
    common_categories: List[str] = Field(default_factory=list)
    baseline_frequency_per_month: float = 0.0
    total_transactions: int = 0
    total_volume: float = 0.0
    baseline_transaction_count: int = 0
    baseline_transaction_ids: List[str] = Field(default_factory=list)
    excluded_transaction_ids: List[str] = Field(default_factory=list)
    is_sufficient: bool = False
    provenance: str = "HISTORICAL_TRANSACTIONS_ONLY"


class RiskFinding(BaseModel):
    rule_id: str
    rule_name: str
    severity: str  # HIGH, MEDIUM, LOW
    cited_transaction_ids: List[str]
    transaction_ids: List[str] = Field(default_factory=list)
    metric_observed: str
    observed_value: str = ""
    baseline_reference: str
    baseline_value: str = ""
    deviation: str = ""
    technical_summary: str
    explanation: str = ""
    suggested_first_step: str
    investigator_action: str = ""

    @model_validator(mode="before")
    @classmethod
    def sync_finding_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Sync transaction_ids
            cited = values.get("cited_transaction_ids") or []
            tx_ids = values.get("transaction_ids") or cited
            values["cited_transaction_ids"] = cited or tx_ids
            values["transaction_ids"] = tx_ids

            # Sync observed
            obs = values.get("observed_value") or values.get("metric_observed") or ""
            values["metric_observed"] = values.get("metric_observed") or obs
            values["observed_value"] = obs

            # Sync baseline
            base = values.get("baseline_value") or values.get("baseline_reference") or ""
            values["baseline_reference"] = values.get("baseline_reference") or base
            values["baseline_value"] = base

            # Sync explanation
            exp = values.get("explanation") or values.get("technical_summary") or ""
            values["technical_summary"] = values.get("technical_summary") or exp
            values["explanation"] = exp

            # Sync action
            act = values.get("investigator_action") or values.get("suggested_first_step") or ""
            values["suggested_first_step"] = values.get("suggested_first_step") or act
            values["investigator_action"] = act

            if not values.get("deviation"):
                values["deviation"] = obs
        return values


class InvestigationResult(BaseModel):
    customer_id: str
    customer_name: str
    account_type: str
    account_number: str
    verdict: str  # "ATTENTION_REQUIRED", "NOTHING_FLAGGED", or "INSUFFICIENT_EVIDENCE"
    evidence_status: str = "SUFFICIENT_HISTORY"  # "SUFFICIENT_HISTORY" or "INSUFFICIENT_EVIDENCE"
    risk_score: int  # 0 to 100
    findings_count: int
    findings: List[RiskFinding] = Field(default_factory=list)
    cited_transactions: List[Transaction] = Field(default_factory=list)
    customer_baseline: Dict[str, Any] = Field(default_factory=dict)
    summary_statistics: Dict[str, Any] = Field(default_factory=dict)
    risk_score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    citation_validation: Dict[str, Any] = Field(default_factory=dict)
    llm_report: Optional[str] = None
    llm_model_used: Optional[str] = None
    fallback_used: bool = False


class CustomAnalysisRequest(BaseModel):
    customer_profile: Optional[CustomerProfile] = None
    historical_transactions: List[Transaction] = Field(default_factory=list)
    observed_transactions: List[Transaction] = Field(default_factory=list)
    transactions: Optional[List[Transaction]] = None  # Legacy backward compatibility

    @model_validator(mode="after")
    def validate_custom_payload(self) -> "CustomAnalysisRequest":
        all_txns = list(self.historical_transactions) + list(self.observed_transactions)
        if self.transactions:
            all_txns.extend(self.transactions)

        seen_ids = set()
        customer_ids = set()
        for t in all_txns:
            if t.transaction_id in seen_ids:
                raise ValueError(
                    f"Duplicate transaction ID detected: '{t.transaction_id}'. "
                    f"All transaction IDs within a single payload must be unique."
                )
            seen_ids.add(t.transaction_id)
            if t.customer_id and str(t.customer_id).strip():
                customer_ids.add(str(t.customer_id).strip())

        if len(customer_ids) > 1:
            raise ValueError(
                f"Mixed customer IDs detected in transaction payload: {sorted(list(customer_ids))}. "
                f"All transactions in a single analysis request must belong to the same customer account."
            )

        return self
