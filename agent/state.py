from typing import TypedDict, Optional, List, Dict, Any


class InvestigationState(TypedDict, total=False):
    # Input
    case_id: str
    case_data: Dict[str, Any]       # case_pack.csv row (+ TransactionID)
    trigger_type: str               # risk_score | customer_report | analyst_request

    # Transaction & entity context
    flagged_txn: Dict[str, Any]
    related_txns: List[Dict[str, Any]]

    # Graph investigation results
    connected_card_ids: List[str]
    connected_device_profiles: List[str]

    # Historical memory
    similar_prior_cases: List[Dict[str, Any]]

    # Assessment
    jev_classification: Dict[str, Any]
    confidence_drivers: List[str]
    fraud_probability: float
    pattern: str
    pattern_description: str
    verdict: str                    # fraud | legitimate | uncertain
    affected_txn_ids: List[str]
    first_suspicious_txn_id: str
    exposure_usd: float

    # Evidence
    evidence: List[Dict[str, Any]]  # [{"claim","source","ref","entity_ids"}]
    evidence_requests: List[Dict[str, Any]]  # [{"type","asked_after_step","assumed_response"}]
    evidence_request_count: int
    customer_response: str          # "" | denied | confirmed | no_reply

    # Actions
    initial_actions: List[Dict[str, Any]]
    final_actions: List[Dict[str, Any]]
    what_changed: str

    # SAR
    sar_required: bool
    sar_reason: str
    sar_narrative: str
    sar_subjects: List[str]

    # Retrieval context
    rag_context: List[Dict[str, Any]]

    # Outputs
    summary: str
    stop_reason: str
    written_to_graph: bool
    graph_case_id: str

    # Graph visualization data for frontend
    graph_nodes: List[Dict[str, Any]]
    graph_edges: List[Dict[str, Any]]

    # Metadata
    tool_calls: int
    tokens: int
    llm_ok: bool                    # False when the LLM call failed (fallback assessment used)
    latency_s: float
    step: int