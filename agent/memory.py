"""Case memory: similar closed-case lookup + investigation write-back to the graph."""
import csv
import math
import os
from datetime import datetime, timezone
from typing import Any, Optional

_CASES: Optional[list] = None
_CASES_BY_ID: dict = {}
_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Initial-docs", "dataset", "closed_cases_history.csv",
)


def _load_cases() -> list:
    global _CASES, _CASES_BY_ID
    if _CASES is not None:
        return _CASES
    cases = []
    try:
        with open(_CSV_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cases.append(row)
    except OSError:
        pass
    _CASES = cases
    _CASES_BY_ID = {c.get("case_id", ""): c for c in cases}
    return cases


def _txn_amount(txn: dict) -> float:
    try:
        return float(txn.get("amount", txn.get("amt", txn.get("TransactionAmt", 0))) or 0)
    except (TypeError, ValueError):
        return 0.0


def _amount_similarity(amount_a: float, amount_b: float) -> float:
    return max(0.0, 1.0 - abs(math.log10(amount_a + 1) - math.log10(amount_b + 1)))


def _case_summary(case: dict) -> str:
    return (
        f"Case {case.get('case_id', '?')} ({case.get('outcome', '?')}, pattern "
        f"{case.get('pattern', '?')}) on card {case.get('card_id', '?')}: "
        f"{case.get('n_txns', '?')} txn(s), ${case.get('exposure_usd', '0')} exposure."
    )


def find_similar_cases(conn, txn: dict, pattern_hint: str, limit: int = 3) -> list:
    """Score closed cases against the flagged txn; returns top-N matches.

    Weights: pattern hint 0.5, amount log-proximity 0.2, identity overlap 0.3.
    """
    amount = _txn_amount(txn)
    txn_id = str(txn.get("txn_id", txn.get("TransactionID", "")))
    hint = (pattern_hint or "").strip().lower()
    scored = []
    for case in _load_cases():
        score = 0.0
        if hint and case.get("pattern", "").strip().lower() == hint:
            score += 0.5
        try:
            score += 0.2 * _amount_similarity(amount, float(case.get("exposure_usd", 0) or 0))
        except (TypeError, ValueError):
            pass
        overlap = 0.0
        if case.get("card_id") and str(txn.get("card_id", "")) == str(case["card_id"]):
            overlap = 0.3
        case_txn_ids = {t.strip() for t in str(case.get("txn_ids", "")).split("|") if t.strip()}
        if txn_id and txn_id in case_txn_ids:
            overlap = 0.3
        score += overlap
        scored.append({"score": score, "case": case})
    scored.sort(key=lambda s: s["score"], reverse=True)
    results = []
    for item in scored[:limit]:
        case = item["case"]
        if item["score"] <= 0:
            continue
        results.append({
            "case_id": case.get("case_id", ""),
            "verdict": case.get("outcome", ""),
            "pattern": case.get("pattern", ""),
            "similarity": round(item["score"], 3),
            "summary": _case_summary(case),
        })
    return results


def _resolve_conn(conn):
    inner = getattr(conn, "conn", None)
    if inner is not None and not hasattr(conn, "upsertVertex"):
        return inner
    return conn


def persist_investigation_case(conn, state: dict) -> str:
    """Upsert an InvestigationCase vertex plus its edges. Returns graph_case_id or ''."""
    case_id = str(state.get("case_id", "") or "")
    if not case_id:
        return ""
    conn = _resolve_conn(conn)
    flagged_txn = state.get("flagged_txn", {}) or {}
    txn_id = str(
        state.get("case_data", {}).get("TransactionID", "")
        or flagged_txn.get("txn_id", "")
        or ""
    )
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.upsertVertex("InvestigationCase", case_id, {
            "source_case_id": str(state.get("case_data", {}).get("case_id", "") or ""),
            "status": "closed" if state.get("verdict") in ("fraud", "legitimate") else "open",
            "verdict": str(state.get("verdict", "uncertain")),
            "fraud_probability": float(state.get("fraud_probability", 0.0) or 0.0),
            "pattern": str(state.get("pattern", "none")),
            "exposure_usd": float(state.get("exposure_usd", 0.0) or 0.0),
            "summary": str(state.get("summary", ""))[:4000],
            "created_at": created_at,
        })
    except Exception as e:
        print(f"Warning: could not persist InvestigationCase {case_id}: {e}")
        return ""

    try:
        if txn_id:
            conn.upsertEdge("InvestigationCase", case_id, "INV_INVOLVES", "Transaction", txn_id)
        card_ids = {str(c) for c in (state.get("connected_card_ids") or []) if c}
        for card_id in card_ids:
            conn.upsertEdge("InvestigationCase", case_id, "INV_ON_CARD", "Card", card_id)
            conn.upsertEdge("InvestigationCase", case_id, "INV_CONNECTED_TO", "Card", card_id)
    except Exception as e:
        print(f"Warning: could not persist InvestigationCase edges for {case_id}: {e}")

    known_cases = _CASES_BY_ID or {c.get("case_id", ""): c for c in _load_cases()}
    for similar in state.get("similar_prior_cases") or []:
        similar_id = str(similar.get("case_id", "") if isinstance(similar, dict) else similar)
        if similar_id and similar_id in known_cases:
            try:
                conn.upsertEdge("InvestigationCase", case_id, "SIMILAR_TO", "ClosedCase", similar_id)
            except Exception as e:
                print(f"Warning: could not link {case_id} -> {similar_id}: {e}")
    return case_id
