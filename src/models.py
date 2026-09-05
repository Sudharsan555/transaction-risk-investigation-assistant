from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator


class Transaction(BaseModel):
    transaction_id: str
    customer_id: str
    timestamp: str  # ISO format YYYY-MM-DDTHH:MM:SS
    description: str
    payee: str
    amount: float
    channel: str  # Mobile, Web, POS, ATM, Wire
    category: Optional[str] = "General"
    is_flagged: bool = False
    flag_reasons: List[str] = Field(default_factory=list)


class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    account_type: str  # Personal Checking, Small Business, High Net Worth, Student
    account_number: str
    baseline_avg_amount: float
    baseline_median_amount: float = 0.0
    baseline_std_amount: float
    baseline_max_normal: float
    baseline_amount_range: List[float] = Field(default_factory=lambda: [0.0, 0.0])
    baseline_active_hours: List[int] = Field(default_factory=lambda: [8, 22])  # [start_hour, end_hour]
    known_payees: List[str] = Field(default_factory=list)
    common_channels: List[str] = Field(default_factory=lambda: ["Mobile", "POS", "Web"])
    common_categories: List[str] = Field(default_factory=list)
    baseline_frequency_per_month: float = 0.0
    total_transactions: int = 0
    total_volume: float = 0.0


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
    transactions: List[Dict[str, Any]]
