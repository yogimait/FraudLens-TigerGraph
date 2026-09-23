"""LangGraph investigation state machine.

Flow: load_case -> investigate_graph -> retrieve_memory_context -> jev_fast_routing
-> compute_initial_actions -> assess_evidence -> (conditional) apply_policy | request_evidence
-> simulate_response -> reassess_evidence -> apply_policy -> persist_case -> generate_outputs.

All TigerGraph access goes through the tg_mcp wrapper; every node counts tool calls.
"""
import csv
import os
import re
from functools import lru_cache
from typing import Any, Dict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

load_dotenv()

import jev_client
import llm as llm_mod
import memory as memory_mod
import rag as rag_mod
from jev_client import classify_fraud_pattern
from policy import apply_policy
from state import InvestigationState
from tg_mcp import TigerGraphMCP

tg_client = TigerGraphMCP()

_GRAPH_NAME = os.environ.get("TG_GRAPH", "FraudGraph")
CASE_PACK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "Initial-docs", "dataset", "case_pack.csv")
MAX_RELATED_TXNS = 30
WINDOW_HOURS = 2


def _txn_id(txn: Dict[str, Any]) -> str:
    return str(txn.get("txn_id", txn.get("TransactionID", "")) or "")


def _txn_amount(txn: Dict[str, Any]) -> float:
    try:
        return abs(float(txn.get("amount", txn.get("TransactionAmt", 0)) or 0))
    except (TypeError, ValueError):
        return 0.0


def _vertex_rows(result: Any, key: str) -> list:
    if not isinstance(result, list):
        return []
    for entry in result:
        if isinstance(entry, dict) and key in entry:
            return [row for row in entry[key] if isinstance(row, dict)]
    return []


def _norm_vertex(row: Dict[str, Any]) -> Dict[str, Any]:
    attrs = row.get("attributes", {}) if isinstance(row, dict) else {}
    vid = row.get("v_id", attrs.get("txn_id", attrs.get("card_id", ""))) if isinstance(row, dict) else ""
    return {"id": str(vid), **(attrs or {})}


def _evidence_entry(claim: str, source: str, ref: str, entity_ids: list) -> Dict[str, Any]:
    return {"claim": claim, "source": source, "ref": ref, "entity_ids": [str(e) for e in entity_ids if e]}


@lru_cache(maxsize=1)
def _case_pack() -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    try:
        with open(CASE_PACK_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows[row["case_id"]] = row
    except OSError:
        pass
    return rows


def _load_case(state: InvestigationState) -> InvestigationState:
    case_data = dict(state.get("case_data") or {})
    pack_row = _case_pack().get(state.get("case_id", ""))
    if pack_row:
        case_data.setdefault("card_id", pack_row.get("card_id", ""))
        case_data.setdefault("customer_id", pack_row.get("customer_id", ""))
        case_data.setdefault("risk_score", pack_row.get("risk_score", ""))
        case_data.setdefault("trigger_text", pack_row.get("trigger_text", ""))
    txn_id = str(case_data.get("TransactionID") or case_data.get("flagged_txn_id") or "")
    flagged: Dict[str, Any] = {}
    if txn_id:
        try:
            gsql = (f"INTERPRET QUERY (STRING t_id) FOR GRAPH {_GRAPH_NAME} {{\n"
                    "  T = SELECT t FROM Transaction:t WHERE t.txn_id == t_id;\n"
                    "  PRINT T;\n}")
            rows = _vertex_rows(tg_client.run_interpreted_query(gsql, {"t_id": txn_id}), "T")
            if rows:
                flagged = {**_norm_vertex(rows[0]), "txn_id": txn_id}
        except Exception as e:
            print(f"Flagged txn fetch failed ({txn_id}): {e}")
    if not flagged and txn_id:
        risk = _parse_amount(case_data.get("trigger_text", "")) if pack_row else 0.0
        flagged = {"txn_id": txn_id, "risk_score": _to_float(case_data.get("risk_score", 0)), "amount": risk}
    return {"case_data": {**case_data, "TransactionID": txn_id},
            "flagged_txn": flagged,
            "step": state.get("step", 0) + 1,
            "tool_calls": state.get("tool_calls", 0) + 1}


def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_amount(text: str) -> float:
    match = re.search(r"\$([\d,]+(?:\.\d+)?)", text or "")
    if not match:
        return 0.0
    return float(match.group(1).replace(",", ""))


def investigate_graph(state: InvestigationState) -> InvestigationState:
    txn = state.get("flagged_txn") or {}
    txn_id = _txn_id(txn) or str((state.get("case_data") or {}).get("TransactionID", ""))
    case_data = state.get("case_data") or {}
    tools = 0
    evidence: list = []
    nodes: list = []
    edges: list = []
    related: list = []
    connected_cards: list = []
    device_profiles: list = []

    amount = _txn_amount(txn)
    nodes.append({"id": f"txn-{txn_id}", "type": "transaction", "label": f"Txn {txn_id}",
                  "data": {"amount": amount, "risk_score": _to_float(txn.get("risk_score", 0))}})

    device_rows = _fetch_device(txn_id)
    device = device_rows[0] if device_rows else None
    device_id = ""
    if device:
        device_id = device["id"]
        profile = _device_profile_string(device)
        nodes.append({"id": f"dev-{device_id}", "type": "device", "label": f"Device {device_id}", "data": device})
        edges.append({"source": f"txn-{txn_id}", "target": f"dev-{device_id}", "label": "FROM_DEVICE"})
        evidence.append(_evidence_entry(
            f"Flagged transaction {txn_id} came from device profile {profile} ({device.get('device_type', 'unknown')})",
            "graph", "get_transaction_device", [txn_id, device_id]))

    # Graph-native card id first (case_pack ids like C12382-K1 don't match the
    # graph's card1-based ids); case_pack value is only a fallback label.
    card_id = _lookup_card(txn_id)
    tools += 1
    if not card_id:
        card_id = str(case_data_card(state) or "")
    if card_id:
        nodes.append({"id": f"card-{card_id}", "type": "card", "label": f"Card {card_id}", "data": {}})
        edges.append({"source": f"card-{card_id}", "target": f"txn-{txn_id}", "label": "MADE"})

    if card_id:
        related = _fetch_card_transactions(card_id)
        tools += 1
        for ct in related:
            cid = ct["id"]
            if cid == txn_id:
                continue
            nodes.append({"id": f"txn-{cid}", "type": "transaction", "label": f"Txn {cid}",
                          "data": {"amount": _txn_amount(ct), "ts": ct.get("ts", "")}})
            edges.append({"source": f"card-{card_id}", "target": f"txn-{cid}", "label": "MADE"})
        evidence.append(_evidence_entry(
            f"Card {card_id} has {len(related)} transactions on record; most recent amounts "
            f"{[round(_txn_amount(t), 2) for t in related[:5]]}",
            "graph", "get_card_transactions", [card_id]))

        window = _fetch_window(card_id, txn.get("ts", ""))
        tools += 1
        if window:
            small = [t for t in window if _txn_amount(t) < 5]
            if small:
                evidence.append(_evidence_entry(
                    f"{len(small)} online authorizations under $5 on card {card_id} within {WINDOW_HOURS}h before the flagged transaction",
                    "graph", "get_card_recent_window", [t["id"] for t in small]))
            related = _merge_related(related, window)

    if card_id:
        customer_id = str((state.get("case_data") or {}).get("customer_id", "") or "")
        if customer_id:
            customer_cards = _fetch_customer_cards(customer_id)
            tools += 1
            other = [c["id"] for c in customer_cards if c["id"] != card_id]
            if other:
                evidence.append(_evidence_entry(
                    f"Customer {customer_id} also holds cards {other}", "graph", "get_customer_cards", other))

    shared_cards = _fetch_shared_device_cards(txn_id)
    tools += 1
    if shared_cards:
        other_cards = [c["id"] for c in shared_cards if c["id"] != card_id]
        connected_cards.extend(other_cards)
        if other_cards and device:
            profile = _device_profile_string(device)
            device_profiles.append(profile)
            evidence.append(_evidence_entry(
                f"Device profile {profile} is shared with cards {other_cards}",
                "graph", "get_shared_device_cards", other_cards))

    related = _dedupe_related(related, txn_id)[:MAX_RELATED_TXNS]

    return {
        "related_txns": related,
        "connected_card_ids": connected_cards,
        "connected_device_profiles": device_profiles,
        "evidence": evidence,
        "graph_nodes": nodes,
        "graph_edges": edges,
        "tool_calls": state.get("tool_calls", 0) + tools,
        "step": state.get("step", 0) + 1,
    }


def case_data_card(state: Dict[str, Any]) -> str:
    return str((state.get("case_data") or {}).get("card_id", "") or "")


def _device_profile_string(device: Dict[str, Any]) -> str:
    bits = [device.get("device_info", ""), device.get("os", ""), device.get("browser", ""), device.get("screen", "")]
    return " | ".join(str(b) for b in bits if b) or str(device.get("id", ""))


def _merge_related(current: list, extra: list) -> list:
    seen = {t["id"] for t in current}
    merged = list(current)
    for t in extra:
        if t["id"] not in seen:
            seen.add(t["id"])
            merged.append(t)
    return merged


def _dedupe_related(txns: list, flagged_id: str) -> list:
    seen: set = set()
    out = []
    for t in sorted(txns, key=lambda t: t.get("ts", ""), reverse=True):
        tid = t["id"]
        if not tid or tid in seen:
            continue
        seen.add(tid)
        out.append(t)
    return out


def _fetch_device(txn_id: str) -> list:
    try:
        return _norm_rows(tg_client.run_installed_query("get_transaction_device", {"t_id": txn_id}), "Devices")
    except Exception as e:
        print(f"get_transaction_device failed: {e}")
        return []


def _fetch_card_transactions(card_id: str) -> list:
    try:
        return _norm_rows(tg_client.run_installed_query("get_card_transactions", {"c_id": card_id}), "Txns")
    except Exception as e:
        print(f"get_card_transactions failed: {e}")
        return []


def _fetch_window(card_id: str, anchor_ts: str) -> list:
    if not anchor_ts:
        return []
    try:
        return _norm_rows(tg_client.run_installed_query(
            "get_card_recent_window", {"c_id": card_id, "anchor_ts": anchor_ts, "hours": WINDOW_HOURS}), "Txns")
    except Exception as e:
        print(f"get_card_recent_window failed: {e}")
        return []


def _fetch_shared_device_cards(txn_id: str) -> list:
    """Cards whose transactions share a device with the flagged transaction.

    GSQL reverse traversal must be single-hop (multi-hop reverse mixes v1/v2
    syntax), so devices are fetched first and shared txns per device, then
    mapped back to cards via the existing interpreted card lookup.
    """
    try:
        devices = _norm_rows(tg_client.run_installed_query("get_transaction_device", {"t_id": txn_id}), "Devices")
    except Exception as e:
        print(f"get_transaction_device failed: {e}")
        return []
    cards_by_id = {}
    for dev in devices:
        try:
            shared = _norm_rows(tg_client.run_installed_query(
                "get_shared_device_cards", {"d_id": dev["id"]}), "SharedTxns")
        except Exception as e:
            print(f"get_shared_device_cards failed: {e}")
            continue
        for t in shared:
            cid = _lookup_card(t["id"])
            if cid:
                cards_by_id[cid] = {"id": cid}
    return list(cards_by_id.values())


def _fetch_customer_cards(customer_id: str) -> list:
    try:
        return _norm_rows(tg_client.run_installed_query("get_customer_cards", {"cust_id": customer_id}), "Cards")
    except Exception as e:
        print(f"get_customer_cards failed: {e}")
        return []


def _lookup_card(txn_id: str) -> str:
    gsql = (f"INTERPRET QUERY (STRING t_id) FOR GRAPH {_GRAPH_NAME} {{\n"
            "  C = SELECT c FROM Card:c -(MADE:e)-> Transaction:t WHERE t.txn_id == t_id;\n"
            "  PRINT C;\n}")
    try:
        rows = _norm_rows(tg_client.run_interpreted_query(gsql, {"t_id": txn_id}), "C")
        return rows[0]["id"] if rows else ""
    except Exception as e:
        print(f"card lookup failed: {e}")
        return ""


def _norm_rows(result: Any, key: str) -> list:
    return [_norm_vertex(r) for r in _vertex_rows(result, key)]


def retrieve_memory_context(state: InvestigationState) -> InvestigationState:
    txn = state.get("flagged_txn") or {}
    txn_id = _txn_id(txn)
    classification = state.get("jev_classification") or {}
    hint = classification.get("pattern") or ""
    if not hint:
        hint, _ = jev_client._heuristic_pattern(txn, state.get("related_txns") or [])
    similar = memory_mod.find_similar_cases(
        tg_client,
        {"txn_id": txn_id, "card_id": case_data_card(state), "amount": _txn_amount(txn)},
        hint, limit=3)
    rag_hits = rag_mod.retrieve_context(
        tg_client,
        [f"{hint} fraud pattern and required policy actions",
         f"transaction {txn_id} risk_score {_to_float(txn.get('risk_score', 0))} evidence"],
        top_k=3)

    evidence = list(state.get("evidence") or [])
    rag_context = []
    for hit in rag_hits:
        rag_context.append({"ref": hit.get("ref", ""), "text": hit.get("text", ""), "score": hit.get("score", 0)})
        evidence.append(_evidence_entry(str(hit.get("text", ""))[:240], "document", hit.get("ref", ""), []))

    nodes = list(state.get("graph_nodes") or [])
    edges = list(state.get("graph_edges") or [])
    case_id = state.get("case_id", "")
    nodes.append({"id": f"case-{case_id}", "type": "case", "label": f"Case {case_id}", "data": {}})
    edges.append({"source": f"case-{case_id}", "target": f"txn-{txn_id}", "label": "INVOLVES"})
    similar_ids = []
    for sim in similar:
        similar_ids.append(sim["case_id"])
        nodes.append({"id": f"cc-{sim['case_id']}", "type": "closed_case", "label": sim["case_id"],
                      "data": {"verdict": sim["verdict"], "pattern": sim["pattern"], "similarity": sim["similarity"]}})
        edges.append({"source": f"case-{case_id}", "target": f"cc-{sim['case_id']}", "label": "SIMILAR_TO"})

    return {
        "similar_prior_cases": similar,
        "rag_context": rag_context,
        "evidence": evidence,
        "graph_nodes": nodes,
        "graph_edges": edges,
        "tool_calls": state.get("tool_calls", 0) + (1 if rag_hits else 0),
        "step": state.get("step", 0) + 1,
    }


def jev_fast_routing(state: InvestigationState) -> InvestigationState:
    txn = state.get("flagged_txn") or {}
    summary = " ".join(str(e.get("claim", "")) for e in state.get("evidence") or [])
    classification = classify_fraud_pattern(
        txn,
        state.get("related_txns") or [],
        evidence_summary=summary,
        coordination_facts={"shared_devices": len(state.get("connected_device_profiles") or []),
                            "shared_cards": len(state.get("connected_card_ids") or [])},
    )
    return {"jev_classification": classification, "step": state.get("step", 0) + 1}


def _prior_probability(state: InvestigationState) -> float:
    txn = state.get("flagged_txn") or {}
    risk = _to_float(txn.get("risk_score", 0)) or _to_float((state.get("case_data") or {}).get("risk_score", 0))
    if risk <= 0 and (state.get("trigger_type") or "") == "customer_report":
        return 0.5
    return min(0.95, max(0.05, risk if risk > 0 else 0.45))


def compute_initial_actions(state: InvestigationState) -> InvestigationState:
    pre_state = dict(state)
    pre_state["fraud_probability"] = _prior_probability(state)
    pre_state["verdict"] = "uncertain"
    pre_state["customer_response"] = ""
    pre_state["evidence_request_count"] = 0
    result = apply_policy(pre_state)
    return {"initial_actions": result["final_actions"],
            "sar_required": result["sar_required"],
            "sar_reason": result["sar_reason"],
            "step": state.get("step", 0) + 1}


def assess_evidence(state: InvestigationState) -> InvestigationState:
    assessment = llm_mod.synthesize_evidence(state)
    return _absorb_assessment(state, assessment)


def reassess_evidence(state: InvestigationState) -> InvestigationState:
    assessment = llm_mod.synthesize_evidence(state)
    return _absorb_assessment(state, assessment)


def _absorb_assessment(state: InvestigationState, assessment: Dict[str, Any]) -> InvestigationState:
    fp = float(assessment.get("fraud_probability", 0.5))
    verdict = assessment.get("verdict", "uncertain")
    pattern = assessment.get("pattern", "none")
    affected = list(assessment.get("affected_txn_ids") or [])
    customer = state.get("customer_response") or ""
    if customer == "confirmed":
        verdict, fp = "legitimate", min(fp, 0.10)
        affected, pattern = [], pattern if pattern != "none" else "none"
    elif customer == "denied":
        fp = max(fp, 0.70)
        if fp >= 0.70:
            verdict = "fraud"
    elif customer == "no_reply" and verdict == "fraud" and fp < 0.85:
        verdict = "uncertain"
    if verdict == "legitimate":
        affected = []

    amounts = {_txn_id(t): _txn_amount(t) for t in (state.get("related_txns") or [])}
    flagged = state.get("flagged_txn") or {}
    if _txn_id(flagged):
        amounts[_txn_id(flagged)] = _txn_amount(flagged)
    exposure = round(sum(amounts.get(t, 0.0) for t in affected), 2)
    first = assessment.get("first_suspicious_txn_id") or (affected[0] if affected else "")

    return {
        "fraud_probability": round(fp, 2),
        "verdict": verdict,
        "pattern": pattern,
        "pattern_description": str(assessment.get("pattern_description", "")),
        "affected_txn_ids": affected,
        "first_suspicious_txn_id": str(first or ""),
        "exposure_usd": exposure if verdict != "legitimate" else 0.0,
        "confidence_drivers": assessment.get("confidence_drivers", []),
        "llm_ok": bool(assessment.get("llm_ok", True)),
        "tokens": int(state.get("tokens", 0) or 0) + int(assessment.get("tokens", 0) or 0),
        "step": state.get("step", 0) + 1,
    }


def evidence_sufficient(state: InvestigationState) -> str:
    fp = float(state.get("fraud_probability", 0.0) or 0.0)
    independent = len([e for e in state.get("evidence") or []
                       if e.get("source") in ("graph", "customer", "external")])
    if state.get("customer_response") in ("denied", "confirmed"):
        return "sufficient"
    if (fp >= 0.85 or fp <= 0.15) and independent >= 2:
        return "sufficient"
    if int(state.get("evidence_request_count", 0) or 0) >= 1:
        return "sufficient"
    return "insufficient"


def request_evidence(state: InvestigationState) -> InvestigationState:
    fp = float(state.get("fraud_probability", 0.0) or 0.0)
    pattern = (state.get("jev_classification") or {}).get("pattern", "none")
    trigger = state.get("trigger_type") or ""
    if trigger == "customer_report":
        req_type = "customer_validation"
    elif fp >= 0.70 or pattern in ("card_testing", "card_not_present_fraud",
                                  "card_not_present_new_device", "account_takeover", "undocumented"):
        req_type = "step_up_auth"
    else:
        req_type = "customer_validation"
    request = {
        "type": req_type,
        "asked_after_step": int(state.get("step", 0)),
        "assumed_response": (
            "Assumed the customer replies within 24 hours; a confirmation closes the case as legitimate, "
            "a denial raises the probability and triggers the block path under R2, silence keeps the card "
            "under monitoring per R4."),
    }
    return {
        "evidence_requests": list(state.get("evidence_requests") or []) + [request],
        "evidence_request_count": int(state.get("evidence_request_count", 0) or 0) + 1,
        "step": state.get("step", 0) + 1,
    }


def simulate_response(state: InvestigationState) -> InvestigationState:
    fp = float(state.get("fraud_probability", 0.0) or 0.0)
    trigger = state.get("trigger_type") or ""
    strong_fraud = fp >= 0.70
    weak_legit = fp <= 0.30
    if strong_fraud:
        response = "denied"
    elif weak_legit:
        response = "confirmed"
    else:
        response = "no_reply"

    request_count = int(state.get("evidence_request_count", 0) or 0)
    requests = list(state.get("evidence_requests") or [])
    if requests:
        requests[-1]["assumed_response"] = (
            f"Simulated response recorded: {response}. " + requests[-1]["assumed_response"])
    evidence = list(state.get("evidence") or []) + [_evidence_entry(
        f"Customer {response} when asked to validate the flagged transaction",
        "customer", f"evidence_request:{request_count}", [])]
    return {"customer_response": response, "evidence": evidence,
            "step": state.get("step", 0) + 1}


def apply_policy_node(state: InvestigationState) -> InvestigationState:
    result = apply_policy(state)
    updates: Dict[str, Any] = {
        "final_actions": result["final_actions"],
        "sar_required": result["sar_required"],
        "sar_reason": result["sar_reason"],
        "stop_reason": _stop_reason(state),
    }
    if not state.get("evidence_requests"):
        updates["initial_actions"] = [dict(a) for a in result["final_actions"]]
    sar_subjects = []
    customer_id = str((state.get("case_data") or {}).get("customer_id", "") or "")
    if customer_id:
        sar_subjects.append(customer_id)
    flagged_card = case_data_card(state)
    if flagged_card:
        sar_subjects.append(flagged_card)
    sar_subjects.extend(state.get("connected_card_ids") or [])
    sar_subjects.extend(state.get("connected_device_profiles") or [])
    updates["sar_subjects"] = sar_subjects
    updates["step"] = state.get("step", 0) + 1
    return updates


def _stop_reason(state: InvestigationState) -> str:
    fp = float(state.get("fraud_probability", 0.0) or 0.0)
    independent = len([e for e in state.get("evidence") or []
                       if e.get("source") in ("graph", "customer", "external")])
    if state.get("customer_response") in ("denied", "confirmed"):
        return "A verification response settled the question (policy section 6)."
    if fp >= 0.85 and independent >= 2:
        return f"Fraud probability {fp:.2f} >= 0.85 supported by {independent} independent evidence items (policy section 6)."
    if fp <= 0.15 and independent >= 2:
        return f"Fraud probability {fp:.2f} <= 0.15 supported by {independent} independent evidence items (policy section 6)."
    if int(state.get("evidence_request_count", 0) or 0) >= 1:
        return "Further steps are unlikely to change the decision; the evidence request round completed (policy section 6)."
    return "Evidence already sufficient for a defensible decision (policy section 6)."


def persist_case_node(state: InvestigationState) -> InvestigationState:
    try:
        graph_case_id = memory_mod.persist_investigation_case(tg_client, dict(state))
    except Exception as e:
        print(f"Case persistence failed: {e}")
        graph_case_id = ""
    return {"written_to_graph": bool(graph_case_id), "graph_case_id": graph_case_id,
            "tool_calls": state.get("tool_calls", 0) + 1, "step": state.get("step", 0) + 1}


def generate_outputs_node(state: InvestigationState) -> InvestigationState:
    outputs = llm_mod.generate_outputs(state)
    return {"summary": outputs.get("summary", ""),
            "sar_narrative": outputs.get("sar_narrative", ""),
            "stop_reason": outputs.get("stop_reason") or state.get("stop_reason", ""),
            "llm_ok": bool(state.get("llm_ok", True)) and bool(outputs.get("llm_ok", True)),
            "tokens": int(state.get("tokens", 0) or 0) + int(outputs.get("tokens", 0) or 0),
            "step": state.get("step", 0) + 1}


def build_graph():
    builder = StateGraph(InvestigationState)
    builder.add_node("load_case", _load_case)
    builder.add_node("investigate_graph", investigate_graph)
    builder.add_node("retrieve_memory_context", retrieve_memory_context)
    builder.add_node("jev_fast_routing", jev_fast_routing)
    builder.add_node("compute_initial_actions", compute_initial_actions)
    builder.add_node("assess_evidence", assess_evidence)
    builder.add_node("request_evidence", request_evidence)
    builder.add_node("simulate_response", simulate_response)
    builder.add_node("reassess_evidence", reassess_evidence)
    builder.add_node("apply_policy", apply_policy_node)
    builder.add_node("persist_case", persist_case_node)
    builder.add_node("generate_outputs", generate_outputs_node)

    builder.add_edge(START, "load_case")
    builder.add_edge("load_case", "investigate_graph")
    builder.add_edge("investigate_graph", "retrieve_memory_context")
    builder.add_edge("retrieve_memory_context", "jev_fast_routing")
    builder.add_edge("jev_fast_routing", "compute_initial_actions")
    builder.add_edge("compute_initial_actions", "assess_evidence")
    builder.add_conditional_edges("assess_evidence", evidence_sufficient,
                                  {"sufficient": "apply_policy", "insufficient": "request_evidence"})
    builder.add_edge("request_evidence", "simulate_response")
    builder.add_edge("simulate_response", "reassess_evidence")
    builder.add_edge("reassess_evidence", "apply_policy")
    builder.add_edge("apply_policy", "persist_case")
    builder.add_edge("persist_case", "generate_outputs")
    builder.add_edge("generate_outputs", END)
    return builder.compile()


graph = build_graph()


def run_investigation(case_id: str, transaction_id: str, trigger_type: str = "risk_score") -> Dict[str, Any]:
    initial_state = {
        "case_id": case_id,
        "case_data": {"TransactionID": str(transaction_id)},
        "trigger_type": trigger_type,
    }
    return graph.invoke(initial_state)


if __name__ == "__main__":
    import json as _json
    print(json.dumps(run_investigation("HHG-017", "3450629"), indent=2, default=str)[:4000])