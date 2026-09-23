"""Builds the exact benchmark answer contract from an InvestigationState.

Shared by api.py, main.py and the benchmark runner so every path emits the
same schema (see Initial-docs/dataset README "Answer Format").
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

SAR_ACTIVITY_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _txn_id(txn: Dict[str, Any]) -> str:
    return str(txn.get("txn_id", txn.get("TransactionID", "")) or "")


def _txn_date(txn: Dict[str, Any]) -> str:
    ts = str(txn.get("ts", "") or "")
    return ts.split(" ")[0] if ts else ""


def _what_changed(initial: List[Dict[str, Any]], final: List[Dict[str, Any]],
                  evidence_requests: List[Dict[str, Any]]) -> str:
    if not evidence_requests:
        return "nothing"
    initial_names = {a.get("action") for a in initial}
    final_names = {a.get("action") for a in final}
    added = [a for a in final_names - initial_names]
    removed = [a for a in initial_names - final_names]
    req_types = ", ".join(sorted({r.get("type", "") for r in evidence_requests})) or "evidence"
    parts = []
    if added:
        parts.append("Final adds " + ", ".join(sorted(added)))
    if removed:
        parts.append("drops " + ", ".join(sorted(removed)))
    if not parts:
        return "nothing"
    return ("; ".join(parts) + f" after the {req_types} response.")


def build_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    case_id = str(state.get("case_id", "") or "")
    verdict = state.get("verdict", "uncertain")
    initial = [dict(a) for a in (state.get("initial_actions") or [])]
    final = [dict(a) for a in (state.get("final_actions") or [])]
    evidence_requests = list(state.get("evidence_requests") or [])
    if not evidence_requests:
        final = [dict(a) for a in initial]

    files_report = any(a.get("action") == "FILE_REPORT" for a in final)
    affected = list(state.get("affected_txn_ids") or [])
    exposure = float(state.get("exposure_usd", 0.0) or 0.0)
    pattern = state.get("pattern", "none")
    pattern_description = str(state.get("pattern_description", "") or "")
    if pattern != "undocumented":
        pattern_description = ""

    if verdict == "fraud":
        status = "closed_fraud"
    elif verdict == "legitimate":
        status = "closed_legitimate"
    else:
        status = "escalated" if any(a.get("action") == "ESCALATE_TO_ANALYST" for a in final) else "open"

    flagged = state.get("flagged_txn") or {}
    flagged_id = str(flagged.get("txn_id", (state.get("case_data") or {}).get("TransactionID", "")) or "")
    date_lookup = {}
    if flagged_id:
        date_lookup[flagged_id] = _txn_date(flagged)
    for t in state.get("related_txns") or []:
        date_lookup.setdefault(str(t.get("txn_id", t.get("TransactionID", ""))), _txn_date(t))
    dates = sorted({date_lookup[t] for t in affected if date_lookup.get(t)})
    activity_dates = [dates[0], dates[-1]] if len(dates) >= 1 and files_report else []

    if files_report:
        narrative = str(state.get("sar_narrative", "") or "")
        subjects = [str(s) for s in (state.get("sar_subjects") or []) if s]
        total_amount = exposure
        sar_reason = str(state.get("sar_reason", "") or "")
    else:
        narrative, subjects, total_amount = "", [], 0
        sar_reason = str(state.get("sar_reason", "") or "") or \
            f"R3a: no filing trigger met (verdict {verdict}, exposure ${exposure:,.2f}, documented pattern)"

    customer_id = str((state.get("case_data") or {}).get("customer_id", "") or "")
    if files_report and customer_id and customer_id not in subjects:
        subjects.insert(0, customer_id)

    first_suspicious = str(state.get("first_suspicious_txn_id", "") or "")
    if verdict == "legitimate":
        first_suspicious = ""

    what_changed = _what_changed(initial, final, evidence_requests)
    latency = round(float(state.get("latency_s", 0.0) or 0.0), 2)

    return {
        "case_id": case_id,
        "case": {
            "status": status,
            "verdict": verdict,
            "fraud_probability": round(float(state.get("fraud_probability", 0.0) or 0.0), 2),
            "pattern": pattern,
            "pattern_description": pattern_description,
            "affected_txn_ids": [str(t) for t in affected],
            "first_suspicious_txn_id": first_suspicious,
            "connected_card_ids": [str(c) for c in (state.get("connected_card_ids") or []) if c],
            "connected_device_profiles": [str(d) for d in (state.get("connected_device_profiles") or []) if d],
            "exposure_usd": 0.0 if verdict == "legitimate" else round(exposure, 2),
            "evidence": [
                {
                    "claim": str(e.get("claim", "")),
                    "source": e.get("source", "graph"),
                    "ref": str(e.get("ref", "")),
                    "entity_ids": [str(x) for x in (e.get("entity_ids") or []) if x],
                }
                for e in (state.get("evidence") or [])
            ],
            "similar_prior_cases": [str(s.get("case_id", "")) if isinstance(s, dict) else str(s)
                                    for s in (state.get("similar_prior_cases") or [])],
            "summary": str(state.get("summary", "") or ""),
            "written_to_graph": bool(state.get("written_to_graph", False)),
            "graph_case_id": str(state.get("graph_case_id", "") or ""),
        },
        "evidence_requests": [
            {
                "type": str(r.get("type", "customer_validation")),
                "asked_after_step": int(r.get("asked_after_step", 0) or 0),
                "assumed_response": str(r.get("assumed_response", "")),
            }
            for r in evidence_requests
        ],
        "sar": {
            "file": files_report,
            "reason": sar_reason,
            "narrative": narrative,
            "subjects": subjects,
            "total_amount_usd": round(total_amount, 2),
            "activity_dates": [d for d in activity_dates if SAR_ACTIVITY_DATE.match(d)],
        },
        "next_best_actions": {
            "initial": initial,
            "final": final,
            "what_changed": what_changed,
        },
        "stop_reason": str(state.get("stop_reason", "") or ""),
        "tool_calls": int(state.get("tool_calls", 0) or 0),
        "tokens": int(state.get("tokens", 0) or 0),
        "latency_s": latency,
        "graph_data": {
            "nodes": list(state.get("graph_nodes") or []),
            "edges": list(state.get("graph_edges") or []),
        },
        "metadata": {
            "duration_seconds": latency,
            "jev_classification": dict(state.get("jev_classification") or {}),
            "llm_ok": bool(state.get("llm_ok", True)),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }


def cases_dir() -> str:
    import os
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cases")


def write_answer(answer: Dict[str, Any], directory: str = None) -> str:
    import json
    import os
    target = directory or cases_dir()
    os.makedirs(target, exist_ok=True)
    path = os.path.join(target, f"{answer['case_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(answer, f, indent=2, ensure_ascii=False)
    return path