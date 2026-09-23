"""Deterministic fraud policy engine: rules R1-R10 plus policy sections 3a and 4.

The LLM never picks actions. Every action carries {"action", "route", "reason"}
where reason cites the policy rule (e.g. "R5: ..."). Routes follow policy
section 2 exactly. Actions are ordered by execution order (policy section 1).
"""
from typing import Any, Dict, List, Tuple

ACTIONS = [
    "ALLOW_TRANSACTION", "DECLINE_TRANSACTION", "MONITOR_CARD",
    "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER",
    "STEP_UP_AUTH", "BLOCK_CARD", "BLOCK_ALL_CARDS", "GENERATE_REPORT",
    "CREATE_CASE", "FILE_REPORT", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD",
]

ACTION_ORDER = {name: i for i, name in enumerate([
    "ALLOW_TRANSACTION", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH",
    "WARN_CUSTOMER", "MONITOR_CARD", "MONITOR_CONNECTED_CARDS",
    "DECLINE_TRANSACTION", "BLOCK_CARD", "BLOCK_ALL_CARDS", "CREATE_CASE",
    "GENERATE_REPORT", "FILE_REPORT", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD",
])}

AUTO_ACTIONS = {
    "ALLOW_TRANSACTION", "MONITOR_CARD", "MONITOR_CONNECTED_CARDS",
    "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH",
    "GENERATE_REPORT", "CREATE_CASE", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD",
}

_ROUTE_SEVERITY = {"auto": 0, "L1": 1, "L2": 2}

CASE_PROBABILITY_THRESHOLD = 0.30
VERIFY_BEFORE_BLOCK_PROBABILITY = 0.70
REPORT_EXPOSURE_THRESHOLD = 1000.0
MONITOR_EXPOSURE_THRESHOLD = 2500.0
ESCALATE_EXPOSURE_THRESHOLD = 500.0
CARD_TESTING_CLEARED_THRESHOLD = 100.0

FRAUD_LIKE_PATTERNS = {
    "card_testing", "card_not_present_fraud", "card_not_present_new_device",
    "out_of_region_use", "account_takeover", "undocumented",
}


def _amt(value: Any) -> float:
    try:
        return abs(float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def _route(action: str, exposure: float) -> str:
    if action == "BLOCK_CARD":
        return "L1" if exposure <= MONITOR_EXPOSURE_THRESHOLD else "L2"
    if action in ("BLOCK_ALL_CARDS", "FILE_REPORT"):
        return "L2"
    if action == "DECLINE_TRANSACTION":
        return "L1"
    if action in AUTO_ACTIONS:
        return "auto"
    return "L1"


def _graph_signals(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [e for e in evidence or [] if e.get("source") in ("graph", "customer", "external")]


def _testing_cleared(state: Dict[str, Any]) -> bool:
    if state.get("pattern") != "card_testing":
        return False
    return any(_amt(t.get("amount", t.get("TransactionAmt", 0))) > CARD_TESTING_CLEARED_THRESHOLD
               for t in state.get("related_txns") or [])


def _evidence_conflicts(state: Dict[str, Any]) -> bool:
    """A customer verification was left unanswered while suspicion stays moderate."""
    fp = float(state.get("fraud_probability", 0.0) or 0.0)
    return state.get("customer_response") == "no_reply" and fp >= 0.50


def _add(actions: Dict[str, Tuple[str, str]], action: str, reason: str, exposure: float) -> None:
    severity = _ROUTE_SEVERITY[_route(action, exposure)]
    existing = actions.get(action)
    if existing is None:
        actions[action] = (reason, severity)
        return
    old_reason, old_severity = existing
    if severity > old_severity:
        actions[action] = (reason, severity)


def _finalize(state: Dict[str, Any], actions: Dict[str, Tuple[str, str]]) -> List[Dict[str, Any]]:
    finalized = []
    for name in sorted(actions, key=lambda a: ACTION_ORDER[a]):
        reason, severity = actions[name]
        route = next(r for r, s in _ROUTE_SEVERITY.items() if s == severity)
        finalized.append({"action": name, "route": route, "reason": reason})
    return _drop_forbidden_blocks(state, finalized)


def _drop_forbidden_blocks(state: Dict[str, Any], actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    confirmed = int(state.get("confirmed_compromised_card_count", 0) or 0)
    if confirmed >= 2:
        return actions
    return [a for a in actions if a["action"] != "BLOCK_ALL_CARDS"]


def apply_policy(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate R1-R10 + section 3a against the current state.

    Returns {"final_actions": [...], "initial_actions": [...], "sar_required": bool,
    "sar_reason": str}. initial_actions echoes whatever the caller already recorded;
    the graph stores the pre-evidence recommendation itself.
    """
    verdict = str(state.get("verdict", "uncertain")).lower()
    fp = float(state.get("fraud_probability", 0.0) or 0.0)
    pattern = state.get("pattern", "none")
    exposure = _amt(state.get("exposure_usd", 0.0))
    customer_response = state.get("customer_response") or ""
    trigger = state.get("trigger_type") or ""
    signals = _graph_signals(state.get("evidence") or [])
    single_signal = len(signals) <= 1
    shared_origin = bool(state.get("connected_device_profiles"))
    coordination = float((state.get("jev_classification") or {}).get("coordination", 0) or 0.0)
    if customer_response == "confirmed":
        verdict = "legitimate"

    actions: Dict[str, Tuple[str, str]] = {}

    case_required = fp >= CASE_PROBABILITY_THRESHOLD or int(state.get("evidence_request_count", 0) or 0) >= 1

    if verdict == "legitimate":
        if trigger == "customer_report":
            _add(actions, "CREATE_CASE", "R7: disputed charge matches the customer's own recurring pattern", exposure)
            if customer_response != "confirmed":
                _add(actions, "VERIFY_WITH_CUSTOMER", "R7: confirm the recurring charge with the customer", exposure)
            _add(actions, "WARN_CUSTOMER", "R7: recurring-charge reminder for the disputed amount", exposure)
            _add(actions, "CLOSE_NO_FRAUD", "R3: no fraud evidence after review", exposure)
        else:
            _add(actions, "ALLOW_TRANSACTION", "R1: activity is consistent with the cardholder's history", exposure)
            _add(actions, "GENERATE_REPORT", "R3a: no case required, investigation recorded internally", exposure)
            _add(actions, "CLOSE_NO_FRAUD", "R3: no fraud evidence after review", exposure)
    elif verdict == "fraud" or fp >= 0.70:
        if customer_response == "denied":
            _add(actions, "BLOCK_CARD", f"R2: customer denied the transaction; exposure ${exposure:,.2f}", exposure)
            _add(actions, "CREATE_CASE", "R2: customer denial confirms unauthorized use", exposure)
        elif pattern == "card_testing":
            _add(actions, "DECLINE_TRANSACTION", "R5: card testing sequence observed on this card", exposure)
            _add(actions, "STEP_UP_AUTH", "R5: require step-up authentication before further activity", exposure)
            if _testing_cleared(state):
                _add(actions, "BLOCK_CARD", "R5: a purchase over $100 has already cleared", exposure)
        else:
            _add(actions, "BLOCK_CARD", f"R2: fraud confirmed at probability {fp:.2f}; exposure ${exposure:,.2f}", exposure)
            _add(actions, "CREATE_CASE", "R2: strong evidence of unauthorized use", exposure)
    else:
        if single_signal or fp < 0.70:
            _add(actions, "VERIFY_WITH_CUSTOMER",
                 f"R1: case rests on {'a single signal' if single_signal else 'weak signals'} at probability {fp:.2f}, verify before any block", exposure)
        else:
            _add(actions, "STEP_UP_AUTH", f"R1: strong suspicion at probability {fp:.2f}, require step-up before further activity", exposure)
        _add(actions, "MONITOR_CARD", "R1: card stays active under monitoring pending verification", exposure)

    if customer_response == "no_reply" and state.get("verdict") != "fraud":
        _add(actions, "MONITOR_CARD", "R4: no reply within 24 hours, card stays under monitoring", exposure)
        _add(actions, "DECLINE_TRANSACTION", "R4: pending authorizations declined until verified", exposure)
        if exposure > ESCALATE_EXPOSURE_THRESHOLD:
            _add(actions, "ESCALATE_TO_ANALYST", f"R4: exposure ${exposure:,.2f} exceeds $500 without a customer reply", exposure)

    if shared_origin:
        _add(actions, "CREATE_CASE", "R6: several cards show fraud from the same device profile", exposure)
        _add(actions, "FILE_REPORT", "R6: shared device profile links multiple cards' fraud", exposure)
        _add(actions, "MONITOR_CONNECTED_CARDS", "R6: every card sharing the device goes under monitoring", exposure)

    if pattern == "undocumented" and (coordination >= 0.5 or shared_origin):
        _add(actions, "CREATE_CASE", "R9: undocumented coordinated pattern across customers", exposure)
        _add(actions, "FILE_REPORT", "R9: undocumented coordinated pattern", exposure)
        _add(actions, "ESCALATE_TO_ANALYST", "R9: undocumented pattern needs analyst review", exposure)

    if verdict == "uncertain" and (exposure > ESCALATE_EXPOSURE_THRESHOLD or _evidence_conflicts(state)):
        _add(actions, "ESCALATE_TO_ANALYST",
             f"R8: uncertain verdict with exposure ${exposure:,.2f} and unresolved evidence", exposure)

    if case_required or trigger == "customer_report":
        _add(actions, "CREATE_CASE", "R3a: fraud probability 0.30 reached" if fp >= CASE_PROBABILITY_THRESHOLD
             else ("R3a: evidence was requested" if int(state.get("evidence_request_count", 0) or 0) >= 1
                   else "R3a: customer dispute recorded"), exposure)

    suspicion = verdict == "fraud" or (fp >= 0.70 and customer_response != "confirmed")
    if suspicion and (exposure > 1000.0 or shared_origin or pattern == "undocumented"):
        _add(actions, "FILE_REPORT",
             f"R3a: strong suspicion with exposure ${exposure:,.2f}" if exposure > 1000.0
             else ("R3a: shared device/other-card fraud connection" if shared_origin
                   else "R3a: undocumented or coordinated pattern"), exposure)

    final_actions = _finalize(state, actions)
    sar_required = any(a["action"] == "FILE_REPORT" for a in final_actions)
    sar_reason = next((a["reason"] for a in final_actions if a["action"] == "FILE_REPORT"), "")
    return {
        "final_actions": final_actions,
        "initial_actions": state.get("initial_actions", []),
        "sar_required": sar_required,
        "sar_reason": sar_reason,
    }