"""Jev (TypeSafe System One) fast decision layer with deterministic fallback.

Real calls via typesafe-sdk: pattern classification (Choice), evidence sufficiency
(Noul), coordination detection (Noul). If JEV_API_KEY is missing or a call fails,
the deterministic graph heuristics below are used instead and results are marked
``engine: "heuristic"``. Jev confidence is a signal only — never the verdict.
"""
import json
import os
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from typesafe_sdk import Choice, Noul, TypeSafeClient
    _SDK_OK = True
except Exception:
    _SDK_OK = False

PATTERN_IDS = [
    "card_testing",
    "card_not_present_fraud",
    "card_not_present_new_device",
    "out_of_region_use",
    "account_takeover",
    "undocumented",
    "none",
]

PATTERN_LABELS = {
    "card_testing": "Card Testing",
    "card_not_present_fraud": "Card-Not-Present Fraud",
    "card_not_present_new_device": "Card-Not-Present New Device",
    "out_of_region_use": "Out-of-Region Use",
    "account_takeover": "Account Takeover",
    "undocumented": "Undocumented Pattern",
    "none": "No Known Pattern",
}

PATTERN_CRITERIA = {
    "card_testing": "3+ small online authorizations on one card within an hour, followed by a larger purchase.",
    "card_not_present_fraud": "Online purchases without the physical card; amounts and merchants inconsistent with cardholder history, often in a short burst.",
    "card_not_present_new_device": "Card-not-present purchases from a device never seen on the account, sometimes behind a proxy.",
    "out_of_region_use": "Purchases in a billing region where the cardholder has no history, while normal activity continues at home.",
    "account_takeover": "Credential or device change followed by value extraction; mixed-channel activity inconsistent with the cardholder.",
    "undocumented": "Coordinated or repeated abuse across cards or customers that fits none of the known patterns.",
    "none": "Evidence does not support any known fraud pattern.",
}

_client: Optional[Any] = None
_client_failed = False
_jev_dead = False


def _get_client() -> Optional[Any]:
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed or _jev_dead or not _SDK_OK:
        return None
    api_key = os.environ.get("JEV_API_KEY", "")
    if not api_key:
        _client_failed = True
        return None
    try:
        _client = TypeSafeClient(api_key=api_key)
        return _client
    except Exception:
        _client_failed = True
        return None


# ---------------------------------------------------------------------------
# Deterministic heuristic fallback (graph-derived, no API)
# ---------------------------------------------------------------------------
def _txn_amount(t: dict) -> float:
    try:
        return float(t.get("amount", t.get("amt", t.get("TransactionAmt", 0))) or 0)
    except (TypeError, ValueError):
        return 0.0


def _history_stats(history: list) -> dict:
    amounts = [_txn_amount(t) for t in history or []]
    return {
        "txn_count": len(amounts),
        "small_txn_count": sum(1 for a in amounts if a < 5),
        "large_txn_count": sum(1 for a in amounts if a > 500),
        "sample_amounts": amounts[:10],
    }


def _heuristic_pattern(txn_data: dict, history: list) -> tuple:
    amount = _txn_amount(txn_data)
    risk_score = float(txn_data.get("risk_score", 0) or 0)
    product_cd = txn_data.get("ProductCD", txn_data.get("product_cd", ""))
    dist1 = float(txn_data.get("dist1", 0) or 0)
    stats = _history_stats(history)
    small, large, hist_count = stats["small_txn_count"], stats["large_txn_count"], stats["txn_count"]

    if small >= 3 and amount < 10:
        return "card_testing", 0.88
    if risk_score > 0.7 and dist1 > 50:
        return "account_takeover", 0.82
    if large >= 2 and risk_score > 0.5:
        return "undocumented", 0.75
    if hist_count > 10 and risk_score > 0.4:
        return "undocumented", 0.70
    if product_cd in ["S", "R"] and risk_score > 0.5:
        return "card_not_present_fraud", 0.65
    if risk_score > 0.6:
        return "card_not_present_fraud", 0.55
    return "none", 0.40


def _heuristic_sufficiency(evidence_summary: str, history: list) -> float:
    text = (evidence_summary or "").lower()
    signals = sum(1 for keyword in ("device", "region", "email", "case", "card") if keyword in text)
    return round(min(0.9, 0.3 + 0.2 * signals + 0.1 * min(len(history or []), 5)), 2)


def _heuristic_coordination(coordination_facts: Optional[dict]) -> float:
    facts = coordination_facts or {}
    shared = sum(
        1 for key in ("shared_devices", "shared_regions", "shared_emails", "shared_cards")
        if float(facts.get(key, 0) or 0) > 0
    )
    if shared == 0:
        return 0.2
    return round(min(0.95, 0.5 + 0.15 * shared), 2)


# ---------------------------------------------------------------------------
# Real Jev calls
# ---------------------------------------------------------------------------
def _build_state(txn_data: dict, history: list, evidence_summary: str, coordination_facts: Optional[dict]) -> str:
    state = {
        "transaction": {
            "amount": _txn_amount(txn_data),
            "risk_score": float(txn_data.get("risk_score", 0) or 0),
            "product_cd": txn_data.get("ProductCD", txn_data.get("product_cd", "")),
            "channel": txn_data.get("channel", ""),
            "dist1": txn_data.get("dist1", ""),
            "dist2": txn_data.get("dist2", ""),
        },
        "history": _history_stats(history),
        "evidence_summary": evidence_summary or "",
        "sharing": coordination_facts or {},
    }
    return json.dumps(state)


def _jev_system_one(client, state: str, questions: dict) -> Any:
    return client.system_one(state=state, questions=questions)


def _mark_dead() -> None:
    """Circuit breaker: stop retrying Jev after a failure."""
    global _jev_dead
    _jev_dead = True


def classify_pattern(txn_data: dict, history: list) -> dict:
    """Jev Choice call: which pattern best explains the evidence?"""
    client = _get_client()
    if client is None:
        return _fallback_pattern(txn_data, history)
    try:
        result = _jev_system_one(client, _build_state(txn_data, history, "", None), {
            "pattern": Choice(
                instructions="Which fraud pattern best explains this transaction and its card history?",
                criteria=PATTERN_CRITERIA,
            ),
        })
        answer = result.choices["pattern"]
        pattern = answer.choice if answer.choice in PATTERN_IDS else "none"
        return {"pattern": pattern, "confidence": answer.confidence, "probabilities": answer.probabilities}
    except Exception:
        _mark_dead()
        return _fallback_pattern(txn_data, history)


def check_sufficiency(evidence_summary: str, history: Optional[list] = None) -> float:
    """Jev Noul call: is the current evidence sufficient for a defensible decision?"""
    client = _get_client()
    if client is None:
        return _heuristic_sufficiency(evidence_summary, history or [])
    try:
        state = _build_state({}, history or [], evidence_summary, None)
        result = _jev_system_one(client, state, {
            "sufficient": Noul(
                instructions=(
                    "Is the current evidence sufficient to make a defensible fraud "
                    "decision (at least two independent signals, or a settled verification)?"
                )
            ),
        })
        return float(result.nouls["sufficient"].noul)
    except Exception:
        _mark_dead()
        return _heuristic_sufficiency(evidence_summary, history or [])


def detect_coordination(coordination_facts: Optional[dict], history: Optional[list] = None) -> float:
    """Jev Noul call: does the evidence indicate coordinated activity across cards/customers?"""
    client = _get_client()
    if client is None:
        return _heuristic_coordination(coordination_facts)
    try:
        state = _build_state({}, history or [], "", coordination_facts or {})
        result = _jev_system_one(client, state, {
            "coordinated": Noul(
                instructions=(
                    "Do the sharing facts (devices, regions, emails, connected cards) "
                    "indicate coordinated activity across multiple cards or customers?"
                )
            ),
        })
        return float(result.nouls["coordinated"].noul)
    except Exception:
        _mark_dead()
        return _heuristic_coordination(coordination_facts)


def _fallback_pattern(txn_data: dict, history: list) -> dict:
    pattern, confidence = _heuristic_pattern(txn_data, history)
    return {"pattern": pattern, "confidence": confidence, "probabilities": {}}


# ---------------------------------------------------------------------------
# Backward-compatible entry point used by agent/graph.py
# ---------------------------------------------------------------------------
def classify_fraud_pattern(
    txn_data: dict,
    history: list,
    evidence_summary: str = "",
    coordination_facts: Optional[dict] = None,
) -> dict:
    """Classify the likely fraud pattern (+ sufficiency/coordination signals).

    Signature compatible with agent/graph.py: classify_fraud_pattern(txn, history).
    Extra optional args enrich the result with sufficiency and coordination signals.
    """
    client = _get_client()
    engine = "jev" if client is not None else "heuristic"
    status = "success"
    had_client = client is not None
    try:
        if client is not None:
            state = _build_state(txn_data, history, evidence_summary, coordination_facts)
            questions = {
                "pattern": Choice(
                    instructions="Which fraud pattern best explains this transaction and its card history?",
                    criteria=PATTERN_CRITERIA,
                ),
                "sufficient": Noul(
                    instructions=(
                        "Is the current evidence sufficient to make a defensible fraud "
                        "decision (at least two independent signals, or a settled verification)?"
                    )
                ),
                "coordinated": Noul(
                    instructions=(
                        "Do the sharing facts (devices, regions, emails, connected cards) "
                        "indicate coordinated activity across multiple cards or customers?"
                    )
                ),
            }
            result = _jev_system_one(client, state, questions)
            choice = result.choices["pattern"]
            pattern = choice.choice if choice.choice in PATTERN_IDS else "none"
            sufficiency = float(result.nouls["sufficient"].noul)
            coordination = float(result.nouls["coordinated"].noul)
            probabilities = choice.probabilities
            confidence = choice.confidence
        else:
            raise RuntimeError("Jev unavailable")
    except Exception:
        _mark_dead()
        fallback = _fallback_pattern(txn_data, history)
        pattern = fallback["pattern"]
        confidence = fallback["confidence"]
        probabilities = {}
        sufficiency = _heuristic_sufficiency(evidence_summary, history)
        coordination = _heuristic_coordination(coordination_facts)
        engine = "heuristic"
        status = "error" if had_client else "success"

    return {
        "engine": engine,
        "status": status,
        "pattern": pattern,
        "pattern_label": PATTERN_LABELS.get(pattern, pattern),
        "jev_pattern": PATTERN_LABELS.get(pattern, pattern),
        "confidence": round(confidence, 3),
        "jev_confidence": round(confidence, 3),
        "probabilities": probabilities,
        "sufficiency": round(sufficiency, 3),
        "coordination": round(coordination, 3),
    }


if __name__ == "__main__":
    demo = classify_fraud_pattern({"amount": 3.2, "risk_score": 0.9, "dist1": 80}, [
        {"amount": 1.1}, {"amount": 2.0}, {"amount": 1.4},
    ])
    print(json.dumps(demo, indent=2))
