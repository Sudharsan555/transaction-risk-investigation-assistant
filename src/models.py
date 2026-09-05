from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


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
    baseline_std_amount: float
    baseline_max_normal: float
    baseline_active_hours: List[int] = Field(default_factory=lambda: [8, 22])  # [start_hour, end_hour]
    known_payees: List[str] = Field(default_factory=list)
    common_channels: List[str] = Field(default_factory=lambda: ["Mobile", "POS", "Web"])
    total_transactions: int = 0
    total_volume: float = 0.0


class RiskFinding(BaseModel):
    rule_id: str
    rule_name: str
    severity: str  # HIGH, MEDIUM, LOW
    cited_transaction_ids: List[str]
    metric_observed: str
    baseline_reference: str
    technical_summary: str
    suggested_first_step: str


class InvestigationResult(BaseModel):
    customer_id: str
    customer_name: str
    account_type: str
    account_number: str
    verdict: str  # "ATTENTION NEEDED" or "NOTHING FLAGGED"
    evidence_status: str = "SUFFICIENT_HISTORY"  # "SUFFICIENT_HISTORY" or "INSUFFICIENT_EVIDENCE"
    risk_score: int  # 0 to 100
    findings_count: int
    findings: List[RiskFinding] = Field(default_factory=list)
    cited_transactions: List[Transaction] = Field(default_factory=list)
    customer_baseline: Dict[str, Any] = Field(default_factory=dict)
    summary_statistics: Dict[str, Any] = Field(default_factory=dict)
    llm_report: Optional[str] = None
    llm_model_used: Optional[str] = None
    fallback_used: bool = False


class CustomAnalysisRequest(BaseModel):
    customer_profile: Optional[CustomerProfile] = None
    transactions: List[Dict[str, Any]]
