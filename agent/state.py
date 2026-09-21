from typing import TypedDict, Optional, List, Dict, Any

class InvestigationState(TypedDict):
    # Input
    case_id: str
    case_data: Dict[str, Any]       # from case_pack.csv row
    trigger_type: str               # risk_score | customer_report | analyst_request

    # Transaction & entity context
    flagged_txn: Dict[str, Any]     # full transaction record
    customer_history: List[Dict[str, Any]]
    card_history: List[Dict[str, Any]]
    device_profile: Optional[Dict[str, Any]]
    related_cards: List[str]
    related_txns: List[Dict[str, Any]]

    # Graph investigation results
    graph_evidence: List[Dict[str, Any]]
    connected_device_profiles: List[str]
    connected_card_ids: List[str]
    billing_regions: List[Dict[str, Any]]
    email_domains: List[Dict[str, Any]]

    # Historical memory
    similar_prior_cases: List[Dict[str, Any]]

    # Assessment
    jev_classification: Dict[str, Any]
    fraud_probability: float
    pattern: str
    pattern_description: str
    verdict: str                    # fraud | legitimate | uncertain
    affected_txn_ids: List[str]
    first_suspicious_txn_id: str
    exposure_usd: float

    # Evidence requests
    evidence_requests: List[Dict[str, Any]]
    evidence_request_count: int
    assumed_responses: List[Dict[str, Any]]

    # Actions
    initial_actions: List[Dict[str, Any]]
    final_actions: List[Dict[str, Any]]
    what_changed: str

    # SAR
    sar_required: bool
    sar_narrative: str
    sar_subjects: List[str]

    # Evidence list for output
    evidence: List[Dict[str, Any]]

    # Metadata
    stop_reason: str
    tool_calls: int
    tokens: int
    investigation_step: int
    summary: str
